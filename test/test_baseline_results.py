"""TODO 3.3: the baselines' goldens and RESULTS.md's baseline table are what harness/trials.tsv's lines say (HAR-13).

The parsing, the golden and the table are tried on a small invented trials text; the real goldens and the real table
are held to the real trials.tsv (text only: no market data is read, AGT-01).
"""
import json
from pathlib import Path

import pytest

from neonrain.harness.trials import TRIALS_COLUMNS
from neonrain.universe.periods import FROM_BOUNDARY, SURVIVOR_ONLY
from scripts.checks import baseline_results as br

COUNTS = "period={}; cells=4; test_rows=100; dropped_missing=1; dropped_ties=2; dropped_thin_dates=0; delisting_ends=3 (whole sample)"
DISPERSION = "folds: {m} ± 0.5 [0.25, 0.75] n=4; groups: {m} ± 0.125 [0.0625, 0.875] n=2; undefined_cells=0"
RUNS = {SURVIVOR_ONLY: ("aaaa", "2026-11-02"), FROM_BOUNDARY: ("bbbb", "2026-11-02")}


def make_line(config: str, date: str, period: str, horizon: int, metric: str, mean: str, flat: bool = False,
              fits: bool = False, so_far: int = 0) -> str:
    """One invented trials line; `flat` makes it the IC of a score with every date flat (no number)."""
    if flat:
        note = "no number: no cell has this metric defined; " + COUNTS.format(period) + "; IC dates=0; dropped_thin=0; dropped_flat=5"
        return "\t".join([config, date, str(horizon), metric, "", "folds: undefined; groups: undefined; undefined_cells=4",
                          str(so_far), note])
    note = COUNTS.format(period)
    if metric == "IC":
        note += "; IC dates=7; dropped_thin=1; dropped_flat=2"
    if metric == "DSR":
        note += "; N=9; V=0.25 (from the Sharpe_10bps lines)"
    dispersion = DISPERSION.format(m=mean) + ("; fits names" if fits else "")
    return "\t".join([config, date, str(horizon), metric, mean, dispersion, str(so_far), note])


def make_run(config: str, date: str, period: str, flat_ic_at: int | None = None, so_far: int = 0) -> list[str]:
    """Seven lines for each of the horizons 3 and 5. Means are 0.25 * (metric number + 1) + horizon number, but the DSR
    is 0.5 at the first horizon and 0.95 (the bar, exactly) at the second; the IC at the second horizon fits names."""
    lines = []
    for index, horizon in enumerate((3, 5)):
        for number, metric in enumerate(br.METRICS):
            mean = str(0.5 if metric == "DSR" and index == 0 else 0.95 if metric == "DSR" else 0.25 * (number + 1) + index)
            lines.append(make_line(config, date, period, horizon, metric, mean, flat=flat_ic_at == horizon and metric == "IC",
                                   fits=metric == "IC" and index == 1, so_far=so_far + len(lines)))
    return lines


def make_trials() -> str:
    """The header, an older run of aaaa (other numbers), the two runs of RUNS (the first period's IC flat at horizon 3),
    and a run of another hash that starts with the same letters."""
    older = [line.replace("2026-11-02", "2026-11-01").replace("\t0.25\t", "\t0.75\t") for line in
             make_run("aaaa", "2026-11-02", SURVIVOR_ONLY)]
    lines = [*older, *make_run("aaaa", "2026-11-02", SURVIVOR_ONLY, flat_ic_at=3, so_far=100),
             *make_run("bbbb", "2026-11-02", FROM_BOUNDARY, so_far=200), *make_run("aaaab", "2026-11-02", SURVIVOR_ONLY)]
    return "\n".join(["\t".join(TRIALS_COLUMNS), *lines]) + "\n"


@pytest.fixture
def trials() -> str:
    return make_trials()


# --- Reading a line --------------------------------------------------------------------------------------------------


def test_an_axis_is_read_with_its_exponents_and_signs() -> None:
    assert br.parse_axis("folds: -9.5e-07 ± 1e-05 [-0.5, 2.0] n=25") == {
        "mean": -9.5e-07, "sd": 1e-05, "low": -0.5, "high": 2.0, "n": 25}


