"""TODO 1.4's check (HAR-10, HAR-07): a strategy with no edge, after costs, reports a deflated Sharpe inside its
noise band across 100 seeds. Slow (about 45 s): outside the fast loop, run by scripts/precommit.sh on its own.

With no edge and one trial, the DSR is the probabilistic Sharpe ratio, which is uniform on [0, 1] when the
truth is zero: about 5 seeds in 100 reach 0.95 by chance. The band: at most 12 (the binomial(100, 0.05)
chance of 13 or more is under 0.2%), and a mean within 0.4 to 0.6. Costs can only push it down.
"""
from functools import cache

import numpy as np
import polars as pl
import pytest

from neonrain.harness import metrics, portfolio, synthetic
from neonrain.harness.market import Market

SEEDS = range(100)


@cache
def market_of(seed: int) -> Market:
    """A seed's market, built once for the two cost levels (generate is a pure function of its config; R-024 c)."""
    return synthetic.generate(synthetic.MarketConfig(tickers=100, days=300, rho=0.0, seed=seed))


def zero_edge_dsr(seed: int, cost_bps: float) -> float:
    """The DSR (one trial) of the long–short portfolio on an edge of ρ = 0, held 5 days, on 227 test dates."""
    market = market_of(seed)
    dates = pl.col("date")
    rows = market.features.filter((dates >= market.calendar[63]) & (dates < market.calendar[290]))
    scores = rows.select("ticker", "date", pl.col("edge").alias("score"))
    daily = portfolio.daily(scores, market.prices, market.calendar, 5, cost_bps)["net"].to_numpy()
    found = metrics.deflated_sharpe(daily, 1, None)
    assert found is not None
    return found


@pytest.mark.slow
def test_a_zero_edge_strategy_stays_inside_its_noise_band() -> None:
    free = np.array([zero_edge_dsr(seed, 0.0) for seed in SEEDS])
    costly = np.array([zero_edge_dsr(seed, portfolio.DEFAULT_COST_BPS) for seed in SEEDS])
    assert (free >= 0.95).sum() <= 12 and 0.4 <= free.mean() <= 0.6
    assert (costly >= 0.95).sum() <= (free >= 0.95).sum() and costly.mean() < free.mean()
    assert (costly <= free).all()
