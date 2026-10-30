"""TODO 1.7 (HAR-14): what holds the goldens, tried on small invented files in tmp_path: their text, a decision in force,
writing them, and checking them. The harness on the synthetic market is test_the_freeze.py."""
import json
from pathlib import Path

import pytest

from neonrain.harness import goldens, trials

GHOST = (
    "### R-002: One\n- **Status:** in force\n\n"
    "### R-003: Two\n- **Status:** proposed\n\n"
    "### R-004: Three\n- **Status:** superseded by R-005\n\n"
    "### R-020: Four\n- **Status:** in force\n"
)
FILES = {"a.json": '{"x": 1}\n', "b.json": '{"y": 2}\n'}


# --- The numbers' text ----------------------------------------------------------------------------------------------


def test_floats_are_cut_to_twelve_significant_digits_wherever_they_sit() -> None:
    assert goldens.rounded({"a": [1 / 3, (2.0, "t")], "b": 7, "c": None, "d": True}) == {
        "a": [0.333333333333, [2.0, "t"]], "b": 7, "c": None, "d": True}
    assert goldens.rounded(123456789.123456789) == 123456789.123


def test_a_golden_is_sorted_indented_and_ends_with_a_line_break_and_refuses_nan() -> None:
    assert goldens.dumped({"b": 1, "a": [0.5]}) == '{\n "a": [\n  0.5\n ],\n "b": 1\n}\n'
    with pytest.raises(ValueError):
        goldens.dumped({"a": float("nan")})


def test_the_first_difference_names_its_line_and_both_texts() -> None:
    assert goldens.first_difference("a\nb\nc\n", "a\nb\nd\n") == 'line 3: golden "c", harness "d"'
    assert goldens.first_difference("a\n", "a\nb\n") == 'line 2: golden "", harness "b"'
    assert goldens.first_difference("a\nb\n", "a\n") == 'line 2: golden "b", harness ""'


def test_sha256_is_of_the_utf8_bytes_in_hex() -> None:
    assert goldens.sha256("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert goldens.sha256("é") == "4a99557e4033c3539de2eb65472017cad5f9557f7a0625a09f1c3f6e2ba69c4c"


# --- A decision in force ---------------------------------------------------------------------------------------------


def test_only_an_entry_whose_own_status_is_in_force_counts() -> None:
    assert goldens.in_force(GHOST, "R-002") and goldens.in_force(GHOST, "R-020")
    assert not goldens.in_force(GHOST, "R-003")  # proposed
    assert not goldens.in_force(GHOST, "R-004")  # superseded
    assert not goldens.in_force(GHOST, "R-009")  # no such entry
    assert not goldens.in_force(GHOST, "R-02")  # not an id
    assert not goldens.in_force(GHOST, "R-002 ")  # not an id
    assert not goldens.in_force(GHOST, "R-00")


# --- Writing ---------------------------------------------------------------------------------------------------------


def test_the_first_write_is_the_freeze_and_indexes_every_file(tmp_path: Path) -> None:
    assert goldens.write(tmp_path / "g", FILES, GHOST) == ["a.json", "b.json"]
    index = json.loads((tmp_path / "g" / goldens.INDEX).read_text())
    assert index["harness_version"] == trials.HARNESS_VERSION
    assert index["files"]["a.json"] == {"sha256": goldens.sha256(FILES["a.json"]), "changed_by": "1.7"}
    assert (tmp_path / "g" / "b.json").read_text() == FILES["b.json"]
    assert goldens.check(tmp_path / "g", FILES, GHOST) == []


def test_the_first_write_makes_the_directory_and_its_parents(tmp_path: Path) -> None:
    goldens.write(tmp_path / "harness" / "goldens", FILES, GHOST)
    assert (tmp_path / "harness" / "goldens" / "a.json").read_text() == FILES["a.json"]


def test_every_golden_that_would_change_is_named_in_the_refusal_and_in_the_check(tmp_path: Path) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    both = {"a.json": "x\n", "b.json": "y\n"}
    with pytest.raises(goldens.GoldenChange, match="a.json, b.json would change"):
        goldens.write(tmp_path, both, GHOST)
    goldens.write(tmp_path, both, GHOST, "R-020")
    assert goldens.check(tmp_path, both, GHOST) == [
        "a.json, b.json changed under a decision, and harness_version is still 1 (HAR-01, HAR-14)"]


def test_writing_what_is_there_changes_nothing(tmp_path: Path) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    before = (tmp_path / goldens.INDEX).read_text()
    assert goldens.write(tmp_path, FILES, GHOST) == []
    assert (tmp_path / goldens.INDEX).read_text() == before


def test_a_changed_golden_is_refused_without_a_decision_and_nothing_is_written(tmp_path: Path) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    before = (tmp_path / goldens.INDEX).read_text()
    with pytest.raises(goldens.GoldenChange, match="a.json would change"):
        goldens.write(tmp_path, FILES | {"a.json": "new\n"}, GHOST)
    assert (tmp_path / "a.json").read_text() == FILES["a.json"] and (tmp_path / goldens.INDEX).read_text() == before


@pytest.mark.parametrize("decision", ["R-003", "R-004", "R-009", "1.7", "R-02"])
def test_a_decision_not_in_force_does_not_excuse_a_change(tmp_path: Path, decision: str) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    with pytest.raises(goldens.GoldenChange, match="not an entry in force"):
        goldens.write(tmp_path, FILES | {"a.json": "new\n"}, GHOST, decision)
    assert (tmp_path / "a.json").read_text() == FILES["a.json"]


def test_a_change_under_a_decision_in_force_is_written_and_kept_in_the_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trials, "HARNESS_VERSION", "2")
    goldens.write(tmp_path, FILES, GHOST)
    assert goldens.write(tmp_path, FILES | {"a.json": "new\n"}, GHOST, "R-020") == ["a.json"]
    files = json.loads((tmp_path / goldens.INDEX).read_text())["files"]
    assert files["a.json"] == {"sha256": goldens.sha256("new\n"), "changed_by": "R-020"}
    assert files["b.json"]["changed_by"] == "1.7"
    assert goldens.check(tmp_path, FILES | {"a.json": "new\n"}, GHOST) == []


