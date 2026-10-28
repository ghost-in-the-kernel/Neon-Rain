"""The baseline runner (TODO 3.1 a) on the synthetic market, never real data: it gives the harness's own numbers, splits
a run at the period boundary, and leaves one trials line per (period, horizon, metric). Trials go to temporary files
only: harness/trials.tsv is an append-only record (HAR-09)."""
import re
import statistics
from datetime import date, timedelta
from functools import partial
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from neonrain import targets
from neonrain.baselines import record, runner, zero
from neonrain.harness import goldens, metrics, portfolio, split, synthetic, trials
from neonrain.harness.dispersion import Axis, Dispersion
from neonrain.harness.market import StampRefused
from neonrain.universe import periods

DAY = date(2026, 10, 27)
GEOMETRY = {"embargo": 63, "step": 40, "min_train": 100, "window": None}
MIN_TICKERS = 5
CONFIG = synthetic.MarketConfig(tickers=60, days=330, rho=0.1, delist_below=0.5, seed=3)
HORIZONS = (3, 63)
KEYS = ["ticker", "date"]


def run_of(changes: dict[str, object] | None = None) -> runner.Run:
    """The small market's run: two folds, a ticker group of 12 (so min_tickers 5), two horizons."""
    base = {"name": "zero", "feature_columns": [], "data_manifest": {"synthetic": "seed-3"}, "geometry": GEOMETRY,
            "min_tickers": MIN_TICKERS, "horizons": HORIZONS}
    return runner.Run(**{**base, **(changes or {})})  # type: ignore[arg-type]


def shifted(market: synthetic.Market, days: int) -> synthetic.Market:
    """The market `days` calendar days later, every frame and the calendar together; a multiple of 7 keeps weekdays."""
    later = pl.col("date") + pl.duration(days=days)
    return market._replace(prices=market.prices.with_columns(later), universe=market.universe.with_columns(later),
                           features=market.features.with_columns(later),
                           calendar=[day + timedelta(days=days) for day in market.calendar])


