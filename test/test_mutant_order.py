"""R-024 (c): under mutmut a mutant's tests run cheapest first; anywhere else the order is left alone."""
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location("neonrain_conftest", Path(__file__).parent / "conftest.py")
assert SPEC is not None and SPEC.loader is not None
CONFTEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONFTEST)


def run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutant: str | None) -> list[str]:
    """The ids of three tests in mutmut's order, after the hook, with their timings in tmp_path."""
    (tmp_path / "mutmut-stats.json").write_text(json.dumps({"duration_by_test": {"a": 3.0, "b": 1.0}}))
    monkeypatch.chdir(tmp_path)
    if mutant is None:
        monkeypatch.delenv("MUTANT_UNDER_TEST", raising=False)
    else:
        monkeypatch.setenv("MUTANT_UNDER_TEST", mutant)
    items = [SimpleNamespace(nodeid=name) for name in ("a", "b", "c")]
    CONFTEST.pytest_collection_modifyitems(items)
    return [item.nodeid for item in items]


def test_a_mutants_tests_run_cheapest_first_and_an_untimed_one_first_of_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert run(tmp_path, monkeypatch, "neonrain.targets.x_labels__mutmut_3") == ["c", "b", "a"]


@pytest.mark.parametrize("mutant", [None, "", "stats", "fail", "list_all_tests"])
def test_every_other_run_keeps_its_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutant: str | None) -> None:
    assert run(tmp_path, monkeypatch, mutant) == ["a", "b", "c"]


def test_a_mutant_run_without_stats_keeps_its_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MUTANT_UNDER_TEST", "neonrain.targets.x_labels__mutmut_3")
    items = [SimpleNamespace(nodeid=name) for name in ("b", "a")]
    CONFTEST.pytest_collection_modifyitems(items)
    assert [item.nodeid for item in items] == ["b", "a"]


def item_asking(nodeid: str, fixtures: tuple[str, ...] = ()) -> SimpleNamespace:
    """A test that asks for fixtures, as pytest records them: each name's definitions, the nearest last."""
    defs = {name: [SimpleNamespace(baseid="test/t.py", argname=name)] for name in fixtures}
    return SimpleNamespace(nodeid=nodeid, _fixtureinfo=SimpleNamespace(name2fixturedefs=defs))


def test_a_test_that_asks_for_a_dear_fixture_runs_after_a_dear_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "mutmut-stats.json").write_text(json.dumps({"duration_by_test": {"a": 3.0, "b": 0.0, "c": 0.5}}))
    (tmp_path / CONFTEST.FIXTURE_SECONDS).write_text(json.dumps({"test/t.py::market": 5.0, "test/t.py::cheap": 0.1}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MUTANT_UNDER_TEST", "neonrain.targets.x_labels__mutmut_3")
    items = [item_asking("b", ("market",)), item_asking("a"), item_asking("c", ("cheap",)), item_asking("d", ("market",))]
    CONFTEST.pytest_collection_modifyitems(items)  # type: ignore[arg-type]
    assert [item.nodeid for item in items] == ["c", "a", "b", "d"]  # 0.6, 3.0, 5.0, 5.0 (a stable sort keeps b before d)


def test_the_seconds_of_a_tests_fixtures_are_the_sum_of_their_means() -> None:
    seconds = {"test/t.py::market": 5.0, "test/t.py::cheap": 0.25}
    assert CONFTEST.fixtures_seconds(item_asking("x", ("market", "cheap", "unknown")), seconds) == 5.25
    assert CONFTEST.fixtures_seconds(SimpleNamespace(nodeid="x"), seconds) == 0.0
    nothing = SimpleNamespace(nodeid="x", _fixtureinfo=SimpleNamespace(name2fixturedefs={"gone": []}))
    assert CONFTEST.fixtures_seconds(nothing, seconds) == 0.0


def test_the_stats_run_keeps_the_mean_seconds_of_each_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MUTANT_UNDER_TEST", "stats")
    monkeypatch.setattr(CONFTEST, "_fixture_runs", {"test/t.py::market": [1.0, 3.0]})
    CONFTEST.pytest_sessionfinish(SimpleNamespace())  # type: ignore[arg-type]
    assert json.loads((tmp_path / CONFTEST.FIXTURE_SECONDS).read_text()) == {"test/t.py::market": 2.0}


@pytest.mark.parametrize("mutant", [None, "", "fail", "neonrain.targets.x_labels__mutmut_3"])
def test_no_other_run_keeps_fixture_seconds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutant: str | None) -> None:
    monkeypatch.chdir(tmp_path)
    if mutant is None:
        monkeypatch.delenv("MUTANT_UNDER_TEST", raising=False)
    else:
        monkeypatch.setenv("MUTANT_UNDER_TEST", mutant)
    CONFTEST.pytest_sessionfinish(SimpleNamespace())  # type: ignore[arg-type]
    assert not (tmp_path / CONFTEST.FIXTURE_SECONDS).exists()


@pytest.mark.parametrize("expression, threads", [("not slow", "1"), ("slow", None), ("", None), ("not slow or x", None)])
def test_only_the_fast_loop_takes_one_polars_thread(
    monkeypatch: pytest.MonkeyPatch, expression: str, threads: str | None
) -> None:
    monkeypatch.delenv("POLARS_MAX_THREADS", raising=False)
    CONFTEST.pytest_configure(SimpleNamespace(option=SimpleNamespace(markexpr=expression)))  # type: ignore[arg-type]
    assert os.environ.pop("POLARS_MAX_THREADS", None) == threads


def test_a_polars_thread_count_already_chosen_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLARS_MAX_THREADS", "3")
    CONFTEST.pytest_configure(SimpleNamespace(option=SimpleNamespace(markexpr="not slow")))  # type: ignore[arg-type]
    assert os.environ["POLARS_MAX_THREADS"] == "3"
