"""http://developer.tempo.io/doc/timesheets/api/rest/latest"""  # noqa

from datetime import datetime
from typing import List, Dict, Optional, Union, Mapping, Iterable, Iterator
import json
import logging

from humps import decamelize
from pydantic import BaseModel
from pydantic.dataclasses import dataclass

from tempoggl.toggl import TogglProject

logger = logging.getLogger(__name__)


# https://docs.atlassian.com/DAC/rest/jira/6.1.html#d2e2990
class JiraProject(BaseModel):
    id: int
    key: str  # e.g. PROJ
    name: str


class IssueResponse(BaseModel):
    key: str  # e.g. PROJ-1234
    id: int
    project_id: int


class WorkLogIssue(IssueResponse):
    toggl_id: int


# http://developer.tempo.io/doc/timesheets/api/rest/latest
class WorkLog(BaseModel):
    comment: str
    date_started: datetime
    date_created: datetime
    date_updated: datetime  # same as date_created if log is not edited
    time_spent_seconds: int
    issue: IssueResponse


@dataclass
class TempoTogglPair:
    tempo_log: WorkLog
    toggl_project: TogglProject
    tempo_project: JiraProject


def rename_self(dirty: Dict) -> Dict:
    """Rename self key into "self_".

    See https://github.com/samuelcolvin/pydantic/issues/430

    :param dirty: this argument is not mutated.
    """
    if 'self' in dirty:
        value = dirty['self']
        cleaned = {k: v for k, v in dirty.items() if k != 'self'}

        added = {'self_': value, **cleaned}
    else:
        added = dirty

    return {
        k: rename_self(v) if isinstance(v, dict) else v
        for k, v in added.items()
    }


def tempo_ids_to_toggl(
    toggl_mapping_conf: Dict[str, int], jira_projects_body: str
) -> Dict[int, Optional[int]]:
    """Use the user configuration to generate mapping between Tempo and Toggl.

    returns:
    {
        123: 123456,

        # this means there exists jira project with id 124, but user has not
        # given the mapped toggl id
        124: None,
    }
    """
    projects = [
        JiraProject.parse_obj(rename_self(i))
        for i in json.loads(jira_projects_body)
    ]

    project_id_to_key = {i.id: i.key for i in projects}

    toggls = {
        p.id: toggl_mapping_conf.get(project_id_to_key[p.id]) for p in projects
    }

    return toggls


@dataclass
class WorklogError:
    message: str


def join_worklogs(
    worklogs: Iterable[WorkLog],
    tempo_projects: Iterable[JiraProject],
    config_toggl_table: Mapping[str, int],
    toggl_projects: Iterable[TogglProject],
) -> Union[WorklogError, List[TempoTogglPair]]:
    tempo_table = {project.id: project for project in tempo_projects}
    toggl_table = {project.id: project for project in toggl_projects}

    toggl_mapping = {
        key: toggl_table.get(toggl_id)
        for key, toggl_id in config_toggl_table.items()
    }

    logger.info('using toggl mapping of {}'.format(toggl_mapping))

    worklogs_response = []

    for worklog in worklogs:
        project = tempo_table.get(worklog.issue.project_id)

        if not project:
            return WorklogError(
                'unexpected project id "{}"'.format(worklog.issue.project_id)
            )

        if project.key not in toggl_mapping:
            return WorklogError(
                'unknown jira key "{}", please add the key to '
                'configuration '.format(project.key)
            )
        else:
            toggl_project = toggl_mapping.get(project.key)

            if toggl_project is None:
                return WorklogError(
                    'invalid toggl id for jira key {}'.format(project.key)
                )

            worklogs_response.append(
                TempoTogglPair(
                    tempo_log=worklog,
                    tempo_project=project,
                    toggl_project=toggl_project,
                )
            )

    return worklogs_response


def reformat_json(dirty: Iterable[Dict]) -> Iterator[Dict]:
    """Rename self attribute and convert to snake_case."""
    for obj in dirty:
        yield rename_self(decamelize(obj))
