"""The indicator family (TODO 2.3) on invented frames: tickers A and B, closes that make every window a sum done by hand.

No real price is in this file (R-006). Sessions are consecutive integers added to 2001-01-01 unless a test says
otherwise. Where a value is "by hand" the arithmetic is in the comment beside it; the MACD of the real settings is
checked against a second, plain-Python computation of the same definition (a loop, not the module's shifts).
"""
import math
from datetime import date, timedelta

import polars as pl
import pytest

from neonrain import targets
from neonrain.features import common, indicators, returns, volatility, volume
from neonrain.harness import market
from neonrain.universe import calendar as sessions_of

FIRST = date(2001, 1, 1)
CALENDAR = [FIRST + timedelta(days=i) for i in range(300)]
WINDOWS = {"rsi_14": 15, "macd": 26, "macd_hist": 34, "mar_5": 5, "mar_21": 21, "mar_63": 63}  # closes each value reads


def frame(rows: list[tuple[str, int, float | None]]) -> pl.DataFrame:
    """A price frame from (ticker, session index, adjusted close)."""
    return pl.DataFrame(
        {"ticker": [r[0] for r in rows], "date": [CALENDAR[r[1]] for r in rows], "close": [r[2] for r in rows]},
        schema=market.PRICE_COLUMNS,
    )


def series(ticker: str, closes: list[float]) -> list[tuple[str, int, float | None]]:
    """The closes at sessions 0, 1, 2, ..."""
    return [(ticker, i, c) for i, c in enumerate(closes)]


def ramp(ticker: str, sessions: range) -> list[tuple[str, int, float | None]]:
    """The close i + 1 at session i."""
    return [(ticker, i, float(i + 1)) for i in sessions]


def noisy(n: int) -> list[float]:
    """A deterministic series that rises and falls without repeating inside any window used here."""
    return [20.0 + (i * 7) % 13 + (i * 3) % 5 * 0.5 for i in range(n)]


def value(out: pl.DataFrame, ticker: str, i: int, column: str) -> float | date | None:
    """One cell of the output, by ticker and session index."""
    return out.filter((pl.col("ticker") == ticker) & (pl.col("date") == CALENDAR[i]))[column].item()


def rows_of(prices: pl.DataFrame) -> pl.DataFrame:
    """The frame as the per-indicator functions take it: usable rows with `pos`, sorted by (ticker, pos)."""
    return common.positioned(prices, CALENDAR).sort("ticker", "pos").filter(common.usable())


def plain_ema(xs: list[float], span: int) -> float:
    """The exponential average of the last `span` values of xs, newest weighted most, written out as a loop."""
    keep = 1 - 2 / (span + 1)
    return sum(keep**j * xs[-1 - j] for j in range(span)) / sum(keep**j for j in range(span))


def plain_macd(closes: list[float], t: int) -> tuple[float, float]:
    """(line, histogram) at index t divided by the close at t, from the real settings, the definition in a loop."""
    def line(u: int) -> float:
        return plain_ema(closes[: u + 1], 12) - plain_ema(closes[: u + 1], 26)

    signal = plain_ema([line(u) for u in range(t - 8, t + 1)], 9)
    return line(t) / closes[t], (line(t) - signal) / closes[t]


def test_the_choices_are_named() -> None:
    assert (indicators.RSI_PERIOD, indicators.MACD_FAST, indicators.MACD_SLOW, indicators.MACD_SIGNAL) == (14, 12, 26, 9)
    assert indicators.FLAT_RSI_IS_NULL is True and indicators.SCALE_BY_CLOSE is True
    assert indicators.PRICE_IN_ITS_MEAN is True and indicators.CLOSE == "close"
    assert indicators.MACD_COLUMNS == ("macd", "macd_hist")


def test_the_moving_average_windows_are_the_horizons_but_the_three() -> None:
    assert indicators.MA_WINDOWS == (5, 21, 63)
    assert set(indicators.MA_WINDOWS) == set(targets.HORIZONS) - {3}
    assert indicators.MA_WINDOWS == volatility.LOOKBACKS == volume.LOOKBACKS


def test_the_shared_helpers_are_one_set_in_every_family() -> None:
    assert common.STAMP_SUFFIX == market.STAMP_SUFFIX
    for family in (returns, volatility, volume, indicators):
        assert family.STAMP_SUFFIX == common.STAMP_SUFFIX
        assert family.OffCalendar is common.OffCalendar


