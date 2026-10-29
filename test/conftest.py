"""Shared fixtures: the repository root the doc tests read. One hook: under mutmut, the cheapest test runs first."""
import functools
import gc
import json
import os
import shutil
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# Decision: R-024 (c). The fast loop's frames are small (a few hundred rows a date), and polars still wakes its thread
# pool for each of the 45,000 eager calls of a run: 17 s of the loop's system time, and a third of its wall clock (37.9 s
# against 30.6 s on the same box, the same 911 tests passing). The loop and the mutants, which run the same tests
# (-m "not slow"), take one polars thread, as scripts/probe/survivorship.py already does; the slow set (the goldens
# compared byte for byte, the harness on the synthetic market) keeps polars' own threading, so it is still the proof
# that the numbers do not depend on it. A value already in the environment is left as it is.
def pytest_configure(config: pytest.Config) -> None:
    """Before any test module imports polars: give the fast loop one polars thread; leave a slow run's as it is."""
    if config.option.markexpr == "not slow":
        os.environ.setdefault("POLARS_MAX_THREADS", "1")


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


# Decision: R-024 (c). mutmut times only a test's call, so a test whose cost is a module fixture (a market, three whole
# evaluations) looked free and ran first, paying that fixture in every mutant that reached it: half of all the test seconds
# of a full mutation run (the progress test of test_baseline_run alone, 1,973 runs of 0.3 s). The stats run now also times
# each fixture's setup, and a mutant's tests are ordered by their call plus the fixtures they ask for. Only the order
# changes; the tests, and what kills a mutant, do not.
FIXTURE_SECONDS = "fixture-seconds.json"  # beside mutmut-stats.json, in mutants/
_fixture_runs: dict[str, list[float]] = {}


def fixture_key(fixturedef: pytest.FixtureDef) -> str:
    """The name a fixture is timed under, e.g. "test/test_baseline_run.py::fitted"."""
    return f"{fixturedef.baseid}::{fixturedef.argname}"


@pytest.hookimpl(wrapper=True)
def pytest_fixture_setup(fixturedef: pytest.FixtureDef, request: pytest.FixtureRequest) -> Iterator[None]:
    """In mutmut's stats run, time each fixture's own setup (the fixtures it asks for are timed apart)."""
    started = time.perf_counter()
    try:
        return (yield)
    finally:
        if os.environ.get("MUTANT_UNDER_TEST") == "stats":
            _fixture_runs.setdefault(fixture_key(fixturedef), []).append(time.perf_counter() - started)


def pytest_sessionfinish(session: pytest.Session) -> None:
    """In mutmut's stats run, keep the mean seconds of each fixture's setup where the mutants' runs will read it."""
    if os.environ.get("MUTANT_UNDER_TEST") == "stats":
        Path(FIXTURE_SECONDS).write_text(json.dumps({k: sum(v) / len(v) for k, v in _fixture_runs.items()}))


def fixtures_seconds(item: pytest.Item, seconds: dict[str, float]) -> float:
    """What the fixtures a test asks for (each of its names, however deep) cost to set up, from the stats run."""
    info = getattr(item, "_fixtureinfo", None)
    made = info.name2fixturedefs.values() if info else []
    return sum(seconds.get(fixture_key(defs[-1]), 0.0) for defs in made if defs)


# Decision: R-024 (c). mutmut runs a mutant's tests with -x, in the order of a set, so a mutant a cheap test kills
# waits for a dear one first half the time. Only the order changes; the tests, and what kills a mutant, do not.
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """In a mutant's own run (not stats, not a clean run), order its tests by the seconds mutmut timed them at, with
    the setup of the fixtures they ask for added."""
    if "__mutmut_" not in os.environ.get("MUTANT_UNDER_TEST", ""):
        return
    stats = Path("mutmut-stats.json")  # mutmut runs a mutant's tests inside mutants/, where it keeps its stats
    seconds = json.loads(stats.read_text())["duration_by_test"] if stats.is_file() else {}
    fixtures = Path(FIXTURE_SECONDS)
    setups = json.loads(fixtures.read_text()) if fixtures.is_file() else {}
    items.sort(key=lambda item: seconds.get(item.nodeid, 0.0) + fixtures_seconds(item, setups))


# Decision: R-024 (c). pytest's unraisable-exception plugin runs gc.collect() at the start and end of every pytest.main,
# and a mutant is one pytest.main in a fork of a warmed process: each collection walked the whole warmed heap (polars,
# the test modules) for 85 ms, twice per mutant, about half the mutation run. Freezing it moves that heap out of the
# collector's walk; nothing is skipped and the plugin still runs. Only under mutmut, which sets this variable.
def pytest_sessionstart(session: pytest.Session) -> None:
    """Under mutmut, freeze what the warmed process already holds so the per-run gc.collect() calls are cheap, and give
    the run its own temporary folder."""
    if "MUTANT_UNDER_TEST" in os.environ:
        gc.freeze()
        own_temporary_root(session.config)


# Decision: R-024 (c). Four mutants run at once, each one pytest.main, and every pytest session keeps its tmp_path folders
# under one shared /tmp/pytest-of-<user>. At the end of a session pytest walks that folder for dead symlinks while another
# session, starting, unlinks and recreates the symlink "pytest-current" in it; when the walk finds the link gone between
# two of its calls, FileNotFoundError leaves pytest.main (J-055). mutmut reads an exception out of a mutant's run as exit
# 255, which it calls a timeout, whatever the tests had said (a killed mutant included), and the gate refuses a timeout as
# an unexplained survivor; the mutant is clean on the next run. A folder only this session uses has nothing to race with.
def own_temporary_root(config: pytest.Config) -> None:
    """Make this session's tmp_path folders live in a new folder nothing else uses, removed when the session ends."""
    root = tempfile.mkdtemp(prefix="neonrain-mutant-")  # e.g. /tmp/neonrain-mutant-k3x9a_
    patch = pytest.MonkeyPatch()
    patch.setenv("PYTEST_DEBUG_TEMPROOT", root)  # pytest's own switch for where pytest-of-<user> goes
    config.add_cleanup(functools.partial(shutil.rmtree, root, ignore_errors=True))
    config.add_cleanup(patch.undo)