def test_a_golden_added_or_removed_later_is_a_change_too(tmp_path: Path) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    with pytest.raises(goldens.GoldenChange, match="c.json would change"):
        goldens.write(tmp_path, FILES | {"c.json": "c\n"}, GHOST)
    with pytest.raises(goldens.GoldenChange, match="b.json would change"):
        goldens.write(tmp_path, {"a.json": FILES["a.json"]}, GHOST)
    assert goldens.write(tmp_path, FILES | {"c.json": "c\n"}, GHOST, "R-002") == ["c.json"]
    assert goldens.write(tmp_path, {"a.json": FILES["a.json"], "c.json": "c\n"}, GHOST, "R-020") == ["b.json"]
    assert not (tmp_path / "b.json").exists()
    index = json.loads((tmp_path / goldens.INDEX).read_text())["files"]
    assert {name: entry["changed_by"] for name, entry in index.items()} == {"a.json": "1.7", "c.json": "R-002"}


def test_a_decision_with_the_first_write_is_not_recorded_as_a_change(tmp_path: Path) -> None:
    goldens.write(tmp_path, FILES, GHOST, "R-002")
    files = json.loads((tmp_path / goldens.INDEX).read_text())["files"]
    assert {entry["changed_by"] for entry in files.values()} == {"1.7"}


# --- Checking --------------------------------------------------------------------------------------------------------


def test_an_empty_directory_has_every_golden_missing(tmp_path: Path) -> None:
    assert goldens.check(tmp_path, FILES, GHOST) == [
        "index.json is missing from {}/ (HAR-14)".format(tmp_path.name),
        f"a.json is missing from {tmp_path.name}/ (HAR-14)", f"b.json is missing from {tmp_path.name}/ (HAR-14)"]


def test_a_golden_that_no_longer_matches_the_harness_is_named_with_its_first_line(tmp_path: Path) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    assert goldens.check(tmp_path, FILES | {"b.json": '{"y": 3}\n'}, GHOST) == [
        'b.json differs from the harness\'s output, line 1: golden "{"y": 2}", harness "{"y": 3}" (HAR-13, R-002)']


def test_a_golden_edited_by_hand_is_caught_even_when_the_harness_agrees_with_the_edit(tmp_path: Path) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    (tmp_path / "a.json").write_text("edited\n")
    assert goldens.check(tmp_path, FILES | {"a.json": "edited\n"}, GHOST) == [
        "a.json was edited by hand: its hash is not the index's"]


def test_a_golden_the_index_does_not_know_and_an_index_entry_with_no_golden_are_caught(tmp_path: Path) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    (tmp_path / "c.json").write_text("c\n")
    assert goldens.check(tmp_path, FILES | {"c.json": "c\n"}, GHOST) == ["c.json is not in index.json"]
    assert goldens.check(tmp_path, {"a.json": FILES["a.json"]}, GHOST) == [
        "b.json is in index.json and is no golden of the harness"]


