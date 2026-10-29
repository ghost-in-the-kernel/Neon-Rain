"""The 12-1 momentum baseline (TODO 3.1 b): its window counted by hand on a small frame, its nulls, its stamp, that the
runner takes it and that a run writes its lines. Synthetic data only; trials go to temporary files."""
from datetime import date, timedelta
from functools import partial
from pathlib import Path

import polars as pl
import pytest

from neonrain import targets
from neonrain.baselines import momentum, record, runner
from neonrain.harness import synthetic
from neonrain.harness.market import StampRefused, check_market

CALENDAR = [date(2000, 1, 3) + timedelta(days=d) for d in range(0, 600) if (date(2000, 1, 3) + timedelta(days=d)).weekday() < 5][:300]
SCHEMA = {"ticker": pl.String, "date": pl.Date, "close": pl.Float64}


def frame(closes: dict[str, dict[int, float | None]]) -> pl.DataFrame:
    """Price rows from {ticker: {position on CALENDAR: close}}; a position not given is a session with no row."""
    rows = [(t, CALENDAR[p], c) for t, by in closes.items() for p, c in by.items()]
    return pl.DataFrame(rows, schema=SCHEMA, orient="row")


def everyone(tickers: list[str], positions: list[int]) -> pl.DataFrame:
    return pl.DataFrame([(t, CALENDAR[p]) for t in tickers for p in positions],
                        schema={"ticker": pl.String, "date": pl.Date}, orient="row")


def line(slope: float, skip: set[int] = frozenset()) -> dict[int, float | None]:  # type: ignore[assignment]
    """close = 100 + slope * position, for every session but those in `skip`."""
    return {p: 100.0 + slope * p for p in range(300) if p not in skip}


def test_the_window_is_the_close_21_back_over_the_close_252_back() -> None:
    """Position 260: close(239) / close(8) - 1 = (100 + 239) / (100 + 8) - 1, by hand."""
    got = momentum.scores(frame({"A": line(1.0), "B": line(0.0)}), everyone(["A", "B"], [260]), CALENDAR)
    want = 339.0 / 108.0 - 1.0
    raw = momentum.window_returns(frame({"A": line(1.0)}), CALENDAR).filter(pl.col("pos") == 239)
    assert raw["value"].to_list() == [pytest.approx(want)] and raw["date"].to_list() == [CALENDAR[239]]
    assert got["ticker"].to_list() == ["A", "B"] and got["score"].to_list() == [1.0, 0.0]  # B's return is 0


def test_the_window_starts_at_the_session_252_back_and_not_before() -> None:
    """At 251 there is no close 252 back; at 252 the window opens, on the first session."""
    got = momentum.scores(frame({"A": line(1.0)}), everyone(["A"], [251, 252, 253]), CALENDAR)
    assert got["date"].to_list() == [CALENDAR[252], CALENDAR[253]]
    assert momentum.SPAN == 231 and momentum.LOOKBACK - momentum.SKIP == 231


def test_the_skipped_month_is_not_read() -> None:
    """A missing or nonpositive close among the latest 20 sessions (and the day itself) takes nothing away."""
    rows = frame({"A": {**line(1.0, skip={250, 255, 260}), 258: -5.0}, "B": line(2.0)})
    got = momentum.scores(rows, everyone(["A", "B"], [260]), CALENDAR)
    assert got["ticker"].to_list() == ["A", "B"] and got["stamp"].to_list() == [CALENDAR[239]] * 2


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), 0.0, -1.0])
def test_a_window_with_an_unusable_close_in_it_has_no_value(bad: float | None) -> None:
    """The close 252 back, one inside the window, and the close 21 back, each in turn; the neighbour keeps its value."""
    for where in (8, 100, 239):
        rows = frame({"A": {**line(1.0), where: bad}, "B": line(2.0)})
        got = momentum.scores(rows, everyone(["A", "B"], [260]), CALENDAR)
        assert got["ticker"].to_list() == ["B"], where


def test_a_close_below_one_is_usable() -> None:
    """Usable is above zero, not above one: a close of 0.5 inside the window keeps the value."""
    rows = frame({"A": {**line(1.0), 100: 0.5}, "B": line(2.0)})
    assert momentum.scores(rows, everyone(["A", "B"], [260]), CALENDAR)["ticker"].to_list() == ["A", "B"]


def test_a_session_with_no_row_in_the_window_has_no_value_and_a_gap_outside_it_has() -> None:
    """At 260 the window is sessions 8 to 239: A's gap at 120 is inside it; B's at 7 (before) and 240 (skipped) are not."""
    rows = frame({"A": line(1.0, skip={120}), "B": line(1.0, skip={7, 240}), "C": line(1.0, skip={8})})
    got = momentum.scores(rows, everyone(["A", "B", "C"], [260]), CALENDAR)
    assert got["ticker"].to_list() == ["B"]  # C's gap at 8, the window's first session, is inside it
    assert momentum.scores(rows, everyone(["B"], [259]), CALENDAR).height == 0  # at 259 the window is 7 to 238


def test_a_cell_off_the_universe_is_not_scored_and_a_universe_cell_without_a_price_row_is_not_either() -> None:
    rows = frame({"A": line(1.0), "X": line(5.0)})
    got = momentum.scores(rows, everyone(["A", "Z"], [260]), CALENDAR)
    assert got["ticker"].to_list() == ["A"]  # X is no member, Z has no prices


