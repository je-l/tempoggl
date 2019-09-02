from os import path
from typing import Dict

import pytest

from tempoggl.tempo import (
    WorklogError,
    rename_self,
    JiraProject,
    WorkLog,
    join_worklogs,
)
from tempoggl.toggl import TogglProject
from test.conftest import load_many


@pytest.mark.parametrize(
    'mapping,error',
    [
        ({'TUN': 4}, 'unknown jira key'),
        ({'TUN': -100, 'PROJ': -101}, 'invalid toggl id'),
    ],
)
def test_worklog_joining_errors(mapping: Dict[str, int], error: str) -> None:
    worklogs = load_many(path.join('test', 'tempo_worklogs.json'), WorkLog)
    toggl_projects = load_many(
        path.join('test', 'toggl_projects.json'), TogglProject
    )
    tempo_projects = load_many(
        path.join('test', 'tempo_projects.json'), JiraProject
    )
    response = join_worklogs(worklogs, tempo_projects, mapping, toggl_projects)
    assert isinstance(response, WorklogError)

    assert error in response.message


def test_worklog_joining_success() -> None:
    toggl_id_mapping = {'PROJ': 1115, 'TUN': 1113}

    worklogs = load_many(path.join('test', 'tempo_worklogs.json'), WorkLog)
    toggl_projects = load_many(
        path.join('test', 'toggl_projects.json'), TogglProject
    )
    tempo_projects = load_many(
        path.join('test', 'tempo_projects.json'), JiraProject
    )

    result = join_worklogs(
        worklogs, tempo_projects, toggl_id_mapping, toggl_projects
    )

    assert isinstance(result, list)


@pytest.mark.parametrize(
    'dirty_input,output',
    [
        ({'self': 1}, {'self_': 1}),
        ({'nested': {'self': 1}}, {'nested': {'self_': 1}}),
    ],
)
def test_rename_self(dirty_input: Dict, output: Dict) -> None:
    """See the rename_self() docstring."""
    assert rename_self(dirty_input) == output


def test_rename_self_no_side_effects() -> None:
    before = {'nested': {'self': 2}}
    expected = {'nested': {'self': 2}}

    rename_self(before)

    assert expected == before