def test_a_change_under_a_decision_that_is_no_longer_in_force_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trials, "HARNESS_VERSION", "2")
    goldens.write(tmp_path, FILES, GHOST)
    goldens.write(tmp_path, FILES | {"a.json": "new\n"}, GHOST, "R-020")
    files = FILES | {"a.json": "new\n"}
    assert goldens.check(tmp_path, files, GHOST.replace("R-020: Four\n- **Status:** in force", "R-020: Four\n- **Status:** proposed")) == [
        "a.json was changed by R-020, which is not in force in theGhost.md"]


def test_a_change_under_a_decision_needs_a_raised_harness_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    goldens.write(tmp_path, FILES | {"a.json": "new\n"}, GHOST, "R-020")
    files = FILES | {"a.json": "new\n"}
    assert goldens.check(tmp_path, files, GHOST) == [
        "a.json changed under a decision, and harness_version is still 1 (HAR-01, HAR-14)"]
    monkeypatch.setattr(trials, "HARNESS_VERSION", "2")
    goldens.write(tmp_path, files | {"b.json": "newer\n"}, GHOST, "R-020")
    assert goldens.check(tmp_path, files | {"b.json": "newer\n"}, GHOST) == []


def test_goldens_of_another_harness_version_are_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    monkeypatch.setattr(trials, "HARNESS_VERSION", "2")
    assert goldens.check(tmp_path, FILES, GHOST) == ["index.json is for harness version 1"]


# --- The baselines' goldens: held by their hashes, never recomputed (TODO 3.3, AGT-01) --------------------------------

HELD = {"baseline_zero.json": '{"baseline": "zero"}\n', "baseline_tree.json": '{"baseline": "tree"}\n'}


def index_of(directory: Path) -> dict[str, dict[str, str]]:
    return json.loads((directory / goldens.INDEX).read_text())["files"]


@pytest.mark.parametrize("name", ["baseline_zero.json", "baseline_tree.json", "baseline_a.json"])
def test_a_baseline_golden_is_held(name: str) -> None:
    assert goldens.is_held(name)


@pytest.mark.parametrize("name", ["synthetic_cells.json", "baseline_.json", "baseline_Zero.json", "baseline_zero.json.bak",
                                  "old_baseline_zero.json", "baseline_zero2.json", "index.json"])
def test_anything_else_is_not_held(name: str) -> None:
    assert not goldens.is_held(name)


def test_a_new_baseline_golden_is_written_by_a_step_and_indexed_beside_the_others(tmp_path: Path) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    assert goldens.write_held(tmp_path, HELD, GHOST, "3.3") == ["baseline_tree.json", "baseline_zero.json"]
    index = index_of(tmp_path)
    assert index["baseline_zero.json"] == {"sha256": goldens.sha256(HELD["baseline_zero.json"]), "changed_by": "3.3"}
    assert index["a.json"] == {"sha256": goldens.sha256(FILES["a.json"]), "changed_by": "1.7"}
    assert (tmp_path / "baseline_tree.json").read_text() == HELD["baseline_tree.json"]
    assert goldens.check(tmp_path, FILES, GHOST) == []


def test_baseline_goldens_may_be_the_first_files_of_a_directory(tmp_path: Path) -> None:
    goldens.write_held(tmp_path / "g", HELD, GHOST, "3.3")
    assert sorted(index_of(tmp_path / "g")) == sorted(HELD)
    assert json.loads((tmp_path / "g" / goldens.INDEX).read_text())["harness_version"] == trials.HARNESS_VERSION


def test_writing_the_others_keeps_the_baseline_goldens_and_their_entries(tmp_path: Path) -> None:
    goldens.write(tmp_path, FILES, GHOST)
    goldens.write_held(tmp_path, HELD, GHOST, "3.3")
    assert goldens.write(tmp_path, FILES | {"c.json": "c\n"}, GHOST, "R-002") == ["c.json"]
    assert (tmp_path / "baseline_zero.json").read_text() == HELD["baseline_zero.json"]
    assert index_of(tmp_path)["baseline_zero.json"]["changed_by"] == "3.3"
    assert goldens.write(tmp_path, FILES | {"c.json": "c\n"}, GHOST) == []


def test_writing_what_is_there_changes_no_baseline_golden(tmp_path: Path) -> None:
    goldens.write_held(tmp_path, HELD, GHOST, "3.3")
    before = (tmp_path / goldens.INDEX).read_text()
    assert goldens.write_held(tmp_path, HELD, GHOST, "3.3") == []
    assert (tmp_path / goldens.INDEX).read_text() == before


@pytest.mark.parametrize("changed_by", ["R-009", "R-003", "3", "3.3.1", "x3.3", "3.3x", ""])
def test_a_new_baseline_golden_needs_a_step_or_a_decision_in_force(tmp_path: Path, changed_by: str) -> None:
    with pytest.raises(goldens.GoldenChange, match=r"baseline_tree.json, baseline_zero.json would change: pass a step"):
        goldens.write_held(tmp_path, HELD, GHOST, changed_by)
    assert not (tmp_path / "baseline_zero.json").exists()


