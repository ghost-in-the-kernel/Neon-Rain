"""The volatility family (TODO 2.3) on invented frames: tickers A and B, closes that make every window a sum done by hand.

No real price is in this file (R-006). Sessions are consecutive integers added to 2001-01-01 unless a test says
otherwise. The main series has the log close alternating 0, 1, 0, 1, ...: its daily log returns are +1 at odd
sessions and -1 at even ones, so the sample standard deviation of n returns with sum m is sqrt((n - m*m/n) / (n - 1)).
"""
import math
from datetime import date, timedelta

import polars as pl
import pytest

from neonrain import targets
from neonrain.features import returns, volatility
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


def zigzag(ticker: str, sessions: range) -> list[tuple[str, int, float | None]]:
    """The close e^(i mod 2): the daily log return is +1 at an odd session and -1 at an even one."""
    return [(ticker, i, math.exp(i % 2)) for i in sessions]


def value(out: pl.DataFrame, ticker: str, i: int, column: str) -> float | date | None:
    """One cell of the output, by ticker and session index."""
    return out.filter((pl.col("ticker") == ticker) & (pl.col("date") == CALENDAR[i]))[column].item()


def test_the_lookbacks_are_the_horizons_but_the_three() -> None:
    assert volatility.LOOKBACKS == (5, 21, 63)
    assert set(volatility.LOOKBACKS) == set(targets.HORIZONS) - {3}


def test_the_choices_are_named() -> None:
    assert volatility.ESTIMATOR == "log" and volatility.DDOF == 1 and volatility.ANNUALIZE is False


def test_the_stamp_suffix_and_the_calendar_refusal_are_the_returns_familys() -> None:
    assert volatility.STAMP_SUFFIX == market.STAMP_SUFFIX == returns.STAMP_SUFFIX
    assert volatility.OffCalendar is returns.OffCalendar


def test_the_columns_are_each_feature_then_its_stamp() -> None:
    out = volatility.volatility(frame(zigzag("A", range(70))), CALENDAR)
    assert out.columns == ["ticker", "date", *volatility.feature_columns()]
    assert volatility.feature_columns() == [
        "vol_5", "vol_5_stamp", "vol_21", "vol_21_stamp", "vol_63", "vol_63_stamp"]
    assert out.schema["vol_21"] == pl.Float64 and out.schema["vol_21_stamp"] == pl.Date
    assert market.stamp_columns(out) == {f"vol_{k}": f"vol_{k}_stamp" for k in (5, 21, 63)}


@pytest.mark.parametrize(("column", "i", "expected"), [
    ("vol_5", 5, math.sqrt(1.2)),  # returns at 1..5: +1 -1 +1 -1 +1, sum 1: (5 - 1/5) / 4
    ("vol_5", 6, math.sqrt((5 - 1 / 5) / 4)),  # -1 +1 -1 +1 -1 ... sum -1 at an even session
    ("vol_5", 69, math.sqrt(1.2)),
    ("vol_21", 21, math.sqrt((21 - 1 / 21) / 20)),  # eleven +1 and ten -1
    ("vol_21", 22, math.sqrt((21 - 1 / 21) / 20)),
    ("vol_63", 63, math.sqrt((63 - 1 / 63) / 62)),
    ("vol_63", 69, math.sqrt((63 - 1 / 63) / 62)),
])
def test_each_volatility_is_the_sample_standard_deviation_of_the_last_k_daily_log_returns(
        column: str, i: int, expected: float) -> None:
    out = volatility.volatility(frame(zigzag("A", range(70))), CALENDAR)
    assert value(out, "A", i, column) == pytest.approx(expected)


def test_the_divisor_is_k_minus_one_and_the_mean_is_taken_from_the_returns() -> None:
    # log closes 0, 1, 3, 3, 6, 10: returns 1, 2, 0, 3, 4; mean 2; squares 1 + 0 + 4 + 1 + 4 = 10; var 10 / 4
    closes = [math.exp(s) for s in (0, 1, 3, 3, 6, 10)]
    out = volatility.volatility(frame([("A", i, c) for i, c in enumerate(closes)]), CALENDAR)
    assert value(out, "A", 5, "vol_5") == pytest.approx(math.sqrt(2.5))