def test_the_columns_are_each_feature_then_its_stamp() -> None:
    out = indicators.indicators(frame(series("A", noisy(70))), CALENDAR)
    expected = ["rsi_14", "rsi_14_stamp", "macd", "macd_stamp", "macd_hist", "macd_hist_stamp",
                "mar_5", "mar_5_stamp", "mar_21", "mar_21_stamp", "mar_63", "mar_63_stamp"]
    assert indicators.feature_columns() == expected
    assert out.columns == ["ticker", "date", *expected]
    assert indicators.rsi_name() == "rsi_14" and indicators.ratio_name(21) == "mar_21"
    assert out.schema["macd_hist"] == pl.Float64 and out.schema["macd_hist_stamp"] == pl.Date
    assert market.stamp_columns(out) == {c: c + "_stamp" for c in expected[::2]}


def test_the_exponential_weights_add_to_one_and_are_the_textbooks_cut_at_the_span() -> None:
    assert indicators.ema_weights(2) == pytest.approx([3 / 4, 1 / 4])  # a = 2/3: (2/3, 2/9) over 8/9
    assert indicators.ema_weights(3) == pytest.approx([4 / 7, 2 / 7, 1 / 7])  # a = 1/2: (1/2, 1/4, 1/8) over 7/8
    for span in (1, 9, 12, 26):
        weights = indicators.ema_weights(span)
        assert len(weights) == span and sum(weights) == pytest.approx(1.0)
        assert all(a > b for a, b in zip(weights, weights[1:], strict=False))
    assert indicators.ema_weights(1) == [1.0]
    assert indicators.ema_weights(26)[1] / indicators.ema_weights(26)[0] == pytest.approx(25 / 27)


# ---- RSI

def test_rsi_by_hand_over_the_last_fourteen_changes() -> None:
    closes = [10, 11, 10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16, 15, 15]
    out = indicators.indicators(frame(series("A", [float(c) for c in closes])), CALENDAR)
    # changes of sessions 1 to 14: gains 1 and six 2s = 13, losses seven 1s = 7: 100 * 13 / 20
    assert value(out, "A", 14, "rsi_14") == pytest.approx(65.0)
    # session 15 drops the first gain (1) and adds a loss of 1: G = 12, L = 8
    assert value(out, "A", 15, "rsi_14") == pytest.approx(60.0)
    # session 16 drops the loss of session 2 and adds a change of 0: G = 12, L = 7
    assert value(out, "A", 16, "rsi_14") == pytest.approx(100 * 12 / 19)
    assert value(out, "A", 14, "rsi_14_stamp") == CALENDAR[14]


def test_rsi_is_100_when_nothing_fell_and_0_when_nothing_rose() -> None:
    up = indicators.indicators(frame(ramp("A", range(20))), CALENDAR)
    down = indicators.indicators(frame(series("A", [100.0 - i for i in range(20)])), CALENDAR)
    assert value(up, "A", 14, "rsi_14") == 100.0 and value(up, "A", 19, "rsi_14") == 100.0
    assert value(down, "A", 14, "rsi_14") == 0.0 and value(down, "A", 19, "rsi_14") == 0.0


def test_a_flat_window_gives_null_never_a_division_by_zero() -> None:
    closes = [10.0] * 14 + [11.0] + [11.0] * 20  # the rise at session 14 leaves the window of session 28
    out = indicators.indicators(frame(series("A", closes)), CALENDAR)
    assert value(out, "A", 13, "rsi_14") is None
    assert value(out, "A", 14, "rsi_14") == 100.0  # one gain, no loss
    assert value(out, "A", 27, "rsi_14") == 100.0
    assert value(out, "A", 28, "rsi_14") is None and value(out, "A", 28, "rsi_14_stamp") is None
    assert value(out, "A", 34, "rsi_14") is None
    assert out.filter(pl.col("rsi_14").is_infinite() | pl.col("rsi_14").is_nan()).height == 0


def test_the_rsi_is_the_same_at_any_price_level() -> None:
    base = noisy(40)
    one = indicators.indicators(frame(series("A", base)), CALENDAR)
    scaled = indicators.indicators(frame(series("A", [c * 250.0 for c in base])), CALENDAR)
    assert [v for v in one["rsi_14"].to_list() if v is not None] == pytest.approx(
        [v for v in scaled["rsi_14"].to_list() if v is not None])
    assert one["rsi_14"].null_count() == scaled["rsi_14"].null_count() == 14


# ---- MACD

