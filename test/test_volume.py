"""The volume ratio family (TODO 2.3) on invented frames: tickers A and B, volumes that make every window a sum done by hand.

No real volume is in this file (R-006). Sessions are consecutive integers added to 2001-01-01 unless a test says
otherwise. The main series has the volume i + 1 at session i, so the prior mean of the k sessions before i is
i - (k - 1) / 2 (the mean of i - k + 1 to i) and the ratio is (i + 1) / (i - (k - 1) / 2).
"""
import math
from datetime import date, timedelta

import polars as pl
import pytest

from neonrain import targets
from neonrain.features import common, returns, volatility, volume
from neonrain.harness import market
from neonrain.universe import calendar as sessions_of

FIRST = date(2001, 1, 1)
CALENDAR = [FIRST + timedelta(days=i) for i in range(300)]


def frame(rows: list[tuple[str, int, float | None]], raw: float = 1.0) -> pl.DataFrame:
    """A price frame from (ticker, session index, adjusted volume); the close is 1 and the raw volume `raw` times it."""
    return pl.DataFrame(
        {"ticker": [r[0] for r in rows], "date": [CALENDAR[r[1]] for r in rows], "close": [1.0] * len(rows),
         "volume": [r[2] for r in rows], "raw_volume": [None if r[2] is None else r[2] * raw for r in rows]},
        schema={**market.PRICE_COLUMNS, "volume": pl.Float64, "raw_volume": pl.Float64},
    )


def ramp(ticker: str, sessions: range) -> list[tuple[str, int, float | None]]:
    """The volume i + 1 for session i."""
    return [(ticker, i, float(i + 1)) for i in sessions]


def flat(ticker: str, sessions: range, level: float = 10.0) -> list[tuple[str, int, float | None]]:
    """The same volume on every session."""
    return [(ticker, i, level) for i in sessions]


def value(out: pl.DataFrame, ticker: str, i: int, column: str) -> float | date | None:
    """One cell of the output, by ticker and session index."""
    return out.filter((pl.col("ticker") == ticker) & (pl.col("date") == CALENDAR[i]))[column].item()


def test_the_lookbacks_are_the_horizons_but_the_three() -> None:
    assert volume.LOOKBACKS == (5, 21, 63)
    assert set(volume.LOOKBACKS) == set(targets.HORIZONS) - {3}
    assert volume.LOOKBACKS == volatility.LOOKBACKS


def test_the_choices_are_named() -> None:
    assert volume.VOLUME == "volume" and volume.PRIOR_INCLUDES_T is False and volume.MEAN is True
    assert volume.ZERO_PRIOR_IS_NULL is True and volume.LOG is False


def test_the_shared_helpers_are_one_set_in_every_family() -> None:
    assert common.STAMP_SUFFIX == market.STAMP_SUFFIX
    for family in (returns, volatility, volume):
        assert family.STAMP_SUFFIX == common.STAMP_SUFFIX
        assert family.OffCalendar is common.OffCalendar
    assert returns.positioned is common.positioned and returns.usable is common.usable


def test_the_columns_are_each_feature_then_its_stamp() -> None:
    out = volume.volume_ratios(frame(ramp("A", range(70))), CALENDAR)
    assert out.columns == ["ticker", "date", *volume.feature_columns()]
    assert volume.feature_columns() == ["volr_5", "volr_5_stamp", "volr_21", "volr_21_stamp", "volr_63", "volr_63_stamp"]
    assert out.schema["volr_21"] == pl.Float64 and out.schema["volr_21_stamp"] == pl.Date
    assert market.stamp_columns(out) == {f"volr_{k}": f"volr_{k}_stamp" for k in (5, 21, 63)}


@pytest.mark.parametrize(("column", "i", "expected"), [
    ("volr_5", 5, 6 / 3),  # volume 6 over the mean of 1..5
    ("volr_5", 10, 11 / 8),  # 11 over the mean of 6..10
    ("volr_21", 21, 22 / 11),
    ("volr_21", 30, 31 / 20),
    ("volr_63", 63, 64 / 32),
    ("volr_63", 69, 70 / 38),
])
def test_each_ratio_is_the_volume_over_the_mean_of_the_k_sessions_before(column: str, i: int, expected: float) -> None:
    out = volume.volume_ratios(frame(ramp("A", range(70))), CALENDAR)
    assert value(out, "A", i, column) == pytest.approx(expected)


