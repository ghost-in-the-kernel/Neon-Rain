"""HAR-07's long–short decile portfolio after HAR-06's costs (R-021), by hand (R-015d), then on the synthetic market.

The hand market: 20 tickers T00..T19 over 6 days, scored by their number, so with n = ⌊20/10⌋ = 2 per leg
the long leg is T18, T19 and the short leg T00, T01. Their closes:

    T18, T19   100  101  102.01  103.0301 …   (+1% a day)
    T00, T01   100   99   98.01   97.0299 …   (−1% a day)
    the rest   100  100  100     100     …

So a sleeve earns 0.01 − (−0.01) = 0.02 a day before costs. At 10 bps (0.001) it pays 2 × 0.001 to open (both
legs at gross 1) and 2 × 0.001 to close; every amount enters the day at the sleeve's 1/h share.
"""
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from neonrain import targets
from neonrain.harness import portfolio, synthetic

DAYS = [date(2000, 1, 3) + timedelta(days=d) for d in range(6)]
NAMES = [f"T{i:02d}" for i in range(20)]


def closes(name: str, day: int) -> float:
    if name in ("T18", "T19"):
        return 100.0 * 1.01**day
    if name in ("T00", "T01"):
        return 100.0 * 0.99**day
    return 100.0


def prices(missing: tuple[tuple[str, int], ...] = ()) -> pl.DataFrame:
    rows = [(n, DAYS[d], closes(n, d)) for n in NAMES for d in range(6) if (n, d) not in missing]
    return pl.DataFrame(rows, schema={"ticker": pl.String, "date": pl.Date, "close": pl.Float64}, orient="row")


def scored(days: tuple[int, ...], names: list[str] = NAMES, same: bool = False) -> pl.DataFrame:
    rows = [(n, DAYS[d], 0.0 if same else float(i)) for d in days for i, n in enumerate(names)]
    return pl.DataFrame(rows, schema={"ticker": pl.String, "date": pl.Date, "score": pl.Float64}, orient="row")


def table(frame: pl.DataFrame) -> list[tuple[float, float, float]]:
    return [(round(g, 12), round(c, 12), round(n, 12)) for g, c, n in frame.select("gross", "cost", "net").iter_rows()]


def test_one_sleeve_by_hand() -> None:
    # h = 2, one test date. Day 0: opens, pays 0.002 × ½. Days 1, 2: earns 0.02 × ½. Day 2: closes, pays 0.002 × ½.
    found = portfolio.daily(scored((0,)), prices(), DAYS, 2, 10.0)
    assert found["date"].to_list() == DAYS[:3]
    assert table(found) == [(0.0, 0.001, -0.001), (0.01, 0.0, 0.01), (0.01, 0.001, 0.009)]


def test_overlapping_sleeves_by_hand() -> None:
    # Sleeves opened on days 0 and 1 (h = 2): day 1 has A earning and B opening; day 2 both earn and A closes.
    found = portfolio.daily(scored((0, 1)), prices(), DAYS, 2, 10.0)
    assert table(found) == [(0.0, 0.001, -0.001), (0.01, 0.001, 0.009), (0.02, 0.001, 0.019), (0.01, 0.001, 0.009)]


def test_a_delisted_name_is_closed_at_its_last_price_and_its_slot_earns_nothing() -> None:
    # T19 has no price from day 2. Day 1: T19 earns 0.01, then closes, paying 0.001 / 2 (its 1/n), × ½.
    # Day 2: long leg (0 + 0.01) / 2 = 0.005, short −0.01, sleeve 0.015, × ½; the rest close: 0.0015 × ½.
    found = portfolio.daily(scored((0,)), prices((("T19", 2), ("T19", 3), ("T19", 4), ("T19", 5))), DAYS, 2, 10.0)
    assert table(found) == [(0.0, 0.001, -0.001), (0.01, 0.00025, 0.00975), (0.0075, 0.00075, 0.00675)]


def test_ties_are_broken_by_ticker_whatever_order_the_rows_come_in() -> None:
    # Every score equal: ascending by (score, ticker) puts T00, T01 first (short) and T18, T19 last (long).
    expected = table(portfolio.daily(scored((0,)), prices(), DAYS, 2, 0.0))
    assert table(portfolio.daily(scored((0,), same=True), prices(), DAYS, 2, 0.0)) == expected
    assert table(portfolio.daily(scored((0,), same=True).reverse(), prices(), DAYS, 2, 0.0)) == expected


def test_legs_by_hand() -> None:
    column = {n: j for j, n in enumerate(NAMES)}
    assert portfolio.legs([(n, float(i)) for i, n in enumerate(NAMES)], column) == ([0, 1], [18, 19])
    assert portfolio.legs([(n, float(i)) for i, n in enumerate(NAMES[:9])], column) == ([], [])
    assert portfolio.legs([(n, -float(i)) for i, n in enumerate(NAMES[:19])], column) == ([18], [0])


def test_too_few_names_open_no_sleeve() -> None:
    # The series still covers the test date and the h after it, as cash.
    found = portfolio.daily(scored((0,), names=NAMES[:9]), prices(), DAYS, 2, 10.0)
    assert table(found) == [(0.0, 0.0, 0.0)] * 3


def test_a_name_without_a_price_on_the_day_is_not_tested() -> None:
    # T19 has no price on day 0: 19 priced names, n = 1, so the legs are T00 and T18.
    found = portfolio.daily(scored((0,)), prices((("T19", 0),)), DAYS, 1, 0.0)
    assert table(found) == [(0.0, 0.0, 0.0), (0.02, 0.0, 0.02)]


