"""Membership (TODO 2.1 b): spans, the trailing median dollar volume, and the universe, on frames invented here.

No real price is in this file (R-006): tickers are A, B, C and the numbers are round ones chosen so each median can
be read off by hand. `sessions(n)` is n consecutive weekdays from 2001-01-01 standing in for a calendar.
"""
from datetime import date, timedelta

import polars as pl
import pytest

from neonrain.universe import membership


def sessions(count: int) -> list[date]:
    """`count` consecutive weekdays from Monday 2001-01-01."""
    days = []
    day = date(2001, 1, 1)
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return days


def frame(rows: list[tuple[str, date, float, float]]) -> pl.DataFrame:
    """A price frame from (ticker, date, close, volume) rows."""
    return pl.DataFrame(rows, schema={"ticker": pl.String, "date": pl.Date, "close": pl.Float64, "volume": pl.Float64}, orient="row")


def steady(ticker: str, days: list[date], dollars: float) -> list[tuple[str, date, float, float]]:
    """One row per day with close 1 and volume `dollars`, so the dollar volume is `dollars`."""
    return [(ticker, day, 1.0, dollars) for day in days]


def small(monkeypatch: pytest.MonkeyPatch, size: int, window: int, observed: int) -> None:
    """Shrink the three constants so a few rows can show the rule."""
    monkeypatch.setattr(membership, "UNIVERSE_SIZE", size)
    monkeypatch.setattr(membership, "WINDOW_SESSIONS", window)
    monkeypatch.setattr(membership, "MIN_OBSERVED", observed)


def test_the_constants_are_the_plans() -> None:
    assert (membership.UNIVERSE_SIZE, membership.WINDOW_SESSIONS, membership.MIN_OBSERVED) == (1000, 63, 63)


def test_spans_are_each_tickers_first_and_last_date_sorted_by_ticker() -> None:
    days = sessions(5)
    prices = frame(steady("B", days[1:4], 1.0) + steady("A", [days[0], days[4]], 1.0))
    got = membership.spans(prices)
    assert got.columns == ["ticker", "first", "last"]
    assert got.rows() == [("A", days[0], days[4]), ("B", days[1], days[3])]


def test_a_gap_inside_a_span_does_not_shorten_it() -> None:
    days = sessions(10)
    got = membership.spans(frame(steady("A", [days[0], days[9]], 1.0)))
    assert got.rows() == [("A", days[0], days[9])]


def test_the_median_is_over_the_window_ending_on_the_day(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 10, 3, 3)
    days = sessions(5)
    rows = [("A", day, 1.0, volume) for day, volume in zip(days, [1.0, 9.0, 2.0, 100.0, 4.0])]
    got = membership.median_dollar_volume(frame(rows), days)
    assert got.columns == ["ticker", "date", "median_dv"]
    assert got.sort("date").rows() == [("A", days[2], 2.0), ("A", days[3], 9.0), ("A", days[4], 4.0)]


def test_dollar_volume_is_raw_close_times_volume(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 10, 2, 2)
    days = sessions(2)
    got = membership.median_dollar_volume(frame([("A", days[0], 3.0, 5.0), ("A", days[1], 7.0, 5.0)]), days)
    assert got.rows() == [("A", days[1], 25.0)]


def test_a_name_with_too_few_observations_has_no_median(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 10, 3, 3)
    days = sessions(4)
    rows = steady("A", days, 5.0) + steady("B", [days[0], days[2], days[3]], 5.0)
    got = membership.median_dollar_volume(frame(rows), days)
    assert got.sort("ticker", "date").rows() == [("A", days[2], 5.0), ("A", days[3], 5.0)]


def test_fewer_observations_are_enough_when_the_minimum_is_lower(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 10, 3, 2)
    days = sessions(3)
    got = membership.median_dollar_volume(frame(steady("A", days[1:], 5.0)), days)
    assert got.rows() == [("A", days[2], 5.0)]


def test_a_missing_row_counts_against_the_window_not_for_it(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 10, 3, 2)
    days = sessions(6)
    rows = [("A", days[0], 1.0, 1.0), ("A", days[1], 1.0, 50.0), ("A", days[4], 1.0, 7.0), ("A", days[5], 1.0, 9.0)]
    rows += steady("B", [days[2], days[3]], 1.0)
    got = membership.median_dollar_volume(frame(rows), days).filter(pl.col("ticker") == "A")
    assert got.sort("date").rows() == [("A", days[1], 25.5), ("A", days[5], 8.0)]


def test_a_session_nobody_traded_is_skipped_in_the_count(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 10, 3, 3)
    days = sessions(5)
    got = membership.median_dollar_volume(frame(steady("A", [days[0], days[1], days[3], days[4]], 5.0)), days)
    assert got.sort("date").rows() == [("A", days[3], 5.0), ("A", days[4], 5.0)]


def test_a_date_that_is_no_session_is_not_counted(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 10, 2, 2)
    days = sessions(3)
    saturday = days[0] + timedelta(days=5)
    rows = steady("A", days, 5.0) + steady("A", [saturday], 1000.0)
    got = membership.median_dollar_volume(frame(rows), days)
    assert got.sort("date").rows() == [("A", days[1], 5.0), ("A", days[2], 5.0)]