def test_an_undefined_axis_is_none_and_an_undefined_sd_is_none() -> None:
    assert br.parse_axis("folds: undefined") is None
    assert br.parse_axis("groups: 0.5 ± undefined [0.5, 0.5] n=1") == {
        "mean": 0.5, "sd": None, "low": 0.5, "high": 0.5, "n": 1}


def test_a_dispersion_is_read_whole() -> None:
    found = br.parse_dispersion("folds: 0.5 ± 0.25 [0.25, 0.75] n=4; groups: 0.5 ± 0.125 [0.0625, 0.875] n=2; undefined_cells=3")
    assert found == {"folds": {"mean": 0.5, "sd": 0.25, "low": 0.25, "high": 0.75, "n": 4},
                     "groups": {"mean": 0.5, "sd": 0.125, "low": 0.0625, "high": 0.875, "n": 2},
                     "undefined_cells": 3, "fits_names": False}


def test_a_dispersion_with_the_fits_names_flag_and_an_undefined_one() -> None:
    assert br.parse_dispersion(DISPERSION.format(m="0.5") + "; fits names")["fits_names"] is True
    assert br.parse_dispersion("folds: undefined; groups: undefined; undefined_cells=125") == {
        "folds": None, "groups": None, "undefined_cells": 125, "fits_names": False}


@pytest.mark.parametrize("text", ["f: undefined; groups: undefined; undefined_cells=1",
                                  "folds: undefined; g: undefined; undefined_cells=1",
                                  "folds: undefined; groups: undefined; undefined=1", ""])
def test_a_dispersion_that_is_not_the_column_is_refused(text: str) -> None:
    with pytest.raises((ValueError, IndexError)):
        br.parse_dispersion(text)


def test_a_dispersion_refusal_names_the_text() -> None:
    with pytest.raises(ValueError, match="not HAR-09's dispersion column: 'folds: x; groups: y; z'"):
        br.parse_dispersion("folds: x; groups: y; z")


def test_a_value_is_the_number_it_spells_else_its_text() -> None:
    assert br.typed("686") == 686 and isinstance(br.typed("686"), int)
    assert br.typed("-3") == -3
    assert br.typed("0.5") == 0.5 and isinstance(br.typed("0.5"), float)
    assert br.typed("1e-05") == 1e-05
    assert br.typed("from-2014-04-01") == "from-2014-04-01"


def test_a_note_is_read_by_its_keys() -> None:
    note = COUNTS.format(SURVIVOR_ONLY) + "; IC dates=15710; dropped_thin=0; dropped_flat=15710"
    assert br.parse_note(note) == {"period": "survivor-only", "cells": 4, "test_rows": 100, "dropped_missing": 1,
                                   "dropped_ties": 2, "dropped_thin_dates": 0, "delisting_ends": 3, "IC_dates": 15710,
                                   "dropped_thin": 0, "dropped_flat": 15710}


def test_a_notes_deflated_sharpe_and_its_reason_for_no_number() -> None:
    assert br.parse_note("N=41; V=0.5 (from the Sharpe_10bps lines)") == {"N": 41, "V": 0.5}
    assert br.parse_note("no number: no cell has this metric defined; cells=4") == {
        "no_number": "no cell has this metric defined", "cells": 4}


def test_a_line_is_read_with_its_number_and_its_columns() -> None:
    found = br.parse_line(7, make_line("aaaa", "2026-11-02", SURVIVOR_ONLY, 5, "IC", "0.5", fits=True, so_far=12))
    assert found == {"line": 7, "config_hash": "aaaa", "date": "2026-11-02", "horizon": 5, "metric": "IC", "mean": 0.5,
                     "trials_so_far": 12, "folds": {"mean": 0.5, "sd": 0.5, "low": 0.25, "high": 0.75, "n": 4},
                     "groups": {"mean": 0.5, "sd": 0.125, "low": 0.0625, "high": 0.875, "n": 2}, "undefined_cells": 0,
                     "fits_names": True, "note": br.parse_note(COUNTS.format(SURVIVOR_ONLY) + "; IC dates=7; dropped_thin=1; dropped_flat=2")}


def test_a_line_with_no_mean_has_none() -> None:
    found = br.parse_line(2, make_line("aaaa", "2026-11-02", SURVIVOR_ONLY, 3, "IC", "", flat=True))
    assert found["mean"] is None and found["folds"] is None