def test_a_simple_return_is_not_used() -> None:
    # closes 1 to 6: log returns ln 2, ln 1.5, ln(4/3), ln 1.25, ln 1.2 = .6931 .4055 .2877 .2231 .1823, mean .3583
    r = [math.log(b / a) for a, b in zip(range(1, 6), range(2, 7), strict=True)]
    mean = sum(r) / 5
    expected = math.sqrt(sum((x - mean) ** 2 for x in r) / 4)
    out = volatility.volatility(frame([("A", i, float(i + 1)) for i in range(6)]), CALENDAR)
    assert value(out, "A", 5, "vol_5") == pytest.approx(expected)
    assert expected == pytest.approx(0.2053, abs=1e-4)  # by hand: squares .1121 .0022 .0050 .0183 .0310 sum .1686, over 4, root


def test_a_constant_price_has_no_spread() -> None:
    out = volatility.volatility(frame([("A", i, 7.0) for i in range(70)]), CALENDAR)
    assert value(out, "A", 63, "vol_63") == pytest.approx(0.0, abs=1e-12)
    assert value(out, "A", 63, "vol_63_stamp") == CALENDAR[63]


def test_the_first_k_sessions_have_no_value_and_no_stamp() -> None:
    out = volatility.volatility(frame(zigzag("A", range(70))), CALENDAR)
    for k in volatility.LOOKBACKS:
        for i in range(k):
            assert value(out, "A", i, volatility.name(k)) is None
            assert value(out, "A", i, volatility.name(k) + "_stamp") is None
        assert value(out, "A", k, volatility.name(k)) is not None


def test_the_stamp_is_the_cells_own_date_and_the_frame_passes_the_harnesss_check() -> None:
    out = volatility.volatility(frame(zigzag("A", range(70)) + zigzag("B", range(10, 80))), CALENDAR)
    market.check_stamps(out)
    assert value(out, "A", 40, "vol_21_stamp") == CALENDAR[40]
    assert value(out, "B", 79, "vol_63_stamp") == CALENDAR[79]


def test_changing_every_price_after_t_leaves_the_feature_at_t_unmoved() -> None:
    rows = [(t, i, 10.0 + (i * 7) % 13) for t in ("A", "B") for i in range(80)]
    cut = 70
    changed = [(t, i, c * 3 + 5 if i > cut else c) for t, i, c in rows]
    before = volatility.volatility(frame(rows), CALENDAR)
    after = volatility.volatility(frame(changed), CALENDAR)
    upto = pl.col("date") <= CALENDAR[cut]
    assert before.filter(upto).equals(after.filter(upto))
    assert not before.filter(~upto).equals(after.filter(~upto))


def test_a_value_reads_every_close_of_its_window_but_none_outside_it() -> None:
    rows = [("A", i, 10.0 + (i * 7) % 13) for i in range(30)]
    moved = [(t, i, 99.0 if i == 20 else c) for t, i, c in rows]
    first = volatility.volatility(frame(rows), CALENDAR)
    second = volatility.volatility(frame(moved), CALENDAR)
    for i in (20, 21, 24, 25):  # the windows whose closes, i-5 to i, hold session 20
        assert value(first, "A", i, "vol_5") != value(second, "A", i, "vol_5")
    for i in (19, 26):
        assert value(first, "A", i, "vol_5") is not None
        assert value(first, "A", i, "vol_5") == value(second, "A", i, "vol_5")


def test_a_missing_session_nulls_every_window_that_crosses_it_and_no_other() -> None:
    rows = [r for r in zigzag("A", range(40)) if r[1] != 10]
    out = volatility.volatility(frame(rows), CALENDAR)
    for i in range(11, 16):  # the return at 11 needs the close at 10; a window of 5 returns ends 4 sessions later
        assert value(out, "A", i, "vol_5") is None
    assert value(out, "A", 9, "vol_5") is not None
    assert value(out, "A", 16, "vol_5") == pytest.approx(math.sqrt((5 - 1 / 5) / 4))
    assert value(out, "A", 16, "vol_5_stamp") == CALENDAR[16]
    assert value(out, "A", 31, "vol_21") is None
    assert value(out, "A", 32, "vol_21") is not None
    assert value(out, "A", 32, "vol_21_stamp") == CALENDAR[32]


def test_a_gap_of_a_reused_ticker_keeps_it_whole_and_gives_no_value_across_it() -> None:
    rows = zigzag("A", range(10)) + zigzag("A", range(200, 230))
    out = volatility.volatility(frame(rows), CALENDAR)
    assert out.height == 40
    assert value(out, "A", 9, "vol_5") is not None
    for i in range(200, 205):
        assert value(out, "A", i, "vol_5") is None
    assert value(out, "A", 205, "vol_5") is not None
    assert all(value(out, "A", i, "vol_63") is None for i in range(200, 230))


