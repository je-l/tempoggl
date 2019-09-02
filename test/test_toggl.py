from typing import Iterable

from tempoggl.cli import tempo_to_toggl
from tempoggl.tempo import TempoTogglPair


def test_entry_has_jira_key(tempodump: Iterable[TempoTogglPair]) -> None:
    for pair in tempodump:
        toggl = tempo_to_toggl(pair)

        assert pair.tempo_log.issue.key in toggl.time_entry.description
