"""The returns family (TODO 2.3) on invented frames: tickers A and B, closes that make every window a sum done by hand.

No real price is in this file (R-006). Sessions are consecutive integers added to 2001-01-01 unless a test says
otherwise; the real calendar skips weekends, which the one test of `calendar.sessions` below uses.
"""
import math
from datetime import date, timedelta

import polars as pl
import pytest

from neonrain import targets
from neonrain.features import returns
from neonrain.harness import market
from neonrain.universe import calendar as sessions_of

FIRST = date(2001, 1, 1)
CALENDAR = [FIRST + timedelta(days=i) for i in range(300)]


def frame(rows: list[tuple[str, int, float | None]]) -> pl.DataFrame:
    """A price frame from (ticker, session index, close)."""
    return pl.DataFrame(
        {"ticker": [r[0] for r in rows], "date": [CALENDAR[r[1]] for r in rows], "close": [r[2] for r in rows]},
        schema=market.PRICE_COLUMNS,
    )


def line(ticker: str, sessions: range) -> list[tuple[str, int, float | None]]:
    """The closes i + 1 for session i: the k-return at i is (i + 1) / (i + 1 - k) - 1."""
    return [(ticker, i, float(i + 1)) for i in sessions]


def value(out: pl.DataFrame, ticker: str, i: int, column: str) -> float | date | None:
    """One cell of the output, by ticker and session index."""
    return out.filter((pl.col("ticker") == ticker) & (pl.col("date") == CALENDAR[i]))[column].item()


def test_the_lookbacks_are_the_four_horizons() -> None:
    assert returns.LOOKBACKS == targets.HORIZONS == (3, 5, 21, 63)


def test_the_stamp_suffix_is_the_harnesss() -> None:
    assert returns.STAMP_SUFFIX == market.STAMP_SUFFIX


def test_the_columns_are_each_feature_then_its_stamp() -> None:
    out = returns.returns(frame(line("A", range(70))), CALENDAR)
    assert out.columns == ["ticker", "date", *returns.feature_columns()]
    assert returns.feature_columns() == [
        "ret_3", "ret_3_stamp", "ret_5", "ret_5_stamp", "ret_21", "ret_21_stamp", "ret_63", "ret_63_stamp"]
    assert out.schema["ret_21"] == pl.Float64 and out.schema["ret_21_stamp"] == pl.Date
    assert market.stamp_columns(out) == {f"ret_{k}": f"ret_{k}_stamp" for k in (21, 3, 5, 63)}


@pytest.mark.parametrize(("column", "i", "expected"), [
    ("ret_3", 3, 3.0), ("ret_3", 4, 5 / 2 - 1), ("ret_3", 69, 70 / 67 - 1),
    ("ret_5", 5, 5.0), ("ret_5", 6, 7 / 2 - 1), ("ret_5", 69, 70 / 65 - 1),
    ("ret_21", 21, 21.0), ("ret_21", 22, 23 / 2 - 1), ("ret_21", 69, 70 / 49 - 1),
    ("ret_63", 63, 63.0), ("ret_63", 64, 65 / 2 - 1), ("ret_63", 69, 9.0),
])
def test_each_return_is_the_close_over_the_close_k_sessions_earlier_minus_one(column: str, i: int, expected: float) -> None:
    out = returns.returns(frame(line("A", range(70))), CALENDAR)
    assert value(out, "A", i, column) == pytest.approx(expected)


def test_the_first_k_sessions_have_no_value_and_no_stamp() -> None:
    out = returns.returns(frame(line("A", range(70))), CALENDAR)
    for k in returns.LOOKBACKS:
        for i in range(k):
            assert value(out, "A", i, returns.name(k)) is None
            assert value(out, "A", i, returns.name(k) + "_stamp") is None
        assert value(out, "A", k, returns.name(k)) is not None