@pytest.mark.parametrize("bad", [None, 0.0, -2.0, math.nan, math.inf])
def test_an_unusable_close_keeps_its_cell_with_no_value_and_breaks_each_window_through_it(bad: float | None) -> None:
    rows = [(t, i, bad if (t, i) == ("A", 10) else math.exp(i % 2)) for t in ("A", "B") for i in range(20)]
    out = volatility.volatility(frame(rows), CALENDAR)
    assert out.height == 40
    assert value(out, "A", 10, "vol_5") is None and value(out, "A", 10, "vol_5_stamp") is None
    for i in range(11, 16):
        assert value(out, "A", i, "vol_5") is None
    assert value(out, "A", 16, "vol_5") is not None
    assert value(out, "A", 9, "vol_5") is not None
    assert value(out, "B", 12, "vol_5") is not None


def test_tickers_do_not_borrow_from_each_other_and_the_input_order_does_not_matter() -> None:
    a, b = zigzag("A", range(10)), [("B", i, 100.0 * math.exp(i % 3)) for i in range(5, 15)]
    out = volatility.volatility(frame(b[::-1] + a[::-1]), CALENDAR)
    assert out["ticker"].to_list() == ["A"] * 10 + ["B"] * 10
    assert out["date"].to_list()[:10] == CALENDAR[:10]
    assert value(out, "B", 9, "vol_5") is None  # B's first row has no return: five returns need session 10
    assert value(out, "B", 10, "vol_5") is not None
    assert value(out, "A", 9, "vol_5") is not None
    assert out.equals(volatility.volatility(frame(a + b), CALENDAR))


def test_a_lookback_counts_sessions_of_the_calendar_not_calendar_days() -> None:
    days = sessions_of.sessions(2001, 2001)
    assert days[:7] == [date(2001, 1, d) for d in (2, 3, 4, 5, 8, 9, 10)]  # the weekend is no session
    closes = [math.exp(s) for s in (0, 1, 0, 1, 0, 1, 0)]
    prices = pl.DataFrame({"ticker": ["A"] * 7, "date": days[:7], "close": closes}, schema=market.PRICE_COLUMNS)
    out = volatility.volatility(prices, days)
    assert out.filter(pl.col("date") == date(2001, 1, 9))["vol_5"].item() == pytest.approx(math.sqrt(1.2))
    assert out.filter(pl.col("date") == date(2001, 1, 8))["vol_5"].item() is None  # only four returns by Monday
    assert out.filter(pl.col("date") == date(2001, 1, 9))["vol_5_stamp"].item() == date(2001, 1, 9)


def test_a_price_off_the_calendar_is_refused_naming_it() -> None:
    prices = frame(zigzag("A", range(5)))
    with pytest.raises(volatility.OffCalendar, match=r"\(A, 2001-01-04\) is off the calendar"):
        volatility.volatility(prices, [d for d in CALENDAR if d != CALENDAR[3]])


def test_no_prices_give_the_empty_frame_with_the_columns() -> None:
    out = volatility.volatility(frame([]), CALENDAR)
    assert out.height == 0 and out.columns == ["ticker", "date", *volatility.feature_columns()]
    assert volatility.volatility(frame([]), []).height == 0


def test_the_whole_market_check_accepts_the_frame() -> None:
    prices = frame(zigzag("A", range(70)) + zigzag("B", range(70)))
    universe = prices.select("ticker", "date")
    out = volatility.volatility(prices, CALENDAR)
    market.check_market(market.Market(prices, universe, out, CALENDAR))


def test_the_rows_come_out_sorted_by_ticker_then_date_with_the_tickers_interleaved_in_the_input() -> None:
    rows = [(t, i, math.exp(i % 2)) for i in (6, 1, 3, 0, 2, 5, 4) for t in ("B", "A", "C")]
    out = volatility.volatility(frame(rows), CALENDAR)
    assert out.select("ticker", "date").rows() == [(t, CALENDAR[i]) for t in ("A", "B", "C") for i in range(7)]
    assert value(out, "C", 6, "vol_5") == pytest.approx(math.sqrt(1.2))
    assert value(out, "C", 5, "vol_5") == pytest.approx(math.sqrt(1.2))
