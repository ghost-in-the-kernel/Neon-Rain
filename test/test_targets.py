"""HAR-02's labels on a hand-built ten-day, three-ticker series (TODO 1.2, R-015d), then on the synthetic market.

The series, every number checkable in a spreadsheet:

    day      0    1    2    3    4    5    6    7    8    9
    A      100  110  120  130  140  150  160  170  180  190
    B      100  100  100  100  100  100  100  100  100  100   (not eligible on day 2)
    C      100   90   80   70   60   50   40   30    —   10   (no price on day 8)
"""
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from neonrain import targets
from neonrain.harness import synthetic

DAYS = [date(2000, 1, 3) + timedelta(days=d) for d in range(10)]  # any ten ordered dates will do
CLOSES = {"A": [100.0 + 10 * d for d in range(10)], "B": [100.0] * 10, "C": [100.0 - 10 * d for d in range(10)]}


def series() -> tuple[pl.DataFrame, pl.DataFrame]:
    """The prices and universe frames of the table above."""
    rows = [(t, DAYS[d], c) for t, closes in CLOSES.items() for d, c in enumerate(closes) if (t, d) != ("C", 8)]
    prices = pl.DataFrame(rows, schema={"ticker": pl.String, "date": pl.Date, "close": pl.Float64}, orient="row")
    eligible = [(t, DAYS[d]) for t in CLOSES for d in range(10) if (t, d) != ("B", 2)]
    return prices, pl.DataFrame(eligible, schema={"ticker": pl.String, "date": pl.Date}, orient="row")


def hand(horizon: int, min_tickers: int = 2) -> targets.Labels:
    prices, universe = series()
    return targets.labels(prices, universe, DAYS, horizon, min_tickers)


def row(found: targets.Labels, ticker: str, day: int) -> dict:
    """One label row as a dict; fails if it is not there."""
    match = found.frame.filter((pl.col("ticker") == ticker) & (pl.col("date") == DAYS[day]))
    assert match.height == 1, f"{ticker} on day {day}: {match.height} rows"
    return match.row(0, named=True)


def test_day_0_by_hand() -> None:
    # A: 130/100 − 1 = 0.3; B: 0; C: 70/100 − 1 = −0.3. Median 0 is B's own return: B ties.
    found = hand(3)
    assert row(found, "A", 0) | {} == {"ticker": "A", "date": DAYS[0], "horizon": 3, "forward": pytest.approx(0.3),
                                       "excess": pytest.approx(0.3), "direction": 1, "rank": 1.0}
    assert row(found, "B", 0)["direction"] is None and row(found, "B", 0)["rank"] == 0.5
    assert row(found, "C", 0)["excess"] == pytest.approx(-0.3)
    assert (row(found, "C", 0)["direction"], row(found, "C", 0)["rank"]) == (0, 0.0)


def test_day_2_without_b_the_median_is_the_mean_of_two() -> None:
    # A: 150/120 − 1 = 0.25; C: 50/80 − 1 = −0.375; median −0.0625; excess ±0.3125; B has no cell.
    found = hand(3)
    assert row(found, "A", 2)["excess"] == pytest.approx(0.3125) and row(found, "A", 2)["rank"] == 1.0
    assert row(found, "C", 2)["excess"] == pytest.approx(-0.3125) and row(found, "C", 2)["rank"] == 0.0
    assert found.frame.filter((pl.col("ticker") == "B") & (pl.col("date") == DAYS[2])).height == 0


def test_day_5_c_has_no_price_three_days_on_so_its_cell_is_dropped_as_missing() -> None:
    # A: 180/150 − 1 = 0.2; B: 0; median 0.1; excess A 0.1, B −0.1. C's day 8 is missing.
    found = hand(3)
    assert row(found, "A", 5)["excess"] == pytest.approx(0.1) and row(found, "B", 5)["excess"] == pytest.approx(-0.1)
    assert row(found, "B", 5)["direction"] == 0
    assert found.dropped_missing == 1


def test_the_counts_by_hand() -> None:
    # Cells: days 0–6 (the last 3 days have no day+3): 3 + 3 + 2 + 3 + 3 + 3 + 3 = 20; one missing.
    # Ties: B is the median on days 0, 1, 3, 4, 6 (with three tickers, the middle one) = 5.
    found = hand(3)
    assert (found.frame.height, found.dropped_missing, found.dropped_ties, found.dropped_thin_dates) == (19, 1, 5, 0)


def test_dates_with_too_few_tickers_are_dropped_and_counted() -> None:
    # min_tickers 3: days 2 and 5 have two priced, eligible tickers.
    found = hand(3, min_tickers=3)
    assert found.dropped_thin_dates == 2 and found.dropped_missing == 1
    assert sorted(set(found.frame["date"].to_list())) == [DAYS[d] for d in (0, 1, 3, 4, 6)]


def test_horizon_five_by_hand() -> None:
    # Day 4: A 190/140 − 1, B 0, C 10/60 − 1 (day 9). Days 0–4 make cells; C's day 3 needs day 8: missing.
    found = hand(5)
    assert row(found, "A", 4)["forward"] == pytest.approx(190 / 140 - 1)
    assert row(found, "C", 4)["forward"] == pytest.approx(10 / 60 - 1)
    assert found.dropped_missing == 1 and found.frame["date"].max() == DAYS[4]


