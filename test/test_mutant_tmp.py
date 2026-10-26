"""R-024 (c): under mutmut each run keeps its tmp_path folders in a folder of its own; anywhere else pytest's default stands."""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location("neonrain_conftest_tmp", Path(__file__).parent / "conftest.py")
assert SPEC is not None and SPEC.loader is not None
CONFTEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONFTEST)


class Session:
    """The two things the hook uses of a pytest session: a config that records the cleanups asked of it."""

    def __init__(self) -> None:
        self.cleanups: list[object] = []
        self.config = SimpleNamespace(add_cleanup=self.cleanups.append)

    def end(self) -> None:
        """Run the cleanups the way pytest does at the end of a session: the last asked for first."""
        for cleanup in reversed(self.cleanups):
            cleanup()  # type: ignore[operator]


def test_a_run_gets_a_temporary_root_of_its_own_and_gives_it_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTEST_DEBUG_TEMPROOT", raising=False)
    session = Session()
    CONFTEST.own_temporary_root(session.config)
    root = Path(os.environ["PYTEST_DEBUG_TEMPROOT"])
    assert root.is_dir() and root.name.startswith("neonrain-mutant-")
    session.end()
    assert not root.exists()
    assert "PYTEST_DEBUG_TEMPROOT" not in os.environ


def test_two_runs_never_share_a_temporary_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTEST_DEBUG_TEMPROOT", raising=False)
    first, second = Session(), Session()
    CONFTEST.own_temporary_root(first.config)
    first_root = os.environ["PYTEST_DEBUG_TEMPROOT"]
    CONFTEST.own_temporary_root(second.config)
    second_root = os.environ["PYTEST_DEBUG_TEMPROOT"]
    assert first_root != second_root
    second.end()
    first.end()
    assert not Path(first_root).exists() and not Path(second_root).exists()


def test_the_root_is_removed_with_what_a_test_left_in_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTEST_DEBUG_TEMPROOT", raising=False)
    session = Session()
    CONFTEST.own_temporary_root(session.config)
    root = Path(os.environ["PYTEST_DEBUG_TEMPROOT"])
    (root / "pytest-of-someone" / "pytest-0").mkdir(parents=True)
    (root / "pytest-of-someone" / "pytest-0" / "left.txt").write_text("a test's file")
    session.end()
    assert not root.exists()


def test_a_mutmut_session_takes_the_root_and_any_other_session_does_not(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(CONFTEST.gc, "freeze", lambda: None)  # the heap of this test run is not for freezing
    monkeypatch.delenv("PYTEST_DEBUG_TEMPROOT", raising=False)
    monkeypatch.delenv("MUTANT_UNDER_TEST", raising=False)
    plain = Session()
    CONFTEST.pytest_sessionstart(SimpleNamespace(config=plain.config))
    assert "PYTEST_DEBUG_TEMPROOT" not in os.environ and plain.cleanups == []
    monkeypatch.setenv("MUTANT_UNDER_TEST", "neonrain.targets.x_labels__mutmut_3")
    mutant = Session()
    CONFTEST.pytest_sessionstart(SimpleNamespace(config=mutant.config))
    assert Path(os.environ["PYTEST_DEBUG_TEMPROOT"]).is_dir()
    mutant.end()