def test_the_macd_by_hand_on_spans_two_three_and_two() -> None:
    prices = frame(series("A", [10.0, 12.0, 11.0, 15.0, 14.0]))
    out = indicators.of_macd(rows_of(prices), 2, 3, 2)
    # line = (3/4 c + 1/4 c_prev) - (4/7 c + 2/7 c_prev + 1/7 c_prev2): 3/28 at 2, 4/7 at 3, 11/28 at 4
    line = out["macd"].to_list()
    assert line[:2] == [None, None]
    assert line[2:] == pytest.approx([3 / 28 / 11, 4 / 7 / 15, 11 / 28 / 14])
    # signal = 3/4 line + 1/4 line_prev: 51/112 at 3, 7/16 at 4; the histogram is line - signal, over the close
    hist = out["macd_hist"].to_list()
    assert hist[:3] == [None, None, None]
    assert hist[3:] == pytest.approx([13 / 112 / 15, -5 / 112 / 14])
    assert out["macd_stamp"].to_list()[1:3] == [None, CALENDAR[2]]
    assert out["macd_hist_stamp"].to_list()[2:] == [None, CALENDAR[3], CALENDAR[4]]


@pytest.mark.parametrize("t", [33, 34, 40, 59])
def test_the_macd_of_the_real_settings_is_the_definition_written_as_a_loop(t: int) -> None:
    closes = noisy(60)
    out = indicators.indicators(frame(series("A", closes)), CALENDAR)
    line, hist = plain_macd(closes, t)
    assert value(out, "A", t, "macd") == pytest.approx(line, rel=1e-9)
    assert value(out, "A", t, "macd_hist") == pytest.approx(hist, rel=1e-9)


def test_the_first_values_come_after_the_warm_up() -> None:
    out = indicators.indicators(frame(series("A", noisy(70))), CALENDAR)
    assert all(value(out, "A", i, "macd") is None for i in range(25))
    assert value(out, "A", 25, "macd") is not None  # 26 closes
    assert all(value(out, "A", i, "macd_hist") is None for i in range(33))
    assert value(out, "A", 33, "macd_hist") is not None  # 26 + 9 - 1 = 34 closes
    assert all(value(out, "A", i, "rsi_14") is None for i in range(14)) and value(out, "A", 14, "rsi_14") is not None
    for k in indicators.MA_WINDOWS:
        assert all(value(out, "A", i, f"mar_{k}") is None for i in range(k - 1))
        assert value(out, "A", k - 1, f"mar_{k}") is not None


def test_the_macd_is_a_fraction_of_the_price_and_the_same_at_any_price_level() -> None:
    base = noisy(50)
    one = indicators.indicators(frame(series("A", base)), CALENDAR)
    scaled = indicators.indicators(frame(series("A", [c * 1000.0 for c in base])), CALENDAR)
    for column in ("macd", "macd_hist"):
        assert scaled[column].drop_nulls().to_list() == pytest.approx(one[column].drop_nulls().to_list())
    # a steady 1% a day: the line is the same fraction of the price at every session
    grown = indicators.indicators(frame(series("A", [100 * 1.01**i for i in range(60)])), CALENDAR)
    lines = [value(grown, "A", i, "macd") for i in range(40, 60)]
    assert max(lines) - min(lines) == pytest.approx(0.0, abs=1e-12)
    assert lines[0] > 0


def test_a_flat_close_gives_a_macd_of_zero() -> None:
    out = indicators.indicators(frame(series("A", [50.0] * 40)), CALENDAR)
    assert value(out, "A", 39, "macd") == pytest.approx(0.0, abs=1e-12)
    assert value(out, "A", 39, "macd_hist") == pytest.approx(0.0, abs=1e-12)


# ---- the moving-average ratios

@pytest.mark.parametrize(("column", "i", "expected"), [
    ("mar_5", 4, 5 / 3),  # closes 1 to 5, mean 3
    ("mar_5", 10, 11 / 9),  # closes 7 to 11, mean 9
    ("mar_21", 20, 21 / 11),
    ("mar_21", 30, 31 / 21),
    ("mar_63", 62, 63 / 32),
    ("mar_63", 69, 70 / 39),
])
def test_each_ratio_is_the_close_over_the_mean_of_the_k_closes_ending_at_t(column: str, i: int, expected: float) -> None:
    out = indicators.indicators(frame(ramp("A", range(70))), CALENDAR)
    assert value(out, "A", i, column) == pytest.approx(expected)


