import os
from os import path
from typing import Optional, Dict, Union
from configparser import ConfigParser
import logging
from textwrap import dedent
from datetime import date

from pydantic import BaseModel, HttpUrl, ValidationError
from pydantic.dataclasses import dataclass


logger = logging.getLogger(__name__)

EXAMPLE_CONFIG = dedent(
    """
    [general]
    ; username: user.name@jira.com
    ; jira_url: https://jira.example.com

    [toggl_mapping]
    ; jira project key to toggl project id
    ; PROJ: 123456
"""
).lstrip()

CONFIG_FILENAME = 'tempoggl.cfg'


@dataclass
class GeneralConfig:
    username: Optional[str] = None
    jira_url: Optional[HttpUrl] = None
    yes: Optional[bool] = None
    from_date: Optional[date] = None
    verbose: Optional[bool] = None
    toggl_token: Optional[str] = None


class FileConfig(BaseModel):
    """Configuration in ~/.config/tempoggl/config by default."""

    general: GeneralConfig
    toggl_mapping: Dict[str, int]  # tempo key "PROJ" to toggl project id


class Environment(BaseModel):
    HOME: str
    XDG_CONFIG_HOME: Optional[str]


def init_config(dest_file: str) -> FileConfig:
    with open(dest_file, 'w') as f:
        f.write(EXAMPLE_CONFIG)

    return FileConfig(general=GeneralConfig(), toggl_mapping={})


def config_dir(env: Environment) -> str:
    config_dir = env.XDG_CONFIG_HOME or path.join(env.HOME, '.config')

    config_path = path.join(config_dir, 'tempoggl')

    return config_path


def read_config(path: str) -> Union[FileConfig, ValidationError]:
    config = ConfigParser()

    # preserve key case, ignore mypy bug
    # https://github.com/python/mypy/issues/708
    config.optionxform = str  # type: ignore
    config.read(path)

    dict_conf = {s: dict(config.items(s)) for s in config.sections()}

    try:
        return FileConfig.parse_obj(dict_conf)
    except ValidationError as errors:
        return errors


def create_or_read_config() -> Union[FileConfig, ValidationError]:
    env = Environment.parse_obj(dict(os.environ))
    dir = config_dir(env)

    if not path.exists(dir):
        logger.info('creating config dirs {}'.format(dir))
        os.makedirs(dir)

    config_path = path.join(dir, CONFIG_FILENAME)

    if path.exists(config_path):
        logger.info('reading config at path {}'.format(config_path))
        return read_config(config_path)
    else:
        logger.info('creating new config to path {}'.format(config_path))
        return init_config(config_path)


class AppConfig(BaseModel):
    """CLI config and arg config combined."""

    username: str
    jira_url: HttpUrl
    yes: bool
    from_date: date
    verbose: bool
    jira_to_toggl: Dict[str, int]  # jira project key to toggl project id
    toggl_token: str
