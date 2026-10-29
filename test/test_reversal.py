"""The 1-month reversal baseline (TODO 3.1 c): its window counted by hand on a small frame, its sign, its nulls, its
stamp, that the runner takes it and that a run writes its lines. Synthetic data only; trials go to temporary files."""
from datetime import date, timedelta
from functools import partial
from pathlib import Path

import polars as pl
import pytest

from neonrain import targets
from neonrain.baselines import momentum, record, reversal, runner
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


def test_the_value_is_the_negated_return_over_the_21_sessions_ending_at_the_cell() -> None:
    """Position 100: close(100) / close(79) - 1 = 200 / 179 - 1, by hand; the window is sessions 79 to 100."""
    raw = momentum.window_returns(frame({"A": line(1.0)}), CALENDAR, reversal.SPAN).filter(pl.col("pos") == 100)
    assert raw["value"].to_list() == [pytest.approx(200.0 / 179.0 - 1.0)] and raw["date"].to_list() == [CALENDAR[100]]
    assert reversal.SPAN == 21


def test_a_falling_ticker_scores_higher_than_a_rising_one() -> None:
    """Sign: the loser is predicted to rise, so it scores 1 and the winner 0; a flat one is between at 0.5."""
    rows = frame({"A": line(1.0), "B": line(-0.5), "C": line(0.0)})
    got = reversal.scores(rows, everyone(["A", "B", "C"], [100]), CALENDAR)
    assert dict(zip(got["ticker"], got["score"])) == {"A": 0.0, "B": 1.0, "C": 0.5}


def test_the_window_starts_at_the_session_21_back_and_not_before() -> None:
    """At 20 there is no close 21 back; at 21 the window opens, on the first session."""
    got = reversal.scores(frame({"A": line(1.0)}), everyone(["A"], [20, 21, 22]), CALENDAR)
    assert got["date"].to_list() == [CALENDAR[21], CALENDAR[22]]


def test_the_day_itself_is_in_the_window_and_nothing_is_skipped() -> None:
    """A gap at the day itself, or at the session 21 back, takes the value away; one at 22 back or after does not."""
    rows = frame({"A": line(1.0, skip={100}), "B": line(1.0, skip={79}), "C": line(1.0, skip={78}), "D": line(1.0, skip={101}),
                  "E": line(1.0, skip={90})})
    got = reversal.scores(rows, everyone(list("ABCDE"), [100]), CALENDAR)
    assert got["ticker"].to_list() == ["C", "D"]


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), 0.0, -1.0])
def test_a_window_with_an_unusable_close_in_it_has_no_value(bad: float | None) -> None:
    """The close 21 back, one inside the window, and the day's own close, each in turn; the neighbour keeps its value."""
    for where in (79, 90, 100):
        rows = frame({"A": {**line(1.0), where: bad}, "B": line(2.0)})
        got = reversal.scores(rows, everyone(["A", "B"], [100]), CALENDAR)
        assert got["ticker"].to_list() == ["B"], where


def test_a_close_below_one_is_usable() -> None:
    """Usable is above zero, not above one: a close of 0.5 inside the window keeps the value."""
    rows = frame({"A": {**line(1.0), 90: 0.5}, "B": line(2.0)})
    assert reversal.scores(rows, everyone(["A", "B"], [100]), CALENDAR)["ticker"].to_list() == ["A", "B"]


def test_a_cell_off_the_universe_is_not_scored_and_a_universe_cell_without_a_price_row_is_not_either() -> None:
    rows = frame({"A": line(1.0), "X": line(5.0)})
    got = reversal.scores(rows, everyone(["A", "Z"], [100]), CALENDAR)
    assert got["ticker"].to_list() == ["A"]  # X is no member, Z has no prices


def test_the_score_is_the_rank_fraction_of_the_negation_with_ties_at_their_average_and_one_cell_scores_half() -> None:
    rows = frame({"A": line(1.0), "B": line(2.0), "C": line(2.0), "D": line(3.0), "E": line(0.0)})
    got = reversal.scores(rows, everyone(list("ABCDE"), [100]), CALENDAR)
    assert dict(zip(got["ticker"], got["score"])) == {"D": 0.0, "B": 0.375, "C": 0.375, "A": 0.75, "E": 1.0}
    one = reversal.scores(rows, everyone(["D"], [100]), CALENDAR)
    assert one["score"].to_list() == [0.5]


def test_two_returns_of_exactly_zero_tie() -> None:
    """Flat tickers (a return of 0) rank together at their average, below the riser and above no one."""
    rows = frame({"A": line(0.0), "B": {p: 50.0 for p in range(300)}, "C": line(1.0)})
    got = reversal.scores(rows, everyone(["A", "B", "C"], [100]), CALENDAR)
    assert dict(zip(got["ticker"], got["score"])) == {"A": 0.75, "B": 0.75, "C": 0.0}