def test_the_session_itself_is_outside_its_prior_mean() -> None:
    rows = flat("A", range(20))
    rows[10] = ("A", 10, 100.0)
    out = volume.volume_ratios(frame(rows), CALENDAR)
    assert value(out, "A", 10, "volr_5") == pytest.approx(10.0)  # 100 over the mean of ten, not over a mean with itself
    assert value(out, "A", 11, "volr_5") == pytest.approx(10 / 28)  # the prior, sessions 6 to 10: (40 + 100) / 5
    assert value(out, "A", 15, "volr_5") == pytest.approx(10 / 28)  # sessions 10 to 14 are its prior: still the surge
    assert value(out, "A", 16, "volr_5") == pytest.approx(1.0)  # session 16's prior, 11 to 15, has left it


def test_a_mean_is_taken_and_not_a_median() -> None:
    rows = [("A", i, v) for i, v in enumerate([1.0, 1.0, 1.0, 1.0, 11.0, 6.0])]  # prior of session 5: mean 3, median 1
    out = volume.volume_ratios(frame(rows), CALENDAR)
    assert value(out, "A", 5, "volr_5") == pytest.approx(2.0)


def test_the_ratio_is_not_logged() -> None:
    out = volume.volume_ratios(frame(flat("A", range(5)) + [("A", 5, 40.0)]), CALENDAR)
    assert value(out, "A", 5, "volr_5") == pytest.approx(4.0)


def test_the_adjusted_volume_is_used_and_the_raw_volume_is_not() -> None:
    # a 2-for-1 split at session 10: the raw count doubles from there, the adjusted volume is on one basis throughout
    rows = flat("A", range(20))
    raw = [10.0 if i < 10 else 20.0 for i in range(20)]
    prices = frame(rows).with_columns(raw_volume=pl.Series(raw))
    out = volume.volume_ratios(prices, CALENDAR)
    assert value(out, "A", 10, "volr_5") == pytest.approx(1.0)  # the raw volumes would give 2
    by_raw = volume.volume_ratios(prices.with_columns(volume=pl.col("raw_volume")), CALENDAR)
    assert value(by_raw, "A", 10, "volr_5") == pytest.approx(2.0)
    assert volume.volume_ratios(frame(rows, raw=7.0), CALENDAR).equals(volume.volume_ratios(frame(rows), CALENDAR))


def test_zero_volume_at_t_gives_a_ratio_of_zero() -> None:
    rows = flat("A", range(10))
    rows[7] = ("A", 7, 0.0)
    out = volume.volume_ratios(frame(rows), CALENDAR)
    assert value(out, "A", 7, "volr_5") == 0.0
    assert value(out, "A", 7, "volr_5_stamp") == CALENDAR[7]


def test_a_zero_in_the_prior_window_counts_as_a_zero_in_its_mean() -> None:
    rows = flat("A", range(10))
    rows[6] = ("A", 6, 0.0)
    out = volume.volume_ratios(frame(rows), CALENDAR)
    assert value(out, "A", 8, "volr_5") == pytest.approx(10 / 8)  # the prior of 8 is sessions 3 to 7: mean 8


def test_a_zero_prior_mean_gives_null_never_infinity() -> None:
    rows = [("A", i, 0.0) for i in range(6)] + [("A", 6, 5.0), ("A", 7, 0.0)]
    out = volume.volume_ratios(frame(rows), CALENDAR)
    assert value(out, "A", 5, "volr_5") is None and value(out, "A", 5, "volr_5_stamp") is None  # 0 over 0
    assert value(out, "A", 6, "volr_5") is None and value(out, "A", 6, "volr_5_stamp") is None  # 5 over 0
    assert value(out, "A", 7, "volr_5") == 0.0  # the priors 2 to 6 hold the 5: mean 1
    assert out.filter(pl.col("volr_5").is_infinite() | pl.col("volr_5").is_nan()).height == 0


def test_a_prior_mean_that_big_volumes_have_left_is_exactly_zero() -> None:
    rows = [("A", i, 1e9 + 0.1 * i) for i in range(3)] + [("A", i, 0.0) for i in range(3, 12)]
    out = volume.volume_ratios(frame(rows), CALENDAR)
    assert value(out, "A", 8, "volr_5") is None  # the prior, sessions 3 to 7, is all zero
    assert value(out, "A", 7, "volr_5") is not None