def test_the_stamp_is_the_cells_own_date_and_the_frame_passes_the_harnesss_check() -> None:
    out = returns.returns(frame(line("A", range(70)) + line("B", range(10, 80))), CALENDAR)
    market.check_stamps(out)
    assert value(out, "A", 40, "ret_21_stamp") == CALENDAR[40]
    assert value(out, "B", 79, "ret_63_stamp") == CALENDAR[79]


def test_changing_every_price_after_t_leaves_the_feature_at_t_unmoved() -> None:
    rows = [(t, i, 10.0 + (i * 7) % 13) for t in ("A", "B") for i in range(80)]
    cut = 70
    changed = [(t, i, c * 3 + 5 if i > cut else c) for t, i, c in rows]
    before = returns.returns(frame(rows), CALENDAR)
    after = returns.returns(frame(changed), CALENDAR)
    upto = pl.col("date") <= CALENDAR[cut]
    assert before.filter(upto).equals(after.filter(upto))
    assert not before.filter(~upto).equals(after.filter(~upto))


def test_a_value_reads_only_the_two_ends_of_its_window_and_the_presence_of_the_rest() -> None:
    rows = [("A", i, 10.0 + (i * 7) % 13) for i in range(30)]
    moved = [(t, i, 99.0 if i in (6, 7) else c) for t, i, c in rows]
    first = returns.returns(frame(rows), CALENDAR)
    second = returns.returns(frame(moved), CALENDAR)
    assert value(first, "A", 21, "ret_21") == value(second, "A", 21, "ret_21")
    assert value(first, "A", 13, "ret_5") == value(second, "A", 13, "ret_5")
    assert value(first, "A", 8, "ret_3") == value(second, "A", 8, "ret_3")
    assert value(first, "A", 9, "ret_3") != value(second, "A", 9, "ret_3")


def test_a_missing_session_nulls_every_window_that_crosses_it_and_no_other() -> None:
    rows = [r for r in line("A", range(40)) if r[1] != 10]
    out = returns.returns(frame(rows), CALENDAR)
    for i in (11, 12, 13):
        assert value(out, "A", i, "ret_3") is None
    assert value(out, "A", 14, "ret_3") == pytest.approx(15 / 12 - 1)
    assert value(out, "A", 9, "ret_3") == pytest.approx(10 / 7 - 1)
    for i in range(11, 16):
        assert value(out, "A", i, "ret_5") is None
    assert value(out, "A", 16, "ret_5") == pytest.approx(17 / 12 - 1)
    assert value(out, "A", 31, "ret_21") is None
    assert value(out, "A", 32, "ret_21") == pytest.approx(33 / 12 - 1)
    assert value(out, "A", 32, "ret_21_stamp") == CALENDAR[32]
    assert value(out, "A", 25, "ret_21") is None


def test_a_gap_of_a_reused_ticker_keeps_it_whole_and_gives_no_value_across_it() -> None:
    rows = line("A", range(10)) + [("A", i, float(i)) for i in range(200, 230)]
    out = returns.returns(frame(rows), CALENDAR)
    assert out.height == 40
    assert value(out, "A", 9, "ret_3") == pytest.approx(10 / 7 - 1)
    for i in (200, 201, 202, 203, 204, 205):
        assert value(out, "A", i, "ret_5") is None or i > 204
    assert value(out, "A", 205, "ret_5") == pytest.approx(205 / 200 - 1)
    assert all(value(out, "A", i, "ret_63") is None for i in range(200, 230))


@pytest.mark.parametrize("bad", [None, 0.0, -2.0, math.nan, math.inf])
def test_an_unusable_close_keeps_its_cell_with_no_value_and_breaks_each_window_through_it(bad: float | None) -> None:
    rows = [(t, i, bad if (t, i) == ("A", 10) else float(i + 1)) for t in ("A", "B") for i in range(20)]
    out = returns.returns(frame(rows), CALENDAR)
    assert out.height == 40
    assert value(out, "A", 10, "ret_3") is None and value(out, "A", 10, "ret_3_stamp") is None
    for i in (11, 12, 13):
        assert value(out, "A", i, "ret_3") is None
    assert value(out, "A", 14, "ret_3") == pytest.approx(15 / 12 - 1)
    assert value(out, "A", 9, "ret_3") == pytest.approx(10 / 7 - 1)
    assert value(out, "B", 12, "ret_3") == pytest.approx(13 / 10 - 1)


