"""The synthetic market (HAR-10): seeded fake prices with an edge of known strength planted in them.

Everything in phase 1 is tested here first, because it is the only market where the right answer is known.
Deterministic (HAR-11): one generator, seeded from the config, drawn in a fixed order; no clock, no network.
"""
import math
from datetime import date, timedelta
from typing import NamedTuple

import numpy as np
import polars as pl

from neonrain.harness.market import Market

START = date(2000, 1, 3)
START_PRICE = 100.0


class MarketConfig(NamedTuple):
    """The market's parameters; every one is part of the run's config (HAR-01)."""

    tickers: int = 200
    days: int = 500
    rho: float = 0.05  # correlation of the edge with the next day's idiosyncratic return
    market_drift: float = 0.0003  # μ, per day, in log return
    market_vol: float = 0.01  # σ_m, per day
    idio_vol: float = 0.02  # σ_x, per day
    delist_below: float | None = None  # a fraction of the start price; None keeps every ticker
    seed: int = 0


def calendar(days: int) -> list[date]:
    """The first `days` weekdays from 2000-01-03: calendar(3) is [2000-01-03, 2000-01-04, 2000-01-05]."""
    found: list[date] = []
    day = START
    while len(found) < days:
        if day.weekday() < 5:
            found.append(day)
        day += timedelta(days=1)
    return found


def tickers(count: int) -> list[str]:
    """Names in order: tickers(3) is ["T000", "T001", "T002"]."""
    return [f"T{i:03d}" for i in range(count)]


# HAR-10's model, drawn in HAR-11's fixed order: market, edge, noise.
def log_returns(config: MarketConfig) -> tuple[np.ndarray, np.ndarray]:
    """The edge (days × tickers) and each day's log return; row 0 of the returns is 0, the start.

    Row t+1 of the returns is μ + σ_m·m + σ_x·(ρ·edge[t] + √(1−ρ²)·z), so with ρ = 1 and no market
    each return is exactly σ_x times the previous day's edge.
    """
    rng = np.random.default_rng(config.seed)
    market = rng.standard_normal(config.days)
    edge = rng.standard_normal((config.days, config.tickers))
    noise = rng.standard_normal((config.days, config.tickers))
    idio = config.rho * edge[:-1] + math.sqrt(1.0 - config.rho**2) * noise[1:]
    returns = np.zeros((config.days, config.tickers))
    returns[1:] = config.market_drift + config.market_vol * market[1:, None] + config.idio_vol * idio
    return edge, returns


def last_days(closes: np.ndarray, delist_below: float | None) -> np.ndarray:
    """Each ticker's last row: the first close under delist_below × 100, else the final day.

    For closes [[100, 100], [40, 90], [20, 80]] and 0.5: [1, 2] (the first falls under 50 on day 1).
    """
    days = closes.shape[0]
    if delist_below is None:
        return np.full(closes.shape[1], days - 1)
    under = closes < delist_below * START_PRICE
    return np.where(under.any(axis=0), under.argmax(axis=0), days - 1)


def generate(config: MarketConfig) -> Market:
    """The market for a config: the same config gives the same frames, byte for byte (HAR-11)."""
    edge, returns = log_returns(config)
    closes = START_PRICE * np.exp(np.cumsum(returns, axis=0))
    last = last_days(closes, config.delist_below)
    dates = calendar(config.days)
    names = tickers(config.tickers)
    alive = np.arange(config.days)[:, None] <= last[None, :]
    rows = np.nonzero(alive)
    columns = {
        "ticker": [names[i] for i in rows[1]],
        "date": [dates[t] for t in rows[0]],
    }
    keys = pl.DataFrame(columns, schema={"ticker": pl.String, "date": pl.Date})
    prices = keys.with_columns(pl.Series("close", closes[rows]))
    # HAR-12: the edge at t is known at the close of t, so its stamp is t itself.
    features = keys.with_columns(pl.Series("edge", edge[rows]), pl.col("date").alias("edge_stamp"))
    order = ["ticker", "date"]
    return Market(prices.sort(order), keys.sort(order), features.sort(order), dates)
