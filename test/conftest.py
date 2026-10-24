"""Shared fixtures: the repository root the doc tests read. One hook: under mutmut, the cheapest test runs first."""
import gc
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


# Decision: R-024 (c). pytest's unraisable-exception plugin runs gc.collect() at the start and end of every pytest.main,
# and a mutant is one pytest.main in a fork of a warmed process: each collection walked the whole warmed heap (polars,
# the test modules) for 85 ms, twice per mutant, about half the mutation run. Freezing it moves that heap out of the
# collector's walk; nothing is skipped and the plugin still runs. Only under mutmut, which sets this variable.
def pytest_sessionstart(session: pytest.Session) -> None:
    """Under mutmut, freeze what the warmed process already holds so the per-run gc.collect() calls are cheap."""
    if "MUTANT_UNDER_TEST" in os.environ:
        gc.freeze()