def test_tickers_do_not_borrow_from_each_other_and_the_input_order_does_not_matter() -> None:
    a, b = line("A", range(10)), [("B", i, 100.0 * (i + 1)) for i in range(5, 15)]
    out = returns.returns(frame(b[::-1] + a[::-1]), CALENDAR)
    assert out["ticker"].to_list() == ["A"] * 10 + ["B"] * 10
    assert out["date"].to_list()[:10] == CALENDAR[:10]
    assert value(out, "B", 8, "ret_3") == pytest.approx(900 / 600 - 1)
    assert value(out, "B", 7, "ret_3") is None
    assert out.equals(returns.returns(frame(a + b), CALENDAR))


def test_a_lookback_counts_sessions_of_the_calendar_not_calendar_days() -> None:
    days = sessions_of.sessions(2001, 2001)
    assert days[:6] == [date(2001, 1, d) for d in (2, 3, 4, 5, 8, 9)]  # the weekend is no session
    prices = pl.DataFrame({"ticker": ["A"] * 6, "date": days[:6], "close": [1.0, 2.0, 4.0, 8.0, 16.0, 32.0]},
                          schema=market.PRICE_COLUMNS)
    on_monday = returns.returns(prices, days).filter(pl.col("date") == date(2001, 1, 8))
    assert on_monday["ret_3"].item() == pytest.approx(16.0 / 2.0 - 1)  # three sessions back is Wednesday the 3rd
    assert on_monday["ret_3_stamp"].item() == date(2001, 1, 8)


def test_a_price_off_the_calendar_is_refused_naming_it() -> None:
    prices = frame(line("A", range(5)))
    with pytest.raises(returns.OffCalendar, match=r"\(A, 2001-01-04\) is off the calendar"):
        returns.returns(prices, [d for d in CALENDAR if d != CALENDAR[3]])


def test_no_prices_give_the_empty_frame_with_the_columns() -> None:
    out = returns.returns(frame([]), CALENDAR)
    assert out.height == 0 and out.columns == ["ticker", "date", *returns.feature_columns()]


def test_the_whole_market_check_accepts_the_frame() -> None:
    prices = frame(line("A", range(70)) + line("B", range(70)))
    universe = prices.select("ticker", "date")
    out = returns.returns(prices, CALENDAR)
    market.check_market(market.Market(prices, universe, out, CALENDAR))


def test_the_first_price_off_the_calendar_by_ticker_then_date_is_the_one_named() -> None:
    descending = [("A", i, 1.0) for i in range(60, 3, -1)]  # sorting by ticker alone would not put 4 first
    prices = frame([("B", 3, 1.0), *descending, ("A", 0, 1.0)])
    with pytest.raises(returns.OffCalendar, match=r"\(A, 2001-01-05\) is off"):
        returns.returns(prices, [CALENDAR[0], CALENDAR[1], CALENDAR[2]])


def test_the_rows_come_out_sorted_by_ticker_then_date_with_the_tickers_interleaved_in_the_input() -> None:
    rows = [(t, i, float(i + 1)) for i in (4, 1, 3, 0, 2) for t in ("B", "A", "C")]
    out = returns.returns(frame(rows), CALENDAR)
    assert out.select("ticker", "date").rows() == [(t, CALENDAR[i]) for t in ("A", "B", "C") for i in range(5)]
    assert value(out, "C", 4, "ret_3") == pytest.approx(5 / 2 - 1)


def test_no_prices_on_an_empty_calendar_still_give_the_empty_frame() -> None:
    assert returns.returns(frame([]), []).height == 0
