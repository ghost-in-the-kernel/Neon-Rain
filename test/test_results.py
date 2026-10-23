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
    assert results.problems(HEADER, "hash\tmean\n") == ["harness/trials.tsv's header is 'hash\\tmean', not HAR-09's"]


def test_an_empty_trials_file_is_caught() -> None:
    assert results.problems(HEADER, "") == ["harness/trials.tsv's header is '', not HAR-09's"]


def test_every_bad_row_is_reported() -> None:
    rows = GOOD.replace("ab12", "cd34") + GOOD.replace("ab12", "ef56")
    assert results.problems(HEADER + rows, TRIALS) == [
        "cd34 has no line in harness/trials.tsv", "ef56 has no line in harness/trials.tsv"
    ]


def test_a_row_with_no_run_is_named_by_a_question_mark() -> None:
    found = results.problems(HEADER + GOOD.replace("| ab12 |", "|  |"), TRIALS)
    assert found == ["? has no line in harness/trials.tsv"]


def test_a_table_without_a_groups_or_findings_column_is_caught() -> None:
    table = "| Run | Folds: mean ± sd [min, max] |\n| --- | --- |\n| ab12 | 0.02 ± 0.01 [0.00, 0.04] |\n"
    assert results.problems(table, TRIALS) == [
        "ab12 has no dispersion on the groups axis (mean ± sd [min, max])", "ab12 cites no finding (NR-F-nn)"
    ]


def test_a_short_row_reads_its_missing_cells_as_empty() -> None:
    assert results.reported_rows(HEADER + "| ab12 | 5 |\n") == [{"Run": "ab12", "Horizon": "5"}]


def test_tables_are_read_separately() -> None:
    text = "| Scorer | x |\n| --- | --- |\n| a | b |\n\nprose\n\n" + HEADER + GOOD
    assert [row["Run"] for row in results.reported_rows(text)] == ["ab12"]


def test_trial_hashes_are_the_first_column_without_the_header() -> None:
    assert results.trial_hashes(TRIALS + "cd 34\tx\n") == {"ab12", "cd 34"}


def test_rows_of_every_run_table_are_read() -> None:
    text = HEADER + GOOD + "\n" + HEADER + GOOD.replace("ab12", "cd34")
    assert [row["Run"] for row in results.reported_rows(text)] == ["ab12", "cd34"]
