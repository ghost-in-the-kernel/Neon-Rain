"""R-024 (c): under mutmut a mutant's tests run cheapest first; anywhere else the order is left alone."""
import importlib.util
import json
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