def test_a_line_of_the_wrong_width_is_refused_with_its_number() -> None:
    with pytest.raises(ValueError, match=r"harness/trials.tsv line 9 has 2 columns, not 8"):
        br.parse_line(9, "a\tb")


# --- Choosing a run --------------------------------------------------------------------------------------------------


def test_a_run_is_the_lines_of_its_hash_and_date_only(trials: str) -> None:
    lines = br.run_lines(trials, "aaaa", "2026-11-02")
    assert len(lines) == 14 and {line["config_hash"] for line in lines} == {"aaaa"} and {line["date"] for line in lines} == {"2026-11-02"}
    assert [line["line"] for line in lines][:2] == [16, 17]  # the header is line 1 and the older run's 14 lines follow


def test_a_run_is_not_the_header_row_nor_a_hash_that_starts_alike() -> None:
    header = "\t".join(TRIALS_COLUMNS)
    text = header + "\n" + make_line("config_hash", "date", SURVIVOR_ONLY, 3, "accuracy", "0.5") + "\n"
    assert [line["line"] for line in br.run_lines(text, "config_hash", "date")] == [2]
    with pytest.raises(ValueError):
        br.run_lines(text.replace("config_hash\tdate", "config_hash\tdated"), "config_hash", "date")


def test_a_run_with_no_line_is_refused_by_name(trials: str) -> None:
    with pytest.raises(ValueError, match="harness/trials.tsv has no line of aaaa on 2026-12-01"):
        br.run_lines(trials, "aaaa", "2026-12-01")


# --- The golden ------------------------------------------------------------------------------------------------------


def test_a_golden_holds_each_period_each_horizon_each_metric(trials: str) -> None:
    found = json.loads(br.golden(trials, "zero", RUNS))
    assert sorted(found) == ["baseline", "runs", "source"] and found["baseline"] == "zero"
    assert found["source"] == "harness/trials.tsv" and sorted(found["runs"]) == [FROM_BOUNDARY, SURVIVOR_ONLY]
    run = found["runs"][SURVIVOR_ONLY]
    assert run["config_hash"] == "aaaa" and run["date"] == "2026-11-02" and sorted(run["horizons"]) == ["3", "5"]
    assert run["horizons"]["3"]["counts"] == {"period": SURVIVOR_ONLY, "cells": 4, "test_rows": 100, "dropped_missing": 1,
                                              "dropped_ties": 2, "dropped_thin_dates": 0, "delisting_ends": 3}
    assert sorted(run["horizons"]["5"]["metrics"]) == sorted(br.METRICS)


def test_a_metric_of_a_golden_keeps_its_line_numbers_and_what_is_not_a_count(trials: str) -> None:
    run = json.loads(br.golden(trials, "zero", RUNS))["runs"][SURVIVOR_ONLY]
    metrics = run["horizons"]["5"]["metrics"]
    assert metrics["accuracy"] == {
        "line": 23, "mean": 1.25, "trials_so_far": 107, "undefined_cells": 0, "extra": {}, "fits_names": False,
        "folds": {"mean": 1.25, "sd": 0.5, "low": 0.25, "high": 0.75, "n": 4},
        "groups": {"mean": 1.25, "sd": 0.125, "low": 0.0625, "high": 0.875, "n": 2}}
    assert metrics["IC"]["extra"] == {"IC_dates": 7, "dropped_thin": 1, "dropped_flat": 2} and metrics["IC"]["fits_names"] is True
    assert metrics["DSR"]["extra"] == {"N": 9, "V": 0.25} and metrics["DSR"]["mean"] == 0.95
    assert metrics["Sharpe_10bps"]["line"] == 27


def test_a_metric_with_no_number_is_kept_as_none(trials: str) -> None:
    ic = json.loads(br.golden(trials, "zero", RUNS))["runs"][SURVIVOR_ONLY]["horizons"]["3"]["metrics"]["IC"]
    assert ic["mean"] is None and ic["folds"] is None and ic["undefined_cells"] == 4
    assert ic["extra"] == {"IC_dates": 0, "dropped_thin": 0, "dropped_flat": 5, "no_number": "no cell has this metric defined"}


def test_a_golden_is_sorted_indented_and_ends_with_a_line_break() -> None:
    assert br.dumped({"b": 1, "a": [0.5]}) == '{\n "a": [\n  0.5\n ],\n "b": 1\n}\n'
    with pytest.raises(ValueError):
        br.dumped({"a": float("nan")})