def test_a_null_volume_is_not_an_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 10, 2, 2)
    days = sessions(3)
    rows = [("A", days[0], 1.0, 4.0), ("A", days[1], 1.0, None), ("A", days[2], 1.0, 6.0)]
    got = membership.median_dollar_volume(frame(rows), days)
    assert got.rows() == []


def test_the_universe_keeps_the_largest_and_breaks_ties_by_ticker(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 2, 2, 2)
    days = sessions(2)
    rows = steady("C", days, 5.0) + steady("B", days, 9.0) + steady("A", days, 5.0) + steady("D", days, 1.0)
    got = membership.universe(frame(rows), days)
    assert got.columns == ["ticker", "date"]
    assert got.rows() == [("A", days[1]), ("B", days[1])]


def test_the_universe_holds_every_name_when_fewer_than_the_size(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 5, 2, 2)
    days = sessions(3)
    rows = steady("A", days, 5.0) + steady("B", days, 6.0)
    got = membership.universe(frame(rows), days)
    assert got.rows() == [("A", days[1]), ("B", days[1]), ("A", days[2]), ("B", days[2])]


def test_a_name_leaves_the_day_it_has_no_price_and_a_delisted_name_stays_until_then(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 5, 2, 2)
    days = sessions(4)
    rows = steady("A", days, 5.0) + steady("B", days[:3], 6.0)
    got = membership.universe(frame(rows), days)
    assert got.filter(pl.col("ticker") == "B")["date"].to_list() == [days[1], days[2]]
    assert got.filter(pl.col("ticker") == "A")["date"].to_list() == [days[1], days[2], days[3]]


def test_the_universe_on_a_date_is_unmoved_by_every_later_row(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 1, 3, 3)
    days = sessions(8)
    before = steady("A", days[:5], 5.0) + steady("B", days[:5], 4.0)
    later_a = steady("A", days[5:], 1.0) + steady("B", days[5:], 900.0)
    later_b = steady("A", days[5:], 900.0)
    first = membership.universe(frame(before + later_a), days)
    second = membership.universe(frame(before + later_b), days)
    cut = days[4]
    assert first.filter(pl.col("date") <= cut).equals(second.filter(pl.col("date") <= cut))
    assert first.filter(pl.col("date") <= cut)["ticker"].unique().to_list() == ["A"]


def test_the_day_itself_counts_in_its_own_window(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 1, 3, 3)
    days = sessions(3)
    rows = [("A", days[0], 1.0, 1.0), ("A", days[1], 1.0, 1.0), ("A", days[2], 1.0, 100.0)]
    rows += [("B", days[0], 1.0, 5.0), ("B", days[1], 1.0, 5.0), ("B", days[2], 1.0, 1.0)]
    got = membership.universe(frame(rows), days)
    assert got.rows() == [("B", days[2])]


def test_the_universe_starts_after_a_full_window(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 5, 3, 3)
    days = sessions(4)
    got = membership.universe(frame(steady("A", days, 5.0)), days)
    assert got["date"].to_list() == days[2:]


def test_the_real_window_is_63_sessions() -> None:
    days = sessions(70)
    got = membership.universe(frame(steady("A", days, 5.0)), days)
    assert got["date"].min() == days[62]
    assert got.height == 8
    assert got.schema == {"ticker": pl.String, "date": pl.Date}


def test_the_medians_come_back_by_ticker_then_date_whatever_the_input_order(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 10, 2, 2)
    days = sessions(3)
    rows = steady("B", days, 2.0) + steady("A", days, 1.0)
    rows = [rows[5], rows[2], rows[0], rows[4], rows[1], rows[3]]
    got = membership.median_dollar_volume(frame(rows), days)
    assert got.select("ticker", "date").rows() == [("A", days[1]), ("A", days[2]), ("B", days[1]), ("B", days[2])]
    assert got["median_dv"].to_list() == [1.0, 1.0, 2.0, 2.0]


def test_dates_that_are_no_session_leave_nothing_and_no_error(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 10, 2, 2)
    got = membership.median_dollar_volume(frame(steady("A", sessions(3), 1.0)), [date(2000, 1, 3)])
    assert got.rows() == []
    assert got.columns == ["ticker", "date", "median_dv"]


def test_a_null_in_another_column_does_not_remove_a_row(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 10, 2, 2)
    days = sessions(3)
    prices = frame(steady("A", days, 4.0)).with_columns(open=pl.Series([1.0, 1.0, None], dtype=pl.Float64))
    got = membership.median_dollar_volume(prices, days)
    assert got.sort("date").rows() == [("A", days[1], 4.0), ("A", days[2], 4.0)]


def test_the_size_is_kept_per_date_not_over_all_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    small(monkeypatch, 1, 2, 2)
    days = sessions(4)
    rows = steady("A", days[:3], 9.0) + steady("A", days[3:], 0.5) + steady("B", days, 5.0)
    got = membership.universe(frame(rows), days)
    assert got.rows() == [("A", days[1]), ("A", days[2]), ("B", days[3])]