def test_the_score_is_the_rank_fraction_with_ties_at_their_average_and_one_cell_scores_half() -> None:
    rows = frame({"A": line(1.0), "B": line(2.0), "C": line(2.0), "D": line(3.0), "E": line(0.0)})
    got = momentum.scores(rows, everyone(list("ABCDE"), [260]), CALENDAR)
    assert dict(zip(got["ticker"], got["score"])) == {"E": 0.0, "A": 0.25, "B": 0.625, "C": 0.625, "D": 1.0}
    one = momentum.scores(rows, everyone(["D"], [260]), CALENDAR)
    assert one["score"].to_list() == [0.5]


def test_the_rank_is_within_the_day_and_among_cells_with_a_value() -> None:
    """Each day ranks its own cells: the same three tickers rank alike on two days; a cell with no value is not ranked."""
    rows = frame({"A": line(1.0), "B": line(2.0), "C": line(3.0), "N": line(9.0, skip={50})})
    got = momentum.scores(rows, everyone(["A", "B", "C", "N"], [260, 270]), CALENDAR)
    assert got.height == 6 and set(got["score"].to_list()) == {0.0, 0.5, 1.0}
    assert got.filter(pl.col("date") == CALENDAR[270]).sort("ticker")["score"].to_list() == [0.0, 0.5, 1.0]


def test_the_frame_has_the_layout_the_runner_takes_and_every_stamp_is_the_session_21_back() -> None:
    got = momentum.scores(frame({"A": line(1.0), "B": line(2.0)}), everyone(["A", "B"], [255, 260, 299]), CALENDAR)
    assert got.columns == ["ticker", "date", "score", "stamp"]
    assert got.schema == {"ticker": pl.String, "date": pl.Date, "score": pl.Float64, "stamp": pl.Date}
    where = {d: i for i, d in enumerate(CALENDAR)}
    assert [where[d] - where[s] for d, s in zip(got["date"], got["stamp"])] == [21] * 6
    assert got["score"].null_count() == 0 and got["score"].min() >= 0 and got["score"].max() <= 1


def test_the_order_of_the_price_rows_changes_nothing_and_the_output_keeps_the_universes_order() -> None:
    """Shuffled price rows give the same scores; the rows come out in the universe's own order, not sorted."""
    rows = frame({"B": line(2.0), "A": line(1.0), "C": line(3.0, skip={50})})
    cells = everyone(["B", "A", "C"], [270, 260]).sort("date", descending=True)
    want = momentum.scores(rows.sort("ticker", "date"), cells, CALENDAR)
    got = momentum.scores(rows.sort("date", descending=True), cells, CALENDAR)
    assert got.equals(want) and got.height == 4
    assert got.select("ticker", "date").equals(cells.filter(pl.col("ticker") != "C"))


def test_a_price_off_the_calendar_is_refused() -> None:
    rows = frame({"A": line(1.0)}).vstack(pl.DataFrame([("A", date(2000, 1, 1), 100.0)], schema=SCHEMA, orient="row"))
    with pytest.raises(ValueError, match=r"^price row \(A, 2000-01-01\) is off the calendar$"):
        momentum.scores(rows, everyone(["A"], [260]), CALENDAR)


GEOMETRY = {"embargo": 63, "step": 40, "min_train": 100, "window": None}
RUN = runner.Run("momentum", [], {"synthetic": "seed-3"}, GEOMETRY, min_tickers=5, horizons=(3,))  # type: ignore[arg-type]


@pytest.fixture(scope="module")
def market() -> synthetic.Market:
    """Built in a fixture, not at import: mutmut times tests, not imports, so a market built at import made every
    mutant these tests cover overrun its CPU limit (J-074)."""
    return synthetic.generate(synthetic.MarketConfig(tickers=60, days=330, rho=0.1, delist_below=0.5, seed=3))


@pytest.fixture(scope="module")
def market_scores(market: synthetic.Market) -> pl.DataFrame:
    return momentum.scores(market.prices, market.universe, market.calendar)


def test_the_synthetic_market_gets_a_stamped_score_from_the_session_252_on(market: synthetic.Market,
                                                                          market_scores: pl.DataFrame) -> None:
    assert market_scores.height > 0 and market_scores["date"].min() >= market.calendar[252]
    scored = runner.scored_market(market.prices, market.universe, market.calendar, market_scores)
    check_market(scored)
    later = market_scores.with_columns(stamp=pl.col("date") + pl.duration(days=1))
    with pytest.raises(StampRefused):
        runner.scored_market(market.prices, market.universe, market.calendar, later)


def test_a_run_of_momentum_leaves_its_lines(market: synthetic.Market, market_scores: pl.DataFrame, tmp_path: Path) -> None:
    scored = runner.scored_market(market.prices, market.universe, market.calendar, market_scores)
    parts = runner.evaluate(scored, partial(targets.labels, market.prices, market.universe, market.calendar,
                                            min_tickers=RUN.min_tickers), RUN)
    cells = [c for cs in parts[3].cells.values() for c in cs]
    assert cells and all(c.ic.dates > 0 for c in cells)  # a ranked score has an IC, unlike zero's constant
    path = tmp_path / "trials.tsv"
    written = record.record(path, date(2026, 10, 28), RUN, parts)
    assert len(written) == 2 * 1 * 7 and {w.metric for w in written} >= {"IC", "DSR", "Sharpe_10bps"}
    rows = [r.split("\t") for r in path.read_text().splitlines()[1:]]
    assert len(rows) == 14 and "CONFLICT" not in path.read_text()
    assert {r[0] for r in rows} == {record.config_hash(RUN, p) for p in runner.PERIOD_NAMES}
