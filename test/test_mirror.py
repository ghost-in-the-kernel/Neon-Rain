"""R-015(c): HAR-07's metrics against a mirror written blind from HAR-06 and HAR-07's text by another agent
(test/mirror_har07.py: standard library only, never shown neonrain/). They must agree on the synthetic market;
a disagreement means the code or the contract is wrong, never that the mirror is adjusted to match (J-018)."""
import math

import mirror_har07 as mirror
import numpy as np
import polars as pl
import pytest

from neonrain import targets
from neonrain.harness import metrics, portfolio, synthetic

CONFIG = synthetic.MarketConfig(tickers=60, days=160, rho=0.2, idio_vol=0.05, delist_below=0.85, seed=21)
HORIZON = 5


def market_and_labels() -> tuple[synthetic.Market, pl.DataFrame]:
    market = synthetic.generate(CONFIG)
    labels = targets.labels(market.prices, market.universe, market.calendar, HORIZON, min_tickers=10).frame
    scored = labels.join(market.features, on=["ticker", "date"]).with_columns(
        (1 / (1 + (-pl.col("edge")).exp())).alias("probability"))
    return market, scored.filter(pl.col("date") < market.calendar[120])


def held_delistings(market: synthetic.Market, scores: pl.DataFrame) -> int:
    """How many leg positions lose their price during their hold: the comparison must exercise HAR-07's delisting
    rule, not only have delistings somewhere in the market (J-018). Worked independently of portfolio.py."""
    index = {d: i for i, d in enumerate(market.calendar)}
    priced = set(market.prices.select("ticker", "date").iter_rows())
    count = 0
    for (day,), group in scores.group_by("date"):
        ranked = sorted((s, t) for t, s in group.select("ticker", "score").iter_rows() if (t, day) in priced)
        n = len(ranked) // 10
        last = min(index[day] + HORIZON, len(market.calendar) - 1)
        for _, ticker in ranked[:n] + ranked[len(ranked) - n:]:
            count += any((ticker, market.calendar[j]) not in priced for j in range(index[day] + 1, last + 1))
    return count


def tradable(market: synthetic.Market) -> pl.DataFrame:
    """The portfolio's scores: every universe row with a feature on the test dates, never only the labelled rows.
    A label needs a price at t+h, so scoring labelled rows alone would keep out every name about to delist:
    a choice on day t made with day t+h's knowledge (NR-F-02, J-018)."""
    rows = market.features.filter(pl.col("date") < market.calendar[120])
    return rows.join(market.universe, on=["ticker", "date"]).select("ticker", "date", pl.col("edge").alias("score"))


def close(ours: float | None, theirs: float | None) -> bool:
    return (ours is None and theirs is None) or (ours is not None and theirs is not None and math.isclose(ours, theirs, rel_tol=1e-9, abs_tol=1e-12))


def test_the_accuracies_agree() -> None:
    _, scored = market_and_labels()
    rows = list(scored.select("probability", "direction").iter_rows())
    frame = scored.select(pl.col("probability").alias("score"), "direction")
    assert close(metrics.accuracy(frame), mirror.accuracy(rows))
    assert close(metrics.balanced_accuracy(frame), mirror.balanced_accuracy(rows))


def test_the_information_coefficients_agree() -> None:
    _, scored = market_and_labels()
    ours = metrics.information_coefficient(scored.select("date", pl.col("edge").alias("score"), "rank"), min_tickers=10)
    theirs = mirror.information_coefficient(list(scored.select("date", "edge", "rank").iter_rows()), min_tickers=10)
    assert all(close(a, b) for a, b in zip(ours[:3], theirs[:3])) and tuple(ours[3:]) == tuple(theirs[3:])
    assert ours.dates > 50


@pytest.mark.parametrize("cost_bps", portfolio.COST_LEVELS_BPS)
def test_the_portfolios_agree_day_by_day_with_delistings(cost_bps: float) -> None:
    market, _ = market_and_labels()
    scores = tradable(market)
    ours = portfolio.daily(scores, market.prices, market.calendar, HORIZON, cost_bps)
    closes = {(t, d): c for t, d, c in market.prices.iter_rows()}
    theirs = mirror.portfolio_daily(list(scores.iter_rows()), closes, market.calendar, HORIZON, cost_bps)
    assert held_delistings(market, scores) >= 20  # HAR-07's delisting rule is exercised, not only present
    assert ours["date"].to_list() == [row[0] for row in theirs]
    for column, index in (("gross", 1), ("cost", 2), ("net", 3)):
        assert np.allclose(ours[column].to_numpy(), [row[index] for row in theirs], rtol=0, atol=1e-12), column


def test_the_sharpes_and_deflated_sharpes_agree() -> None:
    market, _ = market_and_labels()
    daily = portfolio.daily(tradable(market), market.prices, market.calendar, HORIZON, 10.0)["net"].to_numpy()
    assert close(metrics.sharpe(daily), mirror.sharpe(list(daily)))
    for trials, variance in ((1, None), (10, 0.0004), (200, 0.01)):
        assert close(metrics.deflated_sharpe(daily, trials, variance), mirror.deflated_sharpe(list(daily), trials, variance))


def test_the_undefined_cases_agree() -> None:
    assert metrics.sharpe(np.array([0.01])) is None and mirror.sharpe([0.01]) is None
    assert metrics.deflated_sharpe(np.array([0.0, 0.0]), 1, None) is None and mirror.deflated_sharpe([0.0, 0.0], 1, None) is None
    one_class = pl.DataFrame({"score": [0.9, 0.1], "direction": [1, 1]})
    assert metrics.balanced_accuracy(one_class) is None and mirror.balanced_accuracy([(0.9, 1), (0.1, 1)]) is None


def test_scoring_labelled_rows_only_would_hide_every_delisting() -> None:
    # The leak the line above guards against, shown: the labelled rows hold no name that delists in its hold.
    market, scored = market_and_labels()
    assert held_delistings(market, scored.select("ticker", "date", pl.col("edge").alias("score"))) == 0
    assert held_delistings(market, tradable(market)) >= 20
