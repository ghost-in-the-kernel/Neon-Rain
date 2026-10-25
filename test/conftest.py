"""Shared fixtures: the repository root the doc tests read. One hook: under mutmut, the cheapest test runs first."""
import functools
import gc
import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# Decision: R-024 (c). Every test that makes a commit in a throwaway repository ran the machine's own git config: in a
# cloud session that signs each commit by starting an ssh signer, about 90 ms a commit, 150 commits in the fast loop.
# A test of a throwaway repository wants no one's global config (the tests name their own author), so none is read.
@pytest.fixture(autouse=True, scope="session")
def no_global_git_config() -> Iterator[None]:
    """For the whole session, git reads neither the user's nor the system's config; the environment is restored after."""
    patch = pytest.MonkeyPatch()
    patch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    patch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    yield
    patch.undo()


# Decision: R-024 (c). scripts.checks.supply_chain asks importlib.metadata for the installed packages' import names on
# every call, a walk of every installed file (about 0.2 s), and fourteen tests and every supply_chain mutant's run
# make the call. The installed packages do not change during a process, so the answer is kept, and asked for here, at
# import, so that under mutmut the warm-up asks it once and every forked mutant run inherits it. Each caller gets a copy.
def _ask_installed_packages_once() -> None:
    """Replace supply_chain's packages_distributions with a copy-returning memo, primed now."""
    from scripts.checks import supply_chain
    if hasattr(supply_chain.packages_distributions, "cache_info"):  # a warmed process imports this file once only
        return
    kept = functools.cache(supply_chain.packages_distributions)
    kept()
    supply_chain.packages_distributions = lambda: {name: list(found) for name, found in kept().items()}
    supply_chain.packages_distributions.cache_info = kept.cache_info  # type: ignore[attr-defined]


_ask_installed_packages_once()


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
