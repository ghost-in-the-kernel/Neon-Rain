"""Every number in docs/RESULTS.md has a trials line, both dispersions, a finding and a period; a bare one is caught,
and a WIKI run reported for one period only is caught (R-026)."""
from pathlib import Path

from scripts.checks import results

HEADER = "| Run | Horizon | Period | Folds: mean ± sd [min, max] | Groups: mean ± sd [min, max] | Findings |\n| --- | --- | --- | --- | --- | --- |\n"
TRIALS = "\t".join(results.TRIALS_COLUMNS) + "\nab12\t2026-11-01\t5\tIC\t0.02\t0.01\t3\t\n"
GOOD = "| ab12 | 5 | synthetic | 0.02 ± 0.01 [0.00, 0.04] | 0.02 ± 0.02 [-0.01, 0.05] | NR-F-01 |\n"


def test_the_real_results_hold(root: Path) -> None:
    text = (root / "docs" / "RESULTS.md").read_text()
    assert results.problems(text, (root / "harness" / "trials.tsv").read_text()) == []


def test_an_empty_table_holds() -> None:
    assert results.problems(HEADER + "| *(none yet)* | | | | | |\n", TRIALS) == []


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
    table = "| Run | Period | Folds: mean ± sd [min, max] |\n| --- | --- | --- |\n| ab12 | synthetic | 0.02 ± 0.01 [0.00, 0.04] |\n"
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


def test_a_row_naming_no_period_is_caught() -> None:
    assert results.problems(HEADER + GOOD.replace("synthetic", ""), TRIALS) == [
        "ab12 names no period (synthetic, survivor-only, from-2014-04-01)"
    ]


def test_a_row_naming_a_period_not_in_the_list_is_caught() -> None:
    assert results.problems(HEADER + GOOD.replace("synthetic", "pooled"), TRIALS) == [
        "ab12 names no period (synthetic, survivor-only, from-2014-04-01)"
    ]


def test_a_table_without_a_period_column_is_caught() -> None:
    table = "| Run | Groups: mean ± sd [min, max] | Folds: mean ± sd [min, max] | Findings |\n| --- | --- | --- | --- |\n" \
            "| ab12 | 0.02 ± 0.02 [-0.01, 0.05] | 0.02 ± 0.01 [0.00, 0.04] | NR-F-01 |\n"
    assert results.problems(table, TRIALS) == ["ab12 names no period (synthetic, survivor-only, from-2014-04-01)"]


def test_a_wiki_run_reported_for_both_periods_holds() -> None:
    rows = GOOD.replace("synthetic", "survivor-only") + GOOD.replace("synthetic", "from-2014-04-01")
    assert results.problems(HEADER + rows, TRIALS) == []


def test_a_wiki_run_reported_for_the_survivor_only_period_alone_is_caught() -> None:
    assert results.problems(HEADER + GOOD.replace("synthetic", "survivor-only"), TRIALS) == [
        "ab12 5 is reported for the survivor-only period only, not for the from-2014-04-01 (R-026)"
    ]


def test_a_wiki_run_reported_for_the_later_period_alone_is_caught() -> None:
    assert results.problems(HEADER + GOOD.replace("synthetic", "from-2014-04-01"), TRIALS) == [
        "ab12 5 is reported for the from-2014-04-01 period only, not for the survivor-only (R-026)"
    ]


def test_each_horizon_of_a_wiki_run_needs_both_periods() -> None:
    rows = (GOOD.replace("synthetic", "survivor-only") + GOOD.replace("synthetic", "from-2014-04-01")
            + GOOD.replace("synthetic", "survivor-only").replace("| 5 |", "| 21 |"))
    assert results.problems(HEADER + rows, TRIALS) == [
        "ab12 21 is reported for the survivor-only period only, not for the from-2014-04-01 (R-026)"
    ]


def test_each_metric_of_a_wiki_run_needs_both_periods() -> None:
    table = "| Run | Metric | Period | Folds | Groups | Findings |\n| --- | --- | --- | --- | --- | --- |\n"
    body = "| ab12 | IC | survivor-only | 1 ± 0 [1, 1] | 1 ± 0 [1, 1] | NR-F-03 |\n" \
           "| ab12 | Sharpe | from-2014-04-01 | 1 ± 0 [1, 1] | 1 ± 0 [1, 1] | NR-F-03 |\n"
    assert results.problems(table + body, TRIALS) == [
        "ab12 IC is reported for the survivor-only period only, not for the from-2014-04-01 (R-026)",
        "ab12 Sharpe is reported for the from-2014-04-01 period only, not for the survivor-only (R-026)",
    ]


def test_a_synthetic_run_needs_no_second_period() -> None:
    assert results.problems(HEADER + GOOD + GOOD.replace("5", "21", 1), TRIALS) == []


def test_a_row_with_no_run_and_one_period_is_named_by_a_question_mark() -> None:
    row = GOOD.replace("| ab12 |", "|  |").replace("synthetic", "survivor-only")
    assert "? 5 is reported for the survivor-only period only, not for the from-2014-04-01 (R-026)" in results.problems(
        HEADER + row, TRIALS
    )


# --- A model's periods are paired by the model, though each period's run has its own hash ---------------------------

MODEL_HEADER = ("| Run | Model | Horizon | Period | Folds: mean ± sd [min, max] | Groups: mean ± sd [min, max] | Findings |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n")
TWO_RUNS = TRIALS + "cd34\t2026-11-01\t5\tIC\t0.02\t0.01\t3\t\n"
MODEL_ROW = "| ab12 | zero | 5 | survivor-only | 0.02 ± 0.01 [0.00, 0.04] | 0.02 ± 0.02 [-0.01, 0.05] | NR-F-03 |\n"


def test_a_model_with_a_run_for_each_period_holds() -> None:
    later = MODEL_ROW.replace("ab12", "cd34").replace("survivor-only", "from-2014-04-01")
    assert results.problems(MODEL_HEADER + MODEL_ROW + later, TWO_RUNS) == []


def test_a_model_reported_for_one_period_only_is_named_by_the_model() -> None:
    assert results.problems(MODEL_HEADER + MODEL_ROW, TWO_RUNS) == [
        "zero 5 is reported for the survivor-only period only, not for the from-2014-04-01 (R-026)"
    ]


def test_two_models_with_the_same_run_cell_are_not_paired_with_each_other() -> None:
    other = MODEL_ROW.replace("zero", "tree").replace("survivor-only", "from-2014-04-01")
    assert results.problems(MODEL_HEADER + MODEL_ROW + other, TRIALS) == [
        "zero 5 is reported for the survivor-only period only, not for the from-2014-04-01 (R-026)",
        "tree 5 is reported for the from-2014-04-01 period only, not for the survivor-only (R-026)",
    ]


def test_a_run_with_no_model_cell_is_named_by_its_run() -> None:
    assert results.label({"Run": "ab12", "Model": "", "Horizon": "5", "Metric": "IC"}) == "ab12 5 IC"
    assert results.label({"Run": "ab12", "Model": "zero", "Horizon": "5"}) == "zero 5"
