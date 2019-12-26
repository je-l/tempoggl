from argparse import ArgumentParser, Namespace, ArgumentTypeError
from datetime import date, timedelta, datetime
import sys
import re
from typing import Union, Tuple, Iterable, Any, Iterator
from getpass import getpass
from distutils.util import strtobool
from urllib.parse import urlparse
import logging
from pkg_resources import get_distribution
import json

import requests
from dateutil.parser import parse as dateutil_parse
from pydantic import ValidationError

from tempoggl.toggl import (
    TogglEntryRequest,
    push_worklogs,
    fetch_projects,
    TogglEntry,
    generate_description,
)
from tempoggl.tempo import (
    WorkLog,
    join_worklogs,
    WorklogError,
    TempoTogglPair,
    reformat_json,
    JiraProject,
)
from tempoggl.config import create_or_read_config, AppConfig, FileConfig
from tempoggl.typing_tools import unreachable


logger = logging.getLogger(__name__)

DESCRIPTION = (
    'Sync time tracking entries from Jira Tempo '
    'app into Toggl. Prompt before pushing any changes.'
)


def tempo_to_toggl(tempo_log: TempoTogglPair) -> TogglEntry:
    tempo = tempo_log.tempo_log

    return TogglEntry(
        time_entry=TogglEntryRequest(
            description=generate_description(tempo.issue.key, tempo.comment),
            start=tempo.date_started,
            duration=tempo.time_spent_seconds,
            pid=tempo_log.toggl_project.id,
        )
    )


def parse_date(arg: str) -> date:
    try:
        return dateutil_parse(arg).date()
    except Exception:
        raise ArgumentTypeError('cannot parse "{}"'.format(arg))


def jira_toggl_pair(arg: str) -> Tuple[str, int]:
    match = re.match(r'([A-Z]+)=(\d+)', arg)

    if not match:
        raise ArgumentTypeError('toggl-mapping syntax is "PROJ=3456"')

    return (match.group(1), int(match.group(2)))


def parse_args() -> Namespace:
    parser = ArgumentParser(prog='tempoggl', description=DESCRIPTION)
    parser.add_argument('--username', help='jira username')
    parser.add_argument(
        '-y', '--yes', action='store_true', help='answer yes when prompted'
    )
    parser.add_argument(
        'from_date',
        type=parse_date,
        help='sync all entries from this date',
        metavar='YYYY-MM-DD',
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='print more information'
    )
    parser.add_argument(
        '-j',
        '--jira-url',
        help='root url for jira e.g. https://jira.example.com',
    )
    parser.add_argument(
        '-t',
        '--toggl-api-token',
        metavar='TOGGL_TOKEN',
        help='get from here https://toggl.com/app/profile',
    )
    parser.add_argument(
        '-m',
        '--toggl-mapping',
        default=[],
        nargs='*',
        metavar='KEY=ID',
        type=jira_toggl_pair,
        help='map jira project key to toggl project id. For example '
        '"--toggl-mapping PROJ=456 ABCD=5432 MISC=9876"',
    )
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version=get_distribution('tempoggl').version,
    )

    return parser.parse_args()


class UnsafeJiraProtocol:
    pass


def validate_configs(
    args: Namespace, config: FileConfig
) -> Union[UnsafeJiraProtocol, ValidationError, AppConfig]:
    try:
        app_config = AppConfig(
            username=args.username or config.general.username,
            jira_url=args.jira_url or config.general.jira_url,
            yes=args.yes or config.general.yes,
            from_date=args.from_date or config.general.from_date,
            verbose=args.verbose or config.general.verbose,
            jira_to_toggl=(
                {**config.toggl_mapping, **(dict(args.toggl_mapping))}
            ),
            toggl_token=args.toggl_api_token or config.general.toggl_token,
        )
    except ValidationError as e:
        return e
    else:
        parsed_jira_url = urlparse(app_config.jira_url)

        if parsed_jira_url.scheme == 'https':
            return app_config
        elif parsed_jira_url.scheme == 'http':
            return UnsafeJiraProtocol()
        else:
            logger.critical(
                'unexpected jira url scheme: {}'.format(parsed_jira_url.scheme)
            )
            sys.exit(1)


