"""Every number in docs/RESULTS.md has a trials line, both dispersions and a finding; a bare one is caught."""
from pathlib import Path

from scripts.checks import results

HEADER = "| Run | Horizon | Folds: mean ± sd [min, max] | Groups: mean ± sd [min, max] | Findings |\n| --- | --- | --- | --- | --- |\n"
TRIALS = "\t".join(results.TRIALS_COLUMNS) + "\nab12\t2026-11-01\t5\tIC\t0.02\t0.01\t3\t\n"
GOOD = "| ab12 | 5 | 0.02 ± 0.01 [0.00, 0.04] | 0.02 ± 0.02 [-0.01, 0.05] | NR-F-01 |\n"


def test_the_real_results_hold(root: Path) -> None:
    text = (root / "docs" / "RESULTS.md").read_text()
    assert results.problems(text, (root / "harness" / "trials.tsv").read_text()) == []


def test_an_empty_table_holds() -> None:
    assert results.problems(HEADER + "| *(none yet)* | | | | |\n", TRIALS) == []


def test_a_full_row_holds() -> None:
    assert results.problems(HEADER + GOOD, TRIALS) == []


def test_a_row_with_no_trials_line_is_caught() -> None:
    assert results.problems(HEADER + GOOD.replace("ab12", "cd34"), TRIALS) == ["cd34 has no line in harness/trials.tsv"]


def test_a_row_with_no_group_dispersion_is_caught() -> None:
    row = GOOD.replace("0.02 ± 0.02 [-0.01, 0.05]", "0.02")
    assert results.problems(HEADER + row, TRIALS) == ["ab12 has no dispersion on the groups axis (mean ± sd [min, max])"]


def test_a_row_citing_no_finding_is_caught() -> None:
    assert results.problems(HEADER + GOOD.replace("NR-F-01", "none"), TRIALS) == ["ab12 cites no finding (NR-F-nn)"]


def test_a_table_without_a_run_column_is_not_a_reported_number() -> None:
    scorer = "| Scorer | Agreement |\n| --- | --- |\n| haiku | 0.8 |\n"
    assert results.problems(scorer, TRIALS) == []


def test_a_wrong_trials_header_is_caught() -> None:
    assert results.problems(HEADER, "hash\tmean\n") == ["harness/trials.tsv's header is ['hash', 'mean'], not HAR-09's"]
