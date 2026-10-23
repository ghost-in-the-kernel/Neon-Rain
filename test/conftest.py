"""Shared fixtures: the repository root the doc tests read. One hook: under mutmut, the cheapest test runs first."""
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def root() -> Path:
    """The repository root, e.g. /home/user/neon-rain."""
    return ROOT


# Decision: R-024 (c). mutmut runs a mutant's tests with -x, in the order of a set, so a mutant a cheap test kills
# waits for a dear one first half the time. Only the order changes; the tests, and what kills a mutant, do not.
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """In a mutant's own run (not stats, not a clean run), order its tests by the seconds mutmut timed them at."""
    if "__mutmut_" not in os.environ.get("MUTANT_UNDER_TEST", ""):
        return
    stats = Path("mutmut-stats.json")  # mutmut runs a mutant's tests inside mutants/, where it keeps its stats
    seconds = json.loads(stats.read_text())["duration_by_test"] if stats.is_file() else {}
    items.sort(key=lambda item: seconds.get(item.nodeid, 0.0))