def test_a_float_is_written_with_every_digit_the_line_had() -> None:
    assert br.dumped({"a": 0.5000258392710355, "b": 9.591936759124723e-07}) == '{\n "a": 0.5000258392710355,\n "b": 9.591936759124723e-07\n}\n'


def test_lines_that_disagree_on_a_horizons_counts_are_refused(trials: str) -> None:
    lines = trials.splitlines()
    index = next(n for n, line in enumerate(lines) if line.startswith("aaaa\t2026-11-02\t5\taccuracy"))
    lines[index] = lines[index].replace("cells=4", "cells=5")
    with pytest.raises(ValueError, match="the lines of horizon 5 disagree on the counts"):
        br.golden("\n".join(lines) + "\n", "zero", RUNS)


def test_a_metric_twice_in_a_horizon_is_refused(trials: str) -> None:
    lines = trials.splitlines()
    index = next(n for n, line in enumerate(lines) if line.startswith("aaaa\t2026-11-02\t5\taccuracy"))
    with pytest.raises(ValueError, match="horizon 5 has a metric twice"):
        br.golden("\n".join([*lines, lines[index]]) + "\n", "zero", RUNS)


def test_a_run_whose_lines_state_another_period_is_refused(trials: str) -> None:
    with pytest.raises(ValueError, match="bbbb on 2026-11-02 is not a run of the survivor-only period"):
        br.golden(trials, "zero", {SURVIVOR_ONLY: ("bbbb", "2026-11-02")})


def test_golden_names() -> None:
    assert br.golden_name("zero") == "baseline_zero.json"