def across_boundary(market: synthetic.Market) -> synthetic.Market:
    """The market moved so the period boundary falls inside the first fold's test span (position 246 of 226 to 266)."""
    return shifted(market, (periods.BOUNDARY - market.calendar[246]).days // 7 * 7)


def period_dates(moved: synthetic.Market, fold: int, period: str) -> list[date]:
    """The test dates of a fold (spans 226 to 266 and 266 to 306) on one side of the boundary."""
    start = 226 + 40 * fold
    return [d for d in moved.calendar[start:start + 40] if (d < periods.BOUNDARY) == (period == periods.SURVIVOR_ONLY)]


def evaluated(market: synthetic.Market, scores: pl.DataFrame, run: runner.Run) -> dict[int, runner.Horizon]:
    """The runner on a market and a score frame, with the labels of HAR-02 bound in."""
    found = runner.scored_market(market.prices, market.universe, market.calendar, scores)
    return runner.evaluate(found, partial(targets.labels, market.prices, market.universe, market.calendar,
                                          min_tickers=run.min_tickers), run)


@pytest.fixture(scope="module")
def market() -> synthetic.Market:
    return synthetic.generate(CONFIG)


def test_a_cell_is_the_goldens_cell() -> None:
    """The runner's numbers for each (fold, group) cell are `goldens.cell_numbers`'s, same scores and same groups."""
    big = synthetic.generate(synthetic.MarketConfig(tickers=120, days=330, rho=0.1, delist_below=0.5, seed=7))
    scored = goldens.edge_scores(big)
    scores = scored.with_columns(stamp=pl.col("date"))
    run = run_of({"group_seed": goldens.GROUP_SEED, "min_tickers": targets.MIN_TICKERS, "horizons": (5,)})
    got = evaluated(big, scores, run)[5]
    assert got.cells[periods.FROM_BOUNDARY] == [] and len(got.cells[periods.SURVIVOR_ONLY]) == 10
    rows = targets.labels(big.prices, big.universe, big.calendar, 5).frame.join(scored, on=KEYS)
    folds = {fold.number: fold for fold in split.folds(len(big.calendar), **{k: GEOMETRY[k] for k in list(GEOMETRY)[:3]})}
    for cell in got.cells[periods.SURVIVOR_ONLY]:
        want = goldens.cell_numbers(big, rows, scored, folds[cell.fold], cell.group, 5)
        assert (cell.accuracy, cell.balanced_accuracy, cell.test_rows) == (
            want["accuracy"], want["balanced_accuracy"], want["test_rows"])
        assert cell.ic._asdict() == want["ic"]
        for bps in portfolio.COST_LEVELS_BPS:
            assert metrics.sharpe(cell.nets[bps]) == want[f"sharpe_{int(bps)}bps"]


def check_each_period_has_the_test_rows_on_its_side_of_the_boundary(market: synthetic.Market,
                                                                   zero_run: dict[int, runner.Horizon]) -> None:
    moved = across_boundary(market)
    spans = split.folds(len(moved.calendar), **{k: GEOMETRY[k] for k in list(GEOMETRY)[:3]})
    assert [(f.test_start, f.test_end) for f in spans] == [(226, 266), (266, 306)]
    where = {day: i for i, day in enumerate(moved.calendar)}
    for horizon, part in zero_run.items():
        rows = targets.labels(moved.prices, moved.universe, moved.calendar, horizon, MIN_TICKERS).frame
        for period, before in ((periods.SURVIVOR_ONLY, True), (periods.FROM_BOUNDARY, False)):
            want = [d for d in rows["date"] if 226 <= where[d] < 306 and (d < periods.BOUNDARY) == before]
            assert sum(c.test_rows for c in part.cells[period]) == len(want) > 0
        assert {c.fold for c in part.cells[periods.SURVIVOR_ONLY]} == {0}  # fold 0 straddles the boundary
        assert {c.fold for c in part.cells[periods.FROM_BOUNDARY]} == {0, 1}


def check_a_period_cell_is_the_metric_of_that_periods_rows_only(market: synthetic.Market,
                                                               zero_run: dict[int, runner.Horizon]) -> None:
    moved = across_boundary(market)
    scores = zero.scores(moved.universe)
    rows = targets.labels(moved.prices, moved.universe, moved.calendar, 3, MIN_TICKERS).frame.join(scores, on=KEYS)
    held = [t for t, g in split.ticker_groups(scores["ticker"].unique().to_list(), 5, 0).items() if g == 2]
    for period in runner.PERIOD_NAMES:
        mine = rows.filter(pl.col("ticker").is_in(held) & pl.col("date").is_in(period_dates(moved, 0, period)))
        cell = next(c for c in zero_run[3].cells[period] if (c.fold, c.group) == (0, 2))
        assert 0 < cell.test_rows == mine.height and cell.accuracy == metrics.accuracy(mine)


def test_zero_scores_are_one_half_for_every_universe_cell(market: synthetic.Market) -> None:
    found = zero.scores(market.universe)
    assert found.columns == ["ticker", "date", "score", "stamp"] and found.height == market.universe.height
    assert found["score"].to_list() == [0.5] * found.height and found["stamp"].to_list() == found["date"].to_list()
    assert found.select("ticker", "date").equals(market.universe)


def check_the_zero_baseline_has_the_shape_the_harness_gives_a_constant(zero_run: dict[int, runner.Horizon]) -> None:
    for part in zero_run.values():
        for cells in part.cells.values():
            for cell in cells:
                assert cell.balanced_accuracy == 0.5 and cell.ic.mean is None  # predicts 0 everywhere; no IC exists
                assert cell.ic.dates == 0 and cell.ic.dropped_thin == 0 and cell.ic.dropped_flat > 0
                assert set(cell.nets) == {0.0, 10.0, 25.0}


def check_zero_accuracy_is_the_share_of_down_labels(market: synthetic.Market, zero_run: dict[int, runner.Horizon]) -> None:
    moved = across_boundary(market)
    rows = targets.labels(moved.prices, moved.universe, moved.calendar, 3, MIN_TICKERS).frame
    groups = split.ticker_groups(sorted(moved.universe["ticker"].unique()), 5, 0)
    for cell in zero_run[3].cells[periods.FROM_BOUNDARY]:
        held = [t for t, g in groups.items() if g == cell.group]
        mine = rows.filter(pl.col("ticker").is_in(held) & pl.col("date").is_in(period_dates(moved, cell.fold, periods.FROM_BOUNDARY)))
        assert cell.accuracy == (mine.filter(pl.col("direction").is_not_null())["direction"] == 0).mean()


def test_the_score_frame_is_checked(market: synthetic.Market) -> None:
    good = zero.scores(market.universe)

    def refused(scores: pl.DataFrame) -> None:
        runner.scored_market(market.prices, market.universe, market.calendar, scores)

    with pytest.raises(ValueError, match="columns .*expected ticker, date, score, stamp"):
        refused(good.rename({"stamp": "when"}))
    with pytest.raises(ValueError, match="^the score frame has a null or NaN score: a cell without a score is left out of it$"):
        refused(good.with_columns(score=pl.when(pl.col("ticker") == "T001").then(None).otherwise(0.5)))
    with pytest.raises(ValueError, match="^the score frame has a null or NaN score: a cell without a score is left out of it$"):
        refused(good.with_columns(score=pl.when(pl.col("ticker") == "T001").then(float("nan")).otherwise(0.5)))
    with pytest.raises(StampRefused, match="stamp .* is after the cell's date"):
        refused(good.with_columns(stamp=pl.col("date") + pl.duration(days=1)))


def test_the_boundary_belongs_to_the_second_period() -> None:
    days = pl.DataFrame({"date": [periods.BOUNDARY - timedelta(days=1), periods.BOUNDARY]})
    assert days.filter(runner.in_period(periods.SURVIVOR_ONLY))["date"].to_list() == [date(2014, 3, 31)]
    assert days.filter(runner.in_period(periods.FROM_BOUNDARY))["date"].to_list() == [periods.BOUNDARY]


def test_the_config_hash_names_the_period_and_every_part_of_the_run() -> None:
    first, second = (record.config_hash(run_of(), p) for p in runner.PERIOD_NAMES)
    assert first != second
    split_config = {**GEOMETRY, "k": 5, "seed": 0, "period": periods.SURVIVOR_ONLY}
    assert first == trials.config_hash(
        feature_columns=[], target={"horizons": [3, 63], "min_tickers": 5}, split=split_config,
        cost={"levels_bps": [0.0, 10.0, 25.0], "default_bps": 10.0}, model_name="zero", hyperparameters={},
        data_manifest={"synthetic": "seed-3"})
    for change in ({"name": "momentum"}, {"feature_columns": ["a"]}, {"data_manifest": {"synthetic": "x"}},
                   {"group_seed": 1}, {"groups": 4}, {"min_tickers": 6}, {"horizons": (3,)},
                   {"geometry": {**GEOMETRY, "step": 41}}):
        assert record.config_hash(run_of(change), periods.SURVIVOR_ONLY) != first


def lines_of(path: Path) -> list[list[str]]:
    return [row.split("\t") for row in path.read_text().splitlines()[1:]]


def check_a_run_leaves_a_line_per_period_horizon_and_metric(zero_run: dict[int, runner.Horizon], tmp_path: Path) -> None:
    tmp_path.mkdir()
    path = tmp_path / "trials.tsv"
    written = record.record(path, DAY, run_of(), zero_run)
    names = ["accuracy", "balanced_accuracy", "IC", "Sharpe_0bps", "Sharpe_10bps", "Sharpe_25bps", "DSR"]
    assert [(w.period, w.horizon, w.metric) for w in written] == [
        (p, h, m) for p in runner.PERIOD_NAMES for h in HORIZONS for m in names]  # a horizon's DSR follows its others
    rows = lines_of(path)
    assert len(rows) == len(written) == 2 * 2 * 7
    assert [r[0] for r in rows[:14]] == [record.config_hash(run_of(), periods.SURVIVOR_ONLY)] * 14
    assert [r[0] for r in rows[14:]] == [record.config_hash(run_of(), periods.FROM_BOUNDARY)] * 14
    assert {r[1] for r in rows} == {"2026-10-27"} and all(r[5] for r in rows)
    assert [int(r[6]) for r in rows if r[3] == "accuracy"] == [0, 1, 2, 3]  # the two periods' two horizons, in order


def check_the_ic_of_a_constant_is_a_line_with_no_number_and_says_why(zero_run: dict[int, runner.Horizon],
                                                                    tmp_path: Path) -> None:
    tmp_path.mkdir()
    path = tmp_path / "trials.tsv"
    record.record(path, DAY, run_of(), zero_run)
    ic = next(r for r in lines_of(path) if r[3] == "IC" and r[2] == "3")
    assert ic[4] == "" and ic[5].startswith("folds: undefined; groups: undefined; undefined_cells=")
    assert ic[7].startswith("no number: no cell has this metric defined; period=survivor-only; cells=5; test_rows=1200; ")
    assert "IC dates=0; dropped_thin=0; dropped_flat=" in ic[7] and "dropped_flat=0" not in ic[7]
    assert "whole sample" in ic[7] and "dropped_missing=0; dropped_ties=" in ic[7]
    accuracy = next(r for r in lines_of(path) if r[3] == "accuracy" and r[2] == "3")
    assert accuracy[4] != "" and "IC dates" not in accuracy[7] and not accuracy[7].startswith("no number")
    assert accuracy[7].endswith("(whole sample)")


def test_a_period_with_no_test_date_is_a_line_that_says_so(market: synthetic.Market, tmp_path: Path) -> None:
    run = run_of({"horizons": (3,)})
    path = tmp_path / "trials.tsv"
    written = record.record(path, DAY, run, evaluated(market, zero.scores(market.universe), run))
    assert [w.mean is None for w in written if w.period == periods.FROM_BOUNDARY] == [True] * 7
    last = lines_of(path)[-1]
    assert last[4] == last[5] == "" and last[7].startswith("no test date in this period; period=from-2014-04-01; cells=0;")
    assert any(w.mean is not None for w in written if w.period == periods.SURVIVOR_ONLY)


def check_the_dsr_counts_every_dsr_line_before_it_and_takes_v_from_the_sharpes(zero_run: dict[int, runner.Horizon],
                                                                              tmp_path: Path) -> None:
    tmp_path.mkdir()
    path = tmp_path / "trials.tsv"
    record.record(path, DAY, run_of(), zero_run)
    rows = lines_of(path)
    dsr = [r for r in rows if r[3] == "DSR"]
    assert [int(r[6]) for r in dsr] == [0, 1, 2, 3]
    sharpes = [float(r[4]) / 252**0.5 for r in rows if r[3] == "Sharpe_10bps"]
    assert len(sharpes) == 4
    for count, line in enumerate(dsr, start=1):  # each DSR sees the Sharpes written before it, its own horizon's included
        shown = "none" if count == 1 else repr(statistics.variance(sharpes[:count]))
        assert line[7].endswith(f"N={count}; V={shown} (from the Sharpe_10bps lines)")
    order = [(r[3], r[2]) for r in rows[:14]]
    assert order.index(("DSR", "3")) == 6 and order.index(("Sharpe_10bps", "63")) == 11


def test_the_variance_of_the_sharpes_and_the_count_of_trials_come_from_the_file(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    for number, mean in enumerate((None, 2.52, -1.26, 0.0)):
        trials.append_trial(path, run=f"ab{number}", day=DAY, horizon=3, metric=record.SHARPE_FOR_DSR, mean=mean,
                            dispersion=None, note="n")
    trials.append_trial(path, run="ab", day=DAY, horizon=3, metric="Sharpe_0bps", mean=9.0, dispersion=None)
    assert record.sharpe_variance(path) == statistics.variance([2.52 / 252**0.5, -1.26 / 252**0.5, 0.0])
    assert record.trials_before(path, record.SHARPE_FOR_DSR) == 4 and record.trials_before(path, "DSR") == 0


def test_a_variance_of_one_sharpe_is_none(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    trials.append_trial(path, run="ab", day=DAY, horizon=3, metric=record.SHARPE_FOR_DSR, mean=1.0, dispersion=None)
    assert record.sharpe_variance(path) is None


def cell_with(nets: list[float]) -> runner.Cell:
    series = {bps: np.array(nets) for bps in runner.LEVELS}
    return runner.Cell(0, 1, 7, 0.5, 0.5, metrics.IC(None, None, None, 0, 0, 0), series)


def test_a_dsr_after_the_first_with_no_variance_is_undefined_and_says_why(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    trials.append_trial(path, run="ab", day=DAY, horizon=3, metric="DSR", mean=0.5, dispersion=None)
    where = record.Where(path, DAY, "ab", periods.SURVIVOR_ONLY)
    values, note = record.dsr_values(where, [cell_with([0.01, -0.02, 0.03])])
    assert values == {(0, 1): None}
    assert note == "N=2; V=none (from the Sharpe_10bps lines); fewer than two Sharpes to take a variance of"


def test_a_first_dsr_needs_no_variance_and_a_later_one_uses_it(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    series = [0.01, -0.02, 0.03, 0.0, 0.02]
    where = record.Where(path, DAY, "ab", periods.SURVIVOR_ONLY)
    trials.append_trial(path, run="ab", day=DAY, horizon=3, metric="Sharpe_10bps", mean=1.0, dispersion=None)
    values, note = record.dsr_values(where, [cell_with(series)])
    assert values == {(0, 1): metrics.deflated_sharpe(np.array(series), 1, None)} and note.startswith("N=1; V=none")
    trials.append_trial(path, run="cd", day=DAY, horizon=3, metric="Sharpe_10bps", mean=3.0, dispersion=None)
    trials.append_trial(path, run="ab", day=DAY, horizon=3, metric="DSR", mean=0.5, dispersion=None)
    values, note = record.dsr_values(where, [cell_with(series)])
    variance = ((1.0 - 3.0) ** 2 / 2) / 252
    assert values == {(0, 1): metrics.deflated_sharpe(np.array(series), 2, variance)}
    assert note == f"N=2; V={variance!r} (from the Sharpe_10bps lines)"


def check_a_repeat_of_a_run_conflicts_at_nothing(zero_run: dict[int, runner.Horizon], tmp_path: Path) -> None:
    tmp_path.mkdir()
    path = tmp_path / "trials.tsv"
    record.record(path, DAY, run_of(), zero_run)
    record.record(path, DAY, run_of(), zero_run)  # raises TrialConflict if any line conflicts
    rows = lines_of(path)
    first, again = rows[:28], rows[28:]
    assert len(again) == 28 and not any("CONFLICT" in r[7] for r in rows)
    assert [r[:6] for r in again if r[3] != "DSR"] == [r[:6] for r in first if r[3] != "DSR"]
    assert [int(r[6]) for r in again if r[3] == "DSR"] == [4, 5, 6, 7]  # N has grown: the DSR differs by design
    assert [re.search(r"N=\d+", r[7]).group() for r in again if r[3] == "DSR"] == ["N=5", "N=6", "N=7", "N=8"]  # type: ignore[union-attr]


def test_the_count_and_ic_notes_are_exact() -> None:
    class Found:
        frame = pl.DataFrame()
        dropped_missing, dropped_ties, dropped_thin_dates, delisting_ends = 1, 2, 3, 4

    cells = [cell_with([0.0]), cell_with([0.0])._replace(ic=metrics.IC(0.1, 0.1, 1.0, 5, 6, 7), test_rows=11)]
    part = runner.Horizon(3, Found(), {periods.SURVIVOR_ONLY: cells})  # type: ignore[arg-type]
    assert record.count_note(periods.SURVIVOR_ONLY, part, cells) == (
        "period=survivor-only; cells=2; test_rows=18; dropped_missing=1; dropped_ties=2; dropped_thin_dates=3; "
        "delisting_ends=4 (whole sample)")
    assert record.ic_note(cells) == "IC dates=5; dropped_thin=6; dropped_flat=7"


def test_append_writes_the_fold_axis_mean_and_both_dispersions(tmp_path: Path) -> None:
    class Found:
        frame = pl.DataFrame()
        dropped_missing = dropped_ties = dropped_thin_dates = delisting_ends = 0

    cells = [cell_with([0.0])]
    part = runner.Horizon(5, Found(), {periods.FROM_BOUNDARY: cells})  # type: ignore[arg-type]
    where = record.Where(tmp_path / "t.tsv", DAY, "ab12", periods.FROM_BOUNDARY)
    values = {(0, 0): 1.0, (0, 1): 3.0, (1, 0): 2.0, (1, 1): 4.0}
    line = record.append(where, part, "accuracy", values, "extra")
    assert line == record.Line(periods.FROM_BOUNDARY, 5, "accuracy", 2.5, 0)
    row = lines_of(tmp_path / "t.tsv")[0]
    assert row[:5] == ["ab12", "2026-10-27", "5", "accuracy", "2.5"]
    assert row[5] == trials.dispersion_text(Dispersion(Axis(2.5, 0.7071067811865476, 2.0, 3.0, 2),
                                                       Axis(2.5, 1.4142135623730951, 1.5, 3.5, 2), 0, False))
    assert row[7].endswith("(whole sample); extra") and row[7].startswith("period=from-2014-04-01; cells=1;")


@pytest.fixture(scope="module")
def zero_across(market: synthetic.Market) -> dict[int, runner.Horizon]:
    """The zero baseline on the market moved across the boundary: one run, read by the two tests below."""
    moved = across_boundary(market)
    return evaluated(moved, zero.scores(moved.universe), run_of())


def test_a_zero_run_across_the_boundary_splits_by_period_and_has_a_constants_shape(
        market: synthetic.Market, zero_across: dict[int, runner.Horizon]) -> None:
    got = zero_across
    assert list(got) == list(HORIZONS) and [part.horizon for part in got.values()] == list(HORIZONS)
    check_each_period_has_the_test_rows_on_its_side_of_the_boundary(market, got)
    check_a_period_cell_is_the_metric_of_that_periods_rows_only(market, got)
    check_the_zero_baseline_has_the_shape_the_harness_gives_a_constant(got)
    check_zero_accuracy_is_the_share_of_down_labels(market, got)


def test_a_zero_run_leaves_its_lines(zero_across: dict[int, runner.Horizon], tmp_path: Path) -> None:
    got = zero_across
    check_a_run_leaves_a_line_per_period_horizon_and_metric(got, tmp_path / "a")
    check_the_ic_of_a_constant_is_a_line_with_no_number_and_says_why(got, tmp_path / "b")
    check_the_dsr_counts_every_dsr_line_before_it_and_takes_v_from_the_sharpes(got, tmp_path / "c")
    check_a_repeat_of_a_run_conflicts_at_nothing(got, tmp_path / "d")


def test_a_line_without_an_extra_note_ends_at_the_counts(tmp_path: Path) -> None:
    class Found:
        frame = pl.DataFrame()
        dropped_missing = dropped_ties = dropped_thin_dates = delisting_ends = 0

    part = runner.Horizon(5, Found(), {periods.FROM_BOUNDARY: [cell_with([0.0])]})  # type: ignore[arg-type]
    where = record.Where(tmp_path / "t.tsv", DAY, "ab12", periods.FROM_BOUNDARY)
    record.append(where, part, "accuracy", {(0, 0): 1.0})
    assert lines_of(tmp_path / "t.tsv")[0][7].endswith("delisting_ends=0 (whole sample)")


def test_the_scalar_metrics_read_a_cell() -> None:
    series = np.array([0.01, -0.02, 0.03, 0.0, 0.02])
    cell = runner.Cell(0, 1, 7, 0.3, 0.7, metrics.IC(0.1, 0.2, 0.5, 4, 0, 0), {0.0: series, 10.0: series * 2, 25.0: -series})
    got = {name: read(cell) for name, read in runner.scalar_metrics().items()}
    assert list(got) == ["accuracy", "balanced_accuracy", "IC", "Sharpe_0bps", "Sharpe_10bps", "Sharpe_25bps"]
    assert got == {"accuracy": 0.3, "balanced_accuracy": 0.7, "IC": 0.1, "Sharpe_0bps": metrics.sharpe(series),
                   "Sharpe_10bps": metrics.sharpe(series * 2), "Sharpe_25bps": metrics.sharpe(-series)}


def test_the_prices_a_fold_reads_end_with_the_last_sleeve_or_the_calendar() -> None:
    days = [date(2000, 1, 3) + timedelta(days=n) for n in range(100)]
    frame = pl.DataFrame({"ticker": "A", "date": days, "close": 1.0})
    middle = runner.window_prices(frame, days, split.Fold(0, 0, 40, 60, 70), 5)
    assert (middle["date"].min(), middle["date"].max()) == (days[60], days[75])
    late = runner.window_prices(frame, days, split.Fold(0, 0, 40, 80, 90), 63)
    assert (late["date"].min(), late["date"].max()) == (days[80], days[99])