def test_t_is_inside_its_own_mean() -> None:
    out = indicators.indicators(frame(series("A", [10.0] * 4 + [20.0])), CALENDAR)
    assert value(out, "A", 4, "mar_5") == pytest.approx(20 / 12)  # mean (40 + 20) / 5 = 12, not 10
    assert value(out, "A", 4, "mar_5_stamp") == CALENDAR[4]


def test_a_price_on_its_mean_reads_one() -> None:
    out = indicators.indicators(frame(series("A", [10.0] * 30)), CALENDAR)
    assert value(out, "A", 29, "mar_5") == 1.0 and value(out, "A", 29, "mar_21") == 1.0


# ---- the rules every family keeps

def test_the_stamp_is_the_cells_own_date_and_the_frame_passes_the_harnesss_check() -> None:
    out = indicators.indicators(frame(series("A", noisy(80)) + series("B", noisy(90))[10:]), CALENDAR)
    market.check_stamps(out)
    for column in WINDOWS:
        assert value(out, "A", 70, column + "_stamp") == CALENDAR[70]
    assert out.select(c for c in out.columns if c.endswith("_stamp")).null_count().row(0) != (0,) * 6


@pytest.mark.parametrize("column", list(WINDOWS))
def test_a_value_reads_its_window_of_closes_and_none_outside(column: str) -> None:
    n, t = WINDOWS[column], 90
    closes = noisy(100)
    first = indicators.indicators(frame(series("A", closes)), CALENDAR)
    outside = indicators.indicators(frame(series("A", [999.0 if i == t - n else c for i, c in enumerate(closes)])), CALENDAR)
    oldest = indicators.indicators(frame(series("A", [999.0 if i == t - n + 1 else c for i, c in enumerate(closes)])), CALENDAR)
    assert value(first, "A", t, column) is not None
    assert value(first, "A", t, column) == value(outside, "A", t, column)
    assert value(first, "A", t, column) != value(oldest, "A", t, column)


def test_changing_every_close_after_t_leaves_the_features_at_t_unmoved() -> None:
    rows = [(t, i, c) for t in ("A", "B") for i, c in enumerate(noisy(120))]
    cut = 100
    before_frame = frame(rows)
    after_frame = before_frame.with_columns(
        close=pl.when(pl.col("date") > CALENDAR[cut]).then(pl.col("close") * 3 + 5).otherwise(pl.col("close")))
    before = indicators.indicators(before_frame, CALENDAR)
    after = indicators.indicators(after_frame, CALENDAR)
    upto = pl.col("date") <= CALENDAR[cut]
    assert before.filter(upto).equals(after.filter(upto))
    assert not before.filter(~upto).equals(after.filter(~upto))


def test_the_same_input_gives_the_same_output_and_the_start_of_the_sample_does_not_matter() -> None:
    closes = noisy(150)
    whole_sample = indicators.indicators(frame(series("A", closes)), CALENDAR)
    assert whole_sample.equals(indicators.indicators(frame(series("A", closes)), CALENDAR))
    later = indicators.indicators(frame([("A", i, closes[i]) for i in range(40, 150)]), CALENDAR)
    for column in WINDOWS:  # a sample that starts at session 40 gives, after its own warm-up, the same values
        for i in (110, 149):
            assert value(later, "A", i, column) == value(whole_sample, "A", i, column)


@pytest.mark.parametrize("column", list(WINDOWS))
def test_a_missing_session_nulls_every_window_that_crosses_it_and_no_other(column: str) -> None:
    n = WINDOWS[column]
    rows = [r for r in series("A", noisy(150)) if r[1] != 70]
    out = indicators.indicators(frame(rows), CALENDAR)
    for i in range(71, 70 + n):  # a window of n closes ending at i holds session 70 for i - n + 1 <= 70
        assert value(out, "A", i, column) is None
        assert value(out, "A", i, column + "_stamp") is None
    assert value(out, "A", 70 + n, column) is not None
    assert value(out, "A", 69, column) is not None
    assert out.height == 149


def test_a_gap_of_a_reused_ticker_keeps_it_whole_and_gives_no_value_across_it() -> None:
    rows = series("A", noisy(60)) + [("A", 200 + i, 30.0 + i % 7) for i in range(80)]
    out = indicators.indicators(frame(rows), CALENDAR)
    assert out.height == 140
    assert value(out, "A", 59, "macd_hist") is not None
    for column, n in WINDOWS.items():
        assert all(value(out, "A", i, column) is None for i in range(200, 200 + n - 1))
        assert value(out, "A", 200 + n - 1, column) is not None