def test_the_rank_is_within_the_day_and_among_cells_with_a_value() -> None:
    """N's gap at 95 is in the window of day 100 and out of day 120's: it is unranked on the first and ranks on the
    second, where its steep rise scores it 0; each day ranks its own cells."""
    rows = frame({"A": line(1.0), "B": line(2.0), "C": line(3.0), "N": line(9.0, skip={95})})
    got = reversal.scores(rows, everyone(["A", "B", "C", "N"], [100, 120]), CALENDAR)
    assert got.filter(pl.col("date") == CALENDAR[100]).sort("ticker")["score"].to_list() == [1.0, 0.5, 0.0]
    assert got.filter(pl.col("date") == CALENDAR[120]).sort("ticker")["score"].to_list() == [1.0, pytest.approx(2 / 3), pytest.approx(1 / 3), 0.0]
    assert got.filter(pl.col("date") == CALENDAR[120])["ticker"].to_list() == ["A", "B", "C", "N"]


def test_the_frame_has_the_layout_the_runner_takes_and_every_stamp_is_the_cells_own_date() -> None:
    got = reversal.scores(frame({"A": line(1.0), "B": line(2.0)}), everyone(["A", "B"], [30, 100, 299]), CALENDAR)
    assert got.columns == ["ticker", "date", "score", "stamp"]
    assert got.schema == {"ticker": pl.String, "date": pl.Date, "score": pl.Float64, "stamp": pl.Date}
    assert got["stamp"].to_list() == got["date"].to_list() and got.height == 6
    assert got["score"].null_count() == 0 and got["score"].min() >= 0 and got["score"].max() <= 1


def test_the_order_of_the_price_rows_changes_nothing_and_the_output_keeps_the_universes_order() -> None:
    """Shuffled price rows give the same scores; the rows come out in the universe's own order, not sorted."""
    rows = frame({"B": line(2.0), "A": line(1.0), "C": line(3.0, skip={95})})
    cells = everyone(["B", "A", "C"], [120, 100]).sort("date", descending=True)
    want = reversal.scores(rows.sort("ticker", "date"), cells, CALENDAR)
    got = reversal.scores(rows.sort("date", descending=True), cells, CALENDAR)
    assert got.equals(want) and got.height == 5
    assert got.select("ticker", "date").equals(cells.filter(~((pl.col("ticker") == "C") & (pl.col("date") == CALENDAR[100]))))


def test_a_price_off_the_calendar_is_refused() -> None:
    rows = frame({"A": line(1.0)}).vstack(pl.DataFrame([("A", date(2000, 1, 1), 100.0)], schema=SCHEMA, orient="row"))
    with pytest.raises(ValueError, match=r"^price row \(A, 2000-01-01\) is off the calendar$"):
        reversal.scores(rows, everyone(["A"], [100]), CALENDAR)


GEOMETRY = {"embargo": 63, "step": 40, "min_train": 100, "window": None}
RUN = runner.Run("reversal", [], {"synthetic": "seed-3"}, GEOMETRY, min_tickers=5, horizons=(3,))  # type: ignore[arg-type]


@pytest.fixture(scope="module")
def market() -> synthetic.Market:
    """Built in a fixture, not at import: mutmut times tests, not imports (J-074)."""
    return synthetic.generate(synthetic.MarketConfig(tickers=60, days=330, rho=0.1, delist_below=0.5, seed=3))


@pytest.fixture(scope="module")
def market_scores(market: synthetic.Market) -> pl.DataFrame:
    return reversal.scores(market.prices, market.universe, market.calendar)


def test_the_synthetic_market_gets_a_stamped_score_from_the_session_21_on(market: synthetic.Market,
                                                                         market_scores: pl.DataFrame) -> None:
    assert market_scores.height > 0 and market_scores["date"].min() >= market.calendar[21]
    scored = runner.scored_market(market.prices, market.universe, market.calendar, market_scores)
    check_market(scored)
    later = market_scores.with_columns(stamp=pl.col("date") + pl.duration(days=1))
    with pytest.raises(StampRefused):
        runner.scored_market(market.prices, market.universe, market.calendar, later)


def test_a_run_of_reversal_leaves_its_lines(market: synthetic.Market, market_scores: pl.DataFrame, tmp_path: Path) -> None:
    scored = runner.scored_market(market.prices, market.universe, market.calendar, market_scores)
    parts = runner.evaluate(scored, partial(targets.labels, market.prices, market.universe, market.calendar,
                                            min_tickers=RUN.min_tickers), RUN)
    cells = [c for cs in parts[3].cells.values() for c in cs]
    assert cells and all(c.ic.dates > 0 for c in cells)  # a ranked score has an IC, unlike zero's constant
    path = tmp_path / "trials.tsv"
    written = record.record(path, date(2026, 10, 29), RUN, parts)
    assert len(written) == 2 * 1 * 7 and {w.metric for w in written} >= {"IC", "DSR", "Sharpe_10bps"}
    rows = [r.split("\t") for r in path.read_text().splitlines()[1:]]
    assert len(rows) == 14 and "CONFLICT" not in path.read_text()
    assert {r[0] for r in rows} == {record.config_hash(RUN, p) for p in runner.PERIOD_NAMES}
