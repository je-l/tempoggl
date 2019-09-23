"""https://github.com/toggl/toggl_api_docs/blob/master/chapters/time_entries.md  # noqa
"""

from typing import Iterator, List, Sequence, Optional, Any
import sys
from datetime import datetime, timedelta
import traceback
import json
from json import JSONEncoder
import logging
from dataclasses import asdict

from pydantic.dataclasses import dataclass
from pydantic import BaseModel
import requests
from requests.exceptions import RequestException, HTTPError
from tzlocal import get_localzone


logger = logging.getLogger(__name__)

local_tz = get_localzone()


# see https://github.com/toggl/toggl_api_docs/blob/master/chapters/projects.md
class TogglProject(BaseModel):
    id: int
    name: str


class Workspace(BaseModel):
    id: int


# represents single Toggl entry, which is displayed for user before pushing
# changes to Toggl.
@dataclass
class TogglEntryStatus:
    duration: timedelta
    description: str


@dataclass
class TogglEntryPayload:
    id: int
    pid: int
    wid: int
    billable: bool
    start: datetime
    duration: int  # seconds
    description: str
    tags: List[str]


@dataclass
class TogglEntryResponse:
    data: TogglEntryPayload


@dataclass
class TogglEntryRequest:
    description: str
    start: datetime
    duration: int  # seconds
    pid: int
    created_with: str = 'tempoggl https://github.com/je-l/tempoggl'
    billable: bool = True


@dataclass
class TogglEntry:
    time_entry: TogglEntryRequest


class DateTimeEncoder(JSONEncoder):
    def default(self, node: Any) -> Any:
        if isinstance(node, datetime):
            # Tempo api returns datetimes without timezone contrary to the api
            # docs. We should assume the timezone is in the user's timezone.
            if node.tzinfo is None:
                return local_tz.localize(node).isoformat()

            return node.isoformat()

        return JSONEncoder.default(self, node)


def fetch_projects(api_token: str) -> Iterator[TogglProject]:
    auth = (api_token, 'api_token')
    res = requests.get('https://www.toggl.com/api/v8/workspaces', auth=auth)

    if res.status_code == 403:
        logger.critical('invalid toggl token')
        sys.exit(1)

    res.raise_for_status()

    workspaces = [Workspace.parse_obj(i) for i in json.loads(res.text)]

    for workspace in workspaces:
        resp = requests.get(
            'https://www.toggl.com/api/v8/workspaces/{}/projects'.format(
                workspace.id
            ),
            auth=auth,
        )
        resp.raise_for_status()

        projects = [TogglProject.parse_obj(i) for i in json.loads(resp.text)]

        yield from projects


def generate_description(jira_key: str, comment: str) -> str:
    """Make sure we always have jira key in the toggl entry."""
    if jira_key in comment:
        return comment
    else:
        return '{}: {}'.format(jira_key, comment)


def push_worklogs(
    entries: Sequence[TogglEntry], toggl_token: str
) -> Optional[str]:
    """POST converted tempo worklogs into Toggl.

    :returns: If we get error, the formatted traceback.
    """
    for index, worklog in enumerate(entries):
        logger.info('pushing worklog {}/{}'.format(index + 1, len(entries)))

        payload = json.dumps(asdict(worklog), cls=DateTimeEncoder)

        response = requests.post(
            'https://www.toggl.com/api/v8/time_entries',
            data=payload,
            headers={'Content-Type': 'application/json'},
            auth=(toggl_token, 'api_token'),
        )

        try:
            response.raise_for_status()
        except HTTPError as err:
            return err.response.text
        except RequestException:
            return traceback.format_exc()

    return None