@pytest.mark.parametrize("bad", [None, -2.0, 0.0, math.nan, math.inf])
def test_an_unusable_close_keeps_its_cell_with_no_value_and_breaks_each_window_through_it(bad: float | None) -> None:
    rows = [(t, i, bad if (t, i) == ("A", 40) else c) for t in ("A", "B") for i, c in enumerate(noisy(110))]
    out = indicators.indicators(frame(rows), CALENDAR)
    assert out.height == 220
    for column, n in WINDOWS.items():
        for i in (40, 41, 40 + n - 1):
            assert value(out, "A", i, column) is None and value(out, "A", i, column + "_stamp") is None
        assert value(out, "A", 40 + n, column) is not None
        assert value(out, "B", 45, column) is not None or n > 45
        assert value(out, "B", 40 + n - 1, column) is not None


def test_tickers_do_not_borrow_from_each_other_and_the_input_order_does_not_matter() -> None:
    a, b = series("A", noisy(50)), [("B", i + 5, 100.0 + (i * 3) % 11) for i in range(60)]
    out = indicators.indicators(frame(b[::-1] + a[::-1]), CALENDAR)
    assert out.select("ticker", "date").rows() == [("A", CALENDAR[i]) for i in range(50)] + [("B", CALENDAR[i + 5]) for i in range(60)]
    assert value(out, "B", 8, "mar_5") is None and value(out, "B", 9, "mar_5") is not None  # B's first row is session 5
    assert value(out, "B", 18, "rsi_14") is None and value(out, "B", 19, "rsi_14") is not None
    assert out.equals(indicators.indicators(frame(a + b), CALENDAR))
    alone = indicators.indicators(frame(b), CALENDAR).filter(pl.col("ticker") == "B")
    assert out.filter(pl.col("ticker") == "B").equals(alone)


def test_a_window_counts_sessions_of_the_calendar_not_calendar_days() -> None:
    days = sessions_of.sessions(2001, 2001)
    assert days[:7] == [date(2001, 1, d) for d in (2, 3, 4, 5, 8, 9, 10)]  # the weekend is no session
    prices = pl.DataFrame({"ticker": ["A"] * 7, "date": days[:7], "close": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]},
                          schema=market.PRICE_COLUMNS)
    out = indicators.indicators(prices, days)
    assert out.filter(pl.col("date") == date(2001, 1, 8))["mar_5"].item() == pytest.approx(5 / 3)  # Monday: 5 sessions
    assert out.filter(pl.col("date") == date(2001, 1, 5))["mar_5"].item() is None


def test_a_price_off_the_calendar_is_refused_naming_it() -> None:
    with pytest.raises(indicators.OffCalendar, match=r"\(A, 2001-01-04\) is off the calendar"):
        indicators.indicators(frame(ramp("A", range(5))), [d for d in CALENDAR if d != CALENDAR[3]])


def test_no_prices_give_the_empty_frame_with_the_columns() -> None:
    out = indicators.indicators(frame([]), CALENDAR)
    assert out.height == 0 and out.columns == ["ticker", "date", *indicators.feature_columns()]
    assert indicators.indicators(frame([]), []).height == 0


def test_no_value_is_infinite_or_nan() -> None:
    rows = series("A", [10.0] * 30 + [10.0 + i for i in range(40)]) + series("B", [5.0] * 70)
    out = indicators.indicators(frame(rows), CALENDAR)
    for column in indicators.feature_columns():
        if not column.endswith("_stamp"):
            assert out.filter(pl.col(column).is_infinite() | pl.col(column).is_nan()).height == 0


def test_the_whole_market_check_accepts_the_frame() -> None:
    prices = frame(series("A", noisy(100)) + series("B", noisy(100)))
    universe = prices.select("ticker", "date")
    out = indicators.indicators(prices, CALENDAR)
    market.check_market(market.Market(prices, universe, out, CALENDAR))


def test_the_rows_come_out_sorted_by_ticker_then_date_with_the_tickers_interleaved_in_the_input() -> None:
    rows = [(t, i, 2.0 + i) for i in (6, 1, 3, 0, 2, 5, 4) for t in ("B", "A", "C")]
    out = indicators.indicators(frame(rows), CALENDAR)
    assert out.select("ticker", "date").rows() == [(t, CALENDAR[i]) for t in ("A", "B", "C") for i in range(7)]
    assert value(out, "C", 6, "mar_5") == pytest.approx(8 / 6)  # closes 4 to 8, mean 6
