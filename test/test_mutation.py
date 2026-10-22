"""precommit.sh's survivor rule: a survivor without a docs/MUTATION.md line is refused (TODO 0.5, R-015a)."""
from scripts.checks import mutation

RESULTS = "    a.x_f__mutmut_1: killed\n    a.x_f__mutmut_2: survived\n    a.x_g__mutmut_1: timeout\n"
DOC = "| Id | File : line |\n| --- | --- |\n| `a.x_f__mutmut_2` | a.py:3 |\n"


def test_survivors_are_everything_not_killed() -> None:
    assert mutation.survivors(RESULTS) == ["a.x_f__mutmut_2", "a.x_g__mutmut_1"]


def test_an_unfinished_run_counts_as_survivors() -> None:
    assert mutation.survivors("    a.x_f__mutmut_9: not checked\n") == ["a.x_f__mutmut_9"]


def test_an_explained_survivor_passes_and_an_unexplained_one_is_refused() -> None:
    assert mutation.unexplained(RESULTS, DOC) == ["a.x_g__mutmut_1"]


def test_the_placeholder_row_explains_nothing() -> None:
    assert mutation.explained("| *(none yet)* | | |\n") == set()


def test_an_explanation_for_a_mutant_that_no_longer_survives_is_stale() -> None:
    assert mutation.stale("    a.x_f__mutmut_2: killed\n", DOC) == ["a.x_f__mutmut_2"]
    assert mutation.stale(RESULTS, DOC) == []


def test_a_line_that_is_not_a_result_is_ignored() -> None:
    assert mutation.survivors("Running mutation testing\n\n    a.x_f__mutmut_1: survived\n") == ["a.x_f__mutmut_1"]