def test_the_first_k_sessions_have_no_value_and_no_stamp() -> None:
    out = volume.volume_ratios(frame(ramp("A", range(70))), CALENDAR)
    for k in volume.LOOKBACKS:
        for i in range(k):
            assert value(out, "A", i, volume.name(k)) is None
            assert value(out, "A", i, volume.name(k) + "_stamp") is None
        assert value(out, "A", k, volume.name(k)) is not None


def test_the_stamp_is_the_cells_own_date_and_the_frame_passes_the_harnesss_check() -> None:
    out = volume.volume_ratios(frame(ramp("A", range(70)) + ramp("B", range(10, 80))), CALENDAR)
    market.check_stamps(out)
    assert value(out, "A", 40, "volr_21_stamp") == CALENDAR[40]
    assert value(out, "B", 79, "volr_63_stamp") == CALENDAR[79]


def test_changing_every_price_and_volume_after_t_leaves_the_feature_at_t_unmoved() -> None:
    rows = [(t, i, 10.0 + (i * 7) % 13) for t in ("A", "B") for i in range(80)]
    cut = 70
    before_frame = frame(rows)
    after_frame = before_frame.with_columns(
        close=pl.when(pl.col("date") > CALENDAR[cut]).then(pl.col("close") * 3 + 5).otherwise(pl.col("close")),
        volume=pl.when(pl.col("date") > CALENDAR[cut]).then(pl.col("volume") * 3 + 5).otherwise(pl.col("volume")),
        raw_volume=pl.when(pl.col("date") > CALENDAR[cut]).then(pl.col("raw_volume") * 3 + 5).otherwise(pl.col("raw_volume")),
    )
    before = volume.volume_ratios(before_frame, CALENDAR)
    after = volume.volume_ratios(after_frame, CALENDAR)
    upto = pl.col("date") <= CALENDAR[cut]
    assert before.filter(upto).equals(after.filter(upto))
    assert not before.filter(~upto).equals(after.filter(~upto))


def test_a_value_reads_the_volume_at_t_and_the_k_sessions_before_but_none_outside() -> None:
    rows = [("A", i, 10.0 + (i * 7) % 13) for i in range(30)]
    moved = [(t, i, 99.0 if i == 20 else c) for t, i, c in rows]
    first = volume.volume_ratios(frame(rows), CALENDAR)
    second = volume.volume_ratios(frame(moved), CALENDAR)
    for i in (20, 21, 24, 25):  # t = 20 itself, and the windows whose priors, sessions i-5 to i-1, hold session 20
        assert value(first, "A", i, "volr_5") != value(second, "A", i, "volr_5")
    for i in (19, 26):
        assert value(first, "A", i, "volr_5") is not None
        assert value(first, "A", i, "volr_5") == value(second, "A", i, "volr_5")


def test_a_missing_session_nulls_every_window_that_crosses_it_and_no_other() -> None:
    rows = [r for r in ramp("A", range(40)) if r[1] != 10]
    out = volume.volume_ratios(frame(rows), CALENDAR)
    for i in range(11, 16):  # the window of i holds session 10 for i - 5 <= 10 <= i
        assert value(out, "A", i, "volr_5") is None
    assert value(out, "A", 9, "volr_5") is not None
    assert value(out, "A", 16, "volr_5") == pytest.approx(17 / 14)
    assert value(out, "A", 16, "volr_5_stamp") == CALENDAR[16]
    assert value(out, "A", 31, "volr_21") is None
    assert value(out, "A", 32, "volr_21") is not None


def test_a_gap_of_a_reused_ticker_keeps_it_whole_and_gives_no_value_across_it() -> None:
    rows = ramp("A", range(10)) + ramp("A", range(200, 230))
    out = volume.volume_ratios(frame(rows), CALENDAR)
    assert out.height == 40
    assert value(out, "A", 9, "volr_5") is not None
    for i in range(200, 205):
        assert value(out, "A", i, "volr_5") is None
    assert value(out, "A", 205, "volr_5") is not None
    assert all(value(out, "A", i, "volr_63") is None for i in range(200, 230))


