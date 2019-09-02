from os import path

from tempoggl.tempo import tempo_ids_to_toggl
from test.conftest import make_config

TEMPO_PROJECTS = path.join('test', 'tempo_projects.json')


TEST_CONFIG = """
[general]

[toggl_mapping]
PROJ: 777
"""


def test_mapping_toggl_ids() -> None:
    config = make_config(TEST_CONFIG)

    with open(TEMPO_PROJECTS) as tempo_projects_f:
        toggl_ids = tempo_ids_to_toggl(
            config.toggl_mapping, tempo_projects_f.read()
        )

        # see tempo_project.json for magic numbers
        assert toggl_ids.get(1234) == 777
        assert toggl_ids.get(808) is None