def test_a_new_baseline_golden_may_come_under_a_decision_in_force(tmp_path: Path) -> None:
    goldens.write_held(tmp_path, HELD, GHOST, "R-020")
    assert index_of(tmp_path)["baseline_tree.json"]["changed_by"] == "R-020"


def test_a_baseline_golden_that_would_differ_needs_a_decision_in_force_not_a_step(tmp_path: Path) -> None:
    goldens.write_held(tmp_path, HELD, GHOST, "3.3")
    changed = HELD | {"baseline_zero.json": '{"baseline": "zero", "x": 1}\n'}
    with pytest.raises(goldens.GoldenChange, match=r"baseline_zero.json would change: .*, not '3.3'"):
        goldens.write_held(tmp_path, changed, GHOST, "3.3")
    with pytest.raises(goldens.GoldenChange, match="not 'R-003'"):
        goldens.write_held(tmp_path, changed, GHOST, "R-003")
    assert (tmp_path / "baseline_zero.json").read_text() == HELD["baseline_zero.json"]
    assert goldens.write_held(tmp_path, changed, GHOST, "R-020") == ["baseline_zero.json"]
    index = index_of(tmp_path)
    assert index["baseline_zero.json"] == {"sha256": goldens.sha256(changed["baseline_zero.json"]), "changed_by": "R-020"}
    assert index["baseline_tree.json"]["changed_by"] == "3.3"
    assert goldens.check(tmp_path, {}, GHOST) == []


def test_a_golden_that_is_no_baseline_is_refused_by_write_held(tmp_path: Path) -> None:
    with pytest.raises(goldens.GoldenChange, match=r"^a.json, b.json is no baseline golden \(HAR-14\)$"):
        goldens.write_held(tmp_path, FILES | HELD, GHOST, "3.3")
    assert not (tmp_path / "baseline_zero.json").exists()


def test_baseline_goldens_are_checked_by_their_hashes_only(tmp_path: Path) -> None:
    goldens.write_held(tmp_path, HELD, GHOST, "3.3")
    assert goldens.check(tmp_path, {}, GHOST) == []
    assert goldens.check(tmp_path, FILES, GHOST) == [f"{name} is missing from {tmp_path.name}/ (HAR-14)" for name in FILES]


def test_a_baseline_golden_edited_by_hand_missing_or_unindexed_is_caught(tmp_path: Path) -> None:
    goldens.write_held(tmp_path, HELD, GHOST, "3.3")
    (tmp_path / "baseline_zero.json").write_text("edited\n")
    (tmp_path / "baseline_tree.json").unlink()
    (tmp_path / "baseline_new.json").write_text("new\n")
    (tmp_path / "baseline_Bad.json").write_text("not a baseline name\n")
    assert goldens.check(tmp_path, {}, GHOST) == [
        "baseline_new.json is not in index.json",
        f"baseline_tree.json is missing from {tmp_path.name}/ (HAR-14)",
        "baseline_zero.json was edited by hand: its hash is not the index's"]


def test_a_baseline_golden_changed_by_something_else_than_a_step_or_a_decision_in_force_is_caught(tmp_path: Path) -> None:
    goldens.write_held(tmp_path, HELD, GHOST, "R-020")
    assert goldens.check(tmp_path, {}, GHOST) == []
    assert goldens.check(tmp_path, {}, GHOST.replace("R-020: Four\n- **Status:** in force", "R-020: Four\n- **Status:** proposed")) == [
        "baseline_tree.json was changed by R-020, which is no TODO step and not in force in theGhost.md",
        "baseline_zero.json was changed by R-020, which is no TODO step and not in force in theGhost.md"]


def test_the_real_baseline_goldens_are_held_by_the_hashes_of_the_index(root: Path) -> None:
    directory = root / "harness" / "goldens"
    held, _ = goldens.split_index(directory)
    assert sorted(held) == ["baseline_momentum.json", "baseline_reversal.json", "baseline_tree.json", "baseline_zero.json"]
    assert {entry["changed_by"] for entry in held.values()} == {"3.3"}
    assert goldens.held_problems(directory, held, (root / "theGhost.md").read_text()) == []


def test_baseline_goldens_are_written_into_a_directory_that_has_no_parents_yet(tmp_path: Path) -> None:
    goldens.write_held(tmp_path / "harness" / "goldens", HELD, GHOST, "3.3")
    assert (tmp_path / "harness" / "goldens" / "baseline_zero.json").read_text() == HELD["baseline_zero.json"]
