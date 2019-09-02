from typing import List, TypeVar, Callable
import json
from tempfile import NamedTemporaryFile
from os import path

import pytest

from tempoggl.tempo import (
    reformat_json,
    WorkLog,
    JiraProject,
    join_worklogs,
    TempoTogglPair,
)
from tempoggl.toggl import TogglProject
from tempoggl.config import read_config, FileConfig


T = TypeVar('T')


TEST_CONFIG = """
[general]
username: abc
jira_url: https://example.com

[toggl_mapping]
PROJ: 1115
TUN: 1113
"""


def make_config(config: str) -> FileConfig:
    with NamedTemporaryFile('w+') as mock_conf_file:
        mock_conf_file.write(config)
        mock_conf_file.flush()
        conf = read_config(mock_conf_file.name)
        assert isinstance(conf, FileConfig)

        return conf


def load_many(path: str, schema: Callable[..., T]) -> List[T]:
    with open(path) as fixture_file:
        reformatted = reformat_json(json.load(fixture_file))

        return [schema(**i) for i in reformatted]


@pytest.fixture
def tempodump_content() -> str:
    with open(path.join('test', 'tempo_worklogs.json')) as f:
        return f.read()


@pytest.fixture
def tempodump() -> List[TempoTogglPair]:
    conf = make_config(TEST_CONFIG)

    with open(path.join('test', 'tempo_worklogs.json')) as tempo_f, open(
        path.join('test', 'toggl_projects.json')
    ) as toggl_projects_f, open(
        path.join('test', 'tempo_projects.json')
    ) as tempo_projects_f:
        tempo_projects = [
            JiraProject.parse_obj(i)
            for i in reformat_json(json.load(tempo_projects_f))
        ]

        toggl_projects = [
            TogglProject(**i) for i in json.load(toggl_projects_f)
        ]

        parsed_worklogs = [
            WorkLog.parse_obj(i) for i in reformat_json(json.load(tempo_f))
        ]

        joined = join_worklogs(
            parsed_worklogs, tempo_projects, conf.toggl_mapping, toggl_projects
        )
        assert isinstance(joined, list)

        return joined