@pytest.mark.parametrize("bad", [None, -2.0, math.nan, math.inf, -math.inf])
def test_an_unusable_volume_keeps_its_cell_with_no_value_and_breaks_each_window_through_it(bad: float | None) -> None:
    rows = [(t, i, bad if (t, i) == ("A", 10) else 10.0 + i) for t in ("A", "B") for i in range(20)]
    out = volume.volume_ratios(frame(rows), CALENDAR)
    assert out.height == 40
    assert value(out, "A", 10, "volr_5") is None and value(out, "A", 10, "volr_5_stamp") is None
    for i in range(11, 16):
        assert value(out, "A", i, "volr_5") is None
    assert value(out, "A", 16, "volr_5") is not None
    assert value(out, "A", 9, "volr_5") is not None
    assert value(out, "B", 12, "volr_5") is not None


def test_tickers_do_not_borrow_from_each_other_and_the_input_order_does_not_matter() -> None:
    a, b = ramp("A", range(10)), [("B", i, 100.0 * (i % 3 + 1)) for i in range(5, 15)]
    out = volume.volume_ratios(frame(b[::-1] + a[::-1]), CALENDAR)
    assert out["ticker"].to_list() == ["A"] * 10 + ["B"] * 10
    assert out["date"].to_list()[:10] == CALENDAR[:10]
    assert value(out, "B", 9, "volr_5") is None  # B's first row is session 5
    assert value(out, "B", 10, "volr_5") == pytest.approx(200 / 200)  # 200 over the mean of 100 200 300 100 200
    assert value(out, "A", 9, "volr_5") == pytest.approx(10 / 7)
    assert out.equals(volume.volume_ratios(frame(a + b), CALENDAR))


def test_a_lookback_counts_sessions_of_the_calendar_not_calendar_days() -> None:
    days = sessions_of.sessions(2001, 2001)
    assert days[:7] == [date(2001, 1, d) for d in (2, 3, 4, 5, 8, 9, 10)]  # the weekend is no session
    prices = pl.DataFrame(
        {"ticker": ["A"] * 7, "date": days[:7], "close": [1.0] * 7, "volume": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]},
        schema={**market.PRICE_COLUMNS, "volume": pl.Float64})
    out = volume.volume_ratios(prices, days)
    assert out.filter(pl.col("date") == date(2001, 1, 9))["volr_5"].item() == pytest.approx(2.0)
    assert out.filter(pl.col("date") == date(2001, 1, 8))["volr_5"].item() is None  # only four sessions before Monday
    assert out.filter(pl.col("date") == date(2001, 1, 9))["volr_5_stamp"].item() == date(2001, 1, 9)


def test_a_price_off_the_calendar_is_refused_naming_it() -> None:
    prices = frame(ramp("A", range(5)))
    with pytest.raises(volume.OffCalendar, match=r"\(A, 2001-01-04\) is off the calendar"):
        volume.volume_ratios(prices, [d for d in CALENDAR if d != CALENDAR[3]])


def test_no_prices_give_the_empty_frame_with_the_columns() -> None:
    out = volume.volume_ratios(frame([]), CALENDAR)
    assert out.height == 0 and out.columns == ["ticker", "date", *volume.feature_columns()]
    assert volume.volume_ratios(frame([]), []).height == 0


def test_the_whole_market_check_accepts_the_frame() -> None:
    prices = frame(ramp("A", range(70)) + ramp("B", range(70)))
    universe = prices.select("ticker", "date")
    out = volume.volume_ratios(prices, CALENDAR)
    market.check_market(market.Market(prices, universe, out, CALENDAR))


def test_the_rows_come_out_sorted_by_ticker_then_date_with_the_tickers_interleaved_in_the_input() -> None:
    rows = [(t, i, 2.0 + i) for i in (6, 1, 3, 0, 2, 5, 4) for t in ("B", "A", "C")]
    out = volume.volume_ratios(frame(rows), CALENDAR)
    assert out.select("ticker", "date").rows() == [(t, CALENDAR[i]) for t in ("A", "B", "C") for i in range(7)]
    assert value(out, "C", 6, "volr_5") == pytest.approx(8 / 5)
    assert value(out, "C", 5, "volr_5") == pytest.approx(7 / 4)