def test_the_last_horizon_days_make_no_cells_and_are_not_counted() -> None:
    # Horizon 9: only day 0 has a day+9, and all three have a price on day 9 (C's gap is day 8).
    found = hand(9)
    assert found.frame["date"].to_list() == [DAYS[0]] * 3 and found.dropped_missing == 0
    assert row(found, "C", 0)["forward"] == pytest.approx(10 / 100 - 1)


def test_a_horizon_longer_than_the_calendar_makes_nothing() -> None:
    found = hand(10)
    assert (found.frame.height, found.dropped_missing, found.dropped_ties, found.dropped_thin_dates) == (0, 0, 0, 0)


def test_one_ticker_cannot_be_ranked() -> None:
    with pytest.raises(ValueError, match="at least two"):
        hand(3, min_tickers=1)


def test_ties_in_rank_take_the_average() -> None:
    prices, universe = series()
    flat = prices.with_columns(pl.when(pl.col("ticker") == "C").then(100.0).otherwise(pl.col("close")).alias("close"))
    found = targets.labels(flat, universe, DAYS, 3, 2)
    assert row(found, "B", 0)["rank"] == 0.25 and row(found, "C", 0)["rank"] == 0.25 and row(found, "A", 0)["rank"] == 1.0


def test_on_the_synthetic_market_every_label_is_well_formed() -> None:
    market = synthetic.generate(synthetic.MarketConfig(tickers=41, days=120, seed=4))
    for horizon in targets.HORIZONS:
        found = targets.labels(market.prices, market.universe, market.calendar, horizon)
        frame = found.frame
        assert frame.height == 41 * (120 - horizon)
        assert frame["rank"].min() == 0.0 and frame["rank"].max() == 1.0
        per_date = frame.group_by("date").agg(pl.col("direction").sum(), pl.col("excess").median())
        assert (per_date["direction"] == 20).all() and np.allclose(per_date["excess"], 0.0)
        assert found.dropped_ties == 120 - horizon  # 41 tickers: the median ticker ties every date


def test_the_edge_shows_in_the_labels_and_thins_with_the_horizon() -> None:
    # HAR-10: ρ against the next day; about ρ/√h against an h-day window. Rank correlation with the edge:
    market = synthetic.generate(synthetic.MarketConfig(tickers=200, days=400, rho=0.3, seed=6))
    found = {}
    for horizon in (3, 21):
        frame = targets.labels(market.prices, market.universe, market.calendar, horizon).frame
        joined = frame.join(market.features, on=["ticker", "date"], validate="1:1")
        found[horizon] = np.corrcoef(joined["edge"], joined["rank"])[0, 1]
    assert 0.3 / np.sqrt(3) * 0.8 < found[3] < 0.3 / np.sqrt(3) * 1.2
    assert 0.3 / np.sqrt(21) * 0.7 < found[21] < 0.3 / np.sqrt(21) * 1.3


def test_a_delisted_name_s_windows_are_dropped_as_missing() -> None:
    # NR-F-02, held as it stands: the names that fall to delisting lose the windows that cross it.
    market = synthetic.generate(synthetic.MarketConfig(tickers=60, days=250, idio_vol=0.04, delist_below=0.6, seed=2))
    found = targets.labels(market.prices, market.universe, market.calendar, 21)
    delisted = market.prices.group_by("ticker").len().filter(pl.col("len") < 250).height
    assert delisted > 0 and found.dropped_missing == 21 * delisted


def test_labels_are_sorted_by_date_then_ticker_whatever_order_they_came_in() -> None:
    prices, universe = series()
    found = targets.labels(prices.reverse(), universe.reverse(), DAYS, 3, 2).frame
    assert found["ticker"].to_list()[:6] == ["A", "B", "C", "A", "B", "C"]
    assert found["date"].to_list()[:4] == [DAYS[0]] * 3 + [DAYS[1]]


def test_unusable_inputs_are_refused_with_every_reason() -> None:
    prices, universe = series()
    with pytest.raises(ValueError, match="prices has a .ticker, date. twice"):
        targets.labels(pl.concat([prices, prices.head(1)]), universe, DAYS, 3, 2)
    with pytest.raises(ValueError, match="universe has a .ticker, date. twice"):
        targets.labels(prices, pl.concat([universe, universe.tail(1)]), DAYS, 3, 2)
    with pytest.raises(ValueError, match="not strictly increasing"):
        targets.labels(prices, universe, DAYS[:5] + DAYS[4:], 3, 2)
    assert targets.input_problems(prices.head(0), universe.head(0), DAYS[:5] + DAYS[4:] + [DAYS[0]]) == [
        "the calendar is not strictly increasing"
    ]
    with pytest.raises(ValueError, match="twice; .*twice; .*calendar.*; min_tickers is 1"):
        targets.labels(pl.concat([prices, prices]), pl.concat([universe, universe]), DAYS[::-1], 3, 1)


def test_an_eligible_ticker_with_no_price_on_the_day_itself_is_counted_missing() -> None:
    # Remove A's day-1 close: A's day-1 cell has no price at t (missing), on top of C's day 5.
    prices, universe = series()
    gap = prices.filter(~((pl.col("ticker") == "A") & (pl.col("date") == DAYS[1])))
    found = targets.labels(gap, universe, DAYS, 3, 2)
    assert found.dropped_missing == 2 and found.frame.height == 18