def start_syncing(config: AppConfig, jira_password: str) -> None:
    auth = (config.username, jira_password)

    jira_projects_response = requests.get(
        '{}/rest/api/2/project'.format(config.jira_url), auth=auth
    )

    jira_projects_response.raise_for_status()

    # api returns 200 for wrong password
    if jira_projects_response.text == '[]':
        logger.critical('no jira projects found, possibly wrong password')
        sys.exit(1)

    jira_projects = [
        JiraProject.parse_obj(i)
        for i in reformat_json(json.loads(jira_projects_response.content))
    ]

    tempo_response = requests.get(
        '{}/rest/tempo-timesheets/3/worklogs'.format(config.jira_url),
        params={'dateFrom': config.from_date.isoformat()},
        auth=auth,
    )

    toggl_projects = list(fetch_projects(config.toggl_token))

    worklog_resposes = [
        WorkLog.parse_obj(i)
        for i in reformat_json(json.loads(tempo_response.content))
    ]

    worklogs = join_worklogs(
        worklog_resposes, jira_projects, config.jira_to_toggl, toggl_projects
    )

    if not worklogs:
        print(
            'no tempo worklogs found after {}'.format(config.from_date),
            file=sys.stderr,
        )
        sys.exit(1)

    if isinstance(worklogs, list):
        do_continue = prompt_for_pushing(worklogs, verbose=config.verbose)

        if not do_continue:
            logger.info('negative prompt, exiting...')
            sys.exit(1)
        else:
            error = push_worklogs(
                [tempo_to_toggl(tempo) for tempo in worklogs],
                config.toggl_token,
            )

            if error:
                logger.error(error)
                sys.exit(
                    'error writing changes to toggl, please inspect all'
                    ' listed worklog entries manually'
                )
            else:
                print('done', file=sys.stderr)
    elif isinstance(worklogs, WorklogError):
        logger.critical(worklogs.message)
        sys.exit(1)
    else:
        unreachable(worklogs)


def format_prompt(
    rows: Iterable[Tuple[datetime, timedelta, str, str]]
) -> Iterator[str]:
    msg_format = '{0:<20.20} {1:<10.10} {2:<15.15} {3}'
    yield msg_format.format('started', 'duration', 'jira issue', 'description')

    for start, duration, jira_key, description in rows:
        spent_time = str(duration)

        yield msg_format.format(
            start.strftime('%a %d %b %H:%M'), spent_time, jira_key, description
        )


def yes_prompt(question: str) -> bool:
    """Prompt yes/no with yes as default."""
    while True:
        prompted = input(question + ' [Yn]: ')
        if prompted == '':
            return True

        try:
            return strtobool(prompted)
        except ValueError:
            pass


def prompt_for_pushing(
    worklogs: Iterable[TempoTogglPair], verbose: bool
) -> bool:
    """Ask user if we want to continue pushing changes to Toggl."""
    for row in format_prompt(
        (
            w.tempo_log.date_started,
            timedelta(seconds=w.tempo_log.time_spent_seconds),
            w.tempo_log.issue.key,
            w.tempo_log.comment,
        )
        for w in worklogs
    ):
        print(row, file=sys.stderr)

    return yes_prompt('write changes to Toggl?')


def format_error(error: Any) -> str:
    return '{}: {}'.format(': '.join(error['loc']), error['msg'])


def run() -> None:
    args = parse_args()

    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO if args.verbose else logging.WARNING,
    )

    file_config = create_or_read_config()
    if isinstance(file_config, ValidationError):
        for error in file_config.errors():
            formatted_err = format_error(error)
            logger.critical(
                'invalid value for config parameter: {}'.format(formatted_err)
            )
        sys.exit(1)

    logger.info('using config file config {}'.format(file_config))

    config = validate_configs(args, file_config)

    if isinstance(config, AppConfig):
        logger.info('using combined configuration: {}'.format(config))

        pw_prompt = 'jira password for {}: '.format(config.username)

        start_syncing(config, getpass(pw_prompt))
    elif isinstance(config, ValidationError):
        for error in config.errors():
            formatted_err = format_error(error)
            logger.critical(
                'invalid config/parameter value: {}'.format(formatted_err)
            )

        logger.critical('missing or invalid parameters, exiting...')
        sys.exit(1)
    elif isinstance(config, UnsafeJiraProtocol):
        logger.critical(
            'jira with http protocol not supported, please use https'
        )
        sys.exit(1)
    else:
        unreachable(config)