def test_a_sleeve_still_open_at_the_calendar_s_end_closes_there() -> None:
    # h = 5 from day 3: days 4 and 5 exist, so it earns twice and closes on day 5 (the last).
    found = portfolio.daily(scored((3,)), prices(), DAYS, 5, 10.0)
    assert found["date"].to_list() == DAYS[3:]
    assert table(found) == [(0.0, 0.0004, -0.0004), (0.004, 0.0, 0.004), (0.004, 0.0004, 0.0036)]


def test_nothing_scored_is_an_empty_series() -> None:
    found = portfolio.daily(scored(()), prices(), DAYS, 2, 10.0)
    assert found.height == 0
    assert found.schema == {"date": pl.Date, "gross": pl.Float64, "cost": pl.Float64, "net": pl.Float64}


def test_the_cost_levels() -> None:
    assert portfolio.COST_LEVELS_BPS == (0.0, 10.0, 25.0) and portfolio.DEFAULT_COST_BPS == 10.0
    at = {c: portfolio.daily(scored((0,)), prices(), DAYS, 2, c)["cost"].sum() for c in portfolio.COST_LEVELS_BPS}
    assert at == pytest.approx({0.0: 0.0, 10.0: 0.002, 25.0: 0.005})


def test_on_the_synthetic_market_the_steady_cost_is_four_c_over_h_and_the_edge_pays() -> None:
    # R-021: each day one sleeve opens (2c) and one closes (2c), each at 1/h: 4c/h, exactly, with no delistings.
    market = synthetic.generate(synthetic.MarketConfig(tickers=100, days=160, rho=0.3, seed=8))
    horizon = 5
    test_dates = market.calendar[20:140]
    rows = market.features.filter(pl.col("date").is_in(test_dates)).select("ticker", "date", pl.col("edge").alias("score"))
    found = portfolio.daily(rows, market.prices, market.calendar, horizon, 10.0)
    steady = found["cost"].to_numpy()[horizon:120]
    assert np.allclose(steady, 4 * 0.001 / horizon, rtol=0, atol=1e-15)
    assert found["gross"].mean() > 0.002  # the planted edge, before costs
    noise = rows.with_columns(pl.col("score").shuffle(seed=1).over("date"))
    assert abs(portfolio.daily(noise, market.prices, market.calendar, horizon, 0.0)["gross"].mean()) < 0.001


def test_one_sleeve_roughly_agrees_with_the_targets_forward_returns() -> None:
    # One sleeve, h = 3, no cost: its summed daily means are close to, not equal to, the top decile's mean 3-day
    # forward return (targets.labels) less the bottom's, since daily means and 3-day returns compound differently.
    market = synthetic.generate(synthetic.MarketConfig(tickers=100, days=30, rho=0.5, seed=9))
    first = market.calendar[5]
    rows = market.features.filter(pl.col("date") == first).select("ticker", "date", pl.col("edge").alias("score"))
    gross = portfolio.daily(rows, market.prices, market.calendar, 3, 0.0)["gross"].sum() * 3
    forward = targets.labels(market.prices, market.universe, market.calendar, 3).frame.filter(pl.col("date") == first)
    ranked = forward.join(rows, on=["ticker", "date"]).sort("score", "ticker")["forward"].to_numpy()
    spread = ranked[-10:].mean() - ranked[:10].mean()
    assert np.sign(gross) == np.sign(spread) and abs(gross - spread) < 0.25 * abs(spread)


def test_a_thin_date_does_not_stop_the_later_ones() -> None:
    # Day 0 has nine names (no sleeve); day 1 has all twenty. The series starts at day 0 as cash.
    rows = pl.concat([scored((0,), names=NAMES[:9]), scored((1,))])
    found = portfolio.daily(rows, prices(), DAYS, 1, 0.0)
    assert table(found) == [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.02, 0.0, 0.02)]


def test_a_whole_leg_delisted_earns_nothing_after_it_goes() -> None:
    # T18 and T19 have no price from day 2: the long leg earns 0.01 on day 1 and nothing on day 2; the short
    # leg still earns −0.01, so the sleeve makes 0.02 then 0.01 (× ½), and the long leg's close is paid on day 1.
    gone = tuple((n, d) for n in ("T18", "T19") for d in range(2, 6))
    found = portfolio.daily(scored((0,)), prices(gone), DAYS, 2, 10.0)
    assert table(found) == [(0.0, 0.001, -0.001), (0.01, 0.0005, 0.0095), (0.005, 0.0005, 0.0045)]


def test_the_same_scores_give_the_same_bits_in_any_row_order() -> None:
    market = synthetic.generate(synthetic.MarketConfig(tickers=60, days=60, rho=0.2, seed=10))
    rows = market.features.filter(pl.col("date") < market.calendar[40]).select("ticker", "date", pl.col("edge").alias("score"))
    first = portfolio.daily(rows, market.prices, market.calendar, 5, 10.0)
    assert first.equals(portfolio.daily(rows.reverse(), market.prices, market.calendar, 5, 10.0))
    assert first.equals(portfolio.daily(rows.sample(fraction=1.0, shuffle=True, seed=3), market.prices, market.calendar, 5, 10.0))


def test_a_name_gone_the_day_after_it_is_bought_closes_on_the_opening_day() -> None:
    # T19 has no price from day 1: it closes on day 0 at its entry price, paying 0.001 / 2 on top of the
    # 0.002 opening, × ½; the long leg is T18 alone earning 0.01 / 2 on days 1 and 2.
    gone = tuple(("T19", d) for d in range(1, 6))
    found = portfolio.daily(scored((0,)), prices(gone), DAYS, 2, 10.0)
    assert table(found) == [(0.0, 0.00125, -0.00125), (0.0075, 0.0, 0.0075), (0.0075, 0.00075, 0.00675)]