def test_goldens_are_checked_against_the_lines(trials: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(br, "BASELINES", {"zero": RUNS, "tree": RUNS})
    texts = {br.golden_name(name): br.golden(trials, name, RUNS) for name in ("zero", "tree")}
    assert br.golden_problems(trials, texts) == []
    assert br.golden_problems(trials, texts | {"baseline_tree.json": texts["baseline_tree.json"] + " "}) == [
        "baseline_tree.json is not what the lines of harness/trials.tsv give"]
    assert br.golden_problems(trials, {"baseline_zero.json": texts["baseline_zero.json"]}) == [
        "baseline_tree.json is not what the lines of harness/trials.tsv give"]


# --- The table -------------------------------------------------------------------------------------------------------


@pytest.fixture
def texts(trials: str, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setattr(br, "BASELINES", {"zero": RUNS, "tree": RUNS})
    return {br.golden_name(name): br.golden(trials, name, RUNS) for name in ("zero", "tree")}


def test_an_axis_cell_keeps_the_digits_and_says_undefined() -> None:
    axis = {"mean": 0.5000258392710355, "sd": None, "low": 0.25, "high": 9.5e-07, "n": 25}
    assert br.axis_cell(axis) == "0.5000258392710355 ± undefined [0.25, 9.5e-07] n=25"
    assert br.axis_cell({**axis, "sd": 0.125}) == "0.5000258392710355 ± 0.125 [0.25, 9.5e-07] n=25"
    assert br.axis_cell(None) == "undefined"


def test_findings_are_the_periods_then_the_models() -> None:
    assert br.findings("zero", SURVIVOR_ONLY) == "NR-F-03, NR-F-10"
    assert br.findings("tree", FROM_BOUNDARY) == "NR-F-04"
    assert br.findings("reversal", FROM_BOUNDARY) == "NR-F-04, NR-F-09"


def test_a_dsr_cell_says_n_v_and_which_side_of_the_bar() -> None:
    entry = {"extra": {"N": 9, "V": 0.25}, "mean": 0.9499999}
    assert br.dsr_cell("DSR", entry) == "N=9, V=0.25; below 0.95"
    assert br.dsr_cell("DSR", {**entry, "mean": 0.95}) == "N=9, V=0.25; at or above 0.95"
    assert br.dsr_cell("IC", entry) == ""


def test_the_rows_of_a_golden_run_by_horizon_then_period_then_metric(texts: dict[str, str]) -> None:
    found = [line.split(" | ")[0:5] for line in br.rows("zero", texts["baseline_zero.json"])]
    wanted = [metric for metric in br.METRICS]
    expected = [[f"| {run}", "zero", str(horizon), period, metric] for horizon in (3, 5)
                for period, run in ((SURVIVOR_ONLY, "aaaa"), (FROM_BOUNDARY, "bbbb")) for metric in wanted]
    expected.remove(["| aaaa", "zero", "3", SURVIVOR_ONLY, "IC"])  # the one line with no number has no row
    assert found == expected


def test_a_row_is_the_run_the_model_the_cells_and_the_findings(texts: dict[str, str]) -> None:
    rows = br.rows("tree", texts["baseline_tree.json"])
    assert rows[0] == ("| aaaa | tree | 3 | survivor-only | accuracy | 0.25 ± 0.5 [0.25, 0.75] n=4 "
                       "| 0.25 ± 0.125 [0.0625, 0.875] n=2 |  | - | NR-F-03 |")
    ic = next(row for row in rows if row.startswith("| aaaa | tree | 5 | survivor-only | IC "))
    assert ic == "| aaaa | tree | 5 | survivor-only | IC | 1.75 ± 0.5 [0.25, 0.75] n=4 | 1.75 ± 0.125 [0.0625, 0.875] n=2 *fits names* |  | - | NR-F-03 |"
    sharpe = next(row for row in rows if row.startswith("| bbbb | tree | 3 | from-2014-04-01 | Sharpe_25bps "))
    assert sharpe.endswith("|  | 25 bps | NR-F-04 |")
    dsr = next(row for row in rows if row.startswith("| bbbb | tree | 5 | from-2014-04-01 | DSR "))
    assert dsr.endswith("| N=9, V=0.25; at or above 0.95 | 10 bps | NR-F-04 |")


def test_the_table_is_the_header_the_rule_and_the_rows_of_each_baseline_in_order(texts: dict[str, str]) -> None:
    lines = br.table(texts).splitlines()
    assert lines[0] == br.HEADER and lines[1] == "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    assert lines[2:] == br.rows("zero", texts["baseline_zero.json"]) + br.rows("tree", texts["baseline_tree.json"])
    assert br.table(texts).endswith("|\n")


def test_results_holds_the_table_exactly_or_is_caught(texts: dict[str, str]) -> None:
    table = br.table(texts)
    message = ["docs/RESULTS.md's baseline table is not what the baseline goldens give"]
    assert br.table_problems("# Results\n\nprose\n\n" + table + "\nmore\n", texts) == []
    assert br.table_problems("# Results\n", texts) == message
    assert br.table_problems(table.replace("0.25", "0.26", 1), texts) == message
    assert br.table_problems(table + table.replace("aaaa", "cccc"), texts) == message
    assert br.table_problems("| Run | Other |\n| --- | --- |\n| a | b |\n\n" + table, texts) == []


# --- The real ones ---------------------------------------------------------------------------------------------------


def real_texts(root: Path) -> dict[str, str]:
    return {br.golden_name(name): (root / "harness" / "goldens" / br.golden_name(name)).read_text() for name in br.BASELINES}


def test_the_real_goldens_are_what_the_trials_lines_give(root: Path) -> None:
    trials = (root / "harness" / "trials.tsv").read_text()
    assert br.golden_problems(trials, real_texts(root)) == []


def test_the_real_results_table_is_what_the_goldens_give(root: Path) -> None:
    assert br.table_problems((root / "docs" / "RESULTS.md").read_text(), real_texts(root)) == []


def test_the_four_baselines_and_their_runs_are_the_ones_3_3_names() -> None:
    assert list(br.BASELINES) == ["zero", "momentum", "reversal", "tree"]
    assert all(list(runs) == [SURVIVOR_ONLY, FROM_BOUNDARY] for runs in br.BASELINES.values())


def test_a_value_holding_an_equals_sign_or_a_leading_space_is_read_from_its_first_one() -> None:
    assert br.parse_note("k=v (a=b)") == {"k": "v"}
    assert br.parse_note("k= 3") == {"k": ""}


def test_a_horizon_of_one_line_has_its_counts() -> None:
    line = br.parse_line(2, make_line("aaaa", "2026-11-02", SURVIVOR_ONLY, 3, "accuracy", "0.5"))
    assert br.horizon_entry(3, [line])["counts"] == {"period": SURVIVOR_ONLY, "cells": 4, "test_rows": 100, "dropped_missing": 1,
                                                     "dropped_ties": 2, "dropped_thin_dates": 0, "delisting_ends": 3}
