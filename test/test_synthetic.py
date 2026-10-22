"""The synthetic market (HAR-10, TODO 1.1): deterministic, shaped as the harness expects, and its edge recoverable."""
import math
from datetime import date

import numpy as np
import polars as pl

from neonrain.harness import synthetic
from neonrain.harness.synthetic import MarketConfig

SMALL = MarketConfig(tickers=4, days=6, idio_vol=0.05, seed=7)


def next_day_pairs(market: synthetic.Market) -> tuple[np.ndarray, np.ndarray]:
    """Each (edge at t, next day's log return in excess of that day's cross-sectional mean), over all t."""
    frame = market.prices.join(market.features, on=["ticker", "date"], validate="1:1").sort("ticker", "date")
    frame = frame.with_columns(pl.col("close").log().diff().over("ticker").shift(-1).over("ticker").alias("ahead"))
    frame = frame.drop_nulls("ahead").with_columns((pl.col("ahead") - pl.col("ahead").mean().over("date")).alias("excess"))
    return frame["edge"].to_numpy(), frame["excess"].to_numpy()


def recovered(config: MarketConfig) -> float:
    """The correlation a least-squares line through (edge, excess next-day return) recovers."""
    x, y = next_day_pairs(synthetic.generate(config))
    slope, _ = np.linalg.lstsq(np.column_stack([x, np.ones_like(x)]), y, rcond=None)[0]
    return float(slope * x.std() / y.std())


def test_the_same_config_gives_the_same_market_byte_for_byte() -> None:
    first, second = synthetic.generate(SMALL), synthetic.generate(SMALL)
    assert first.prices.equals(second.prices) and first.features.equals(second.features)
    assert first.universe.equals(second.universe) and first.calendar == synthetic.calendar(6)


def test_another_seed_gives_another_market() -> None:
    other = synthetic.generate(SMALL._replace(seed=8))
    assert not other.prices.equals(synthetic.generate(SMALL).prices)


def test_the_frames_have_the_harness_shape() -> None:
    market = synthetic.generate(SMALL)
    assert market.prices.columns == ["ticker", "date", "close"]
    assert market.universe.columns == ["ticker", "date"]
    assert market.features.columns == ["ticker", "date", "edge", "edge_stamp"]
    assert market.prices.height == market.universe.height == market.features.height == 24
    assert market.prices["ticker"].unique().sort().to_list() == ["T000", "T001", "T002", "T003"]
    assert market.prices.filter(pl.col("date") == date(2000, 1, 3))["close"].to_list() == [100.0] * 4


def test_the_calendar_is_weekdays_from_the_start() -> None:
    assert synthetic.calendar(6) == [date(2000, 1, d) for d in (3, 4, 5, 6, 7, 10)]


def test_every_edge_is_stamped_with_its_own_date() -> None:
    features = synthetic.generate(SMALL).features
    assert (features["edge_stamp"] == features["date"]).all()


def test_by_hand_with_rho_one_each_return_is_the_previous_edge_times_the_volatility() -> None:
    # R-015(d): no market, ρ = 1, so log(P[t+1] / P[t]) = σ_x · edge[t] exactly, row by row.
    config = MarketConfig(tickers=2, days=5, rho=1.0, market_drift=0.0, market_vol=0.0, idio_vol=0.1, seed=3)
    market = synthetic.generate(config)
    for ticker in ("T000", "T001"):
        closes = market.prices.filter(pl.col("ticker") == ticker)["close"].to_numpy()
        edges = market.features.filter(pl.col("ticker") == ticker)["edge"].to_numpy()
        assert np.allclose(np.diff(np.log(closes)), 0.1 * edges[:-1], rtol=0, atol=1e-12)


def test_the_market_factor_moves_every_ticker_alike() -> None:
    # No idiosyncratic part: every ticker's path is the same drift plus market.
    config = MarketConfig(tickers=3, days=5, idio_vol=0.0, market_drift=0.001, market_vol=0.02, seed=1)
    wide = synthetic.generate(config).prices.pivot(on="ticker", index="date", values="close")
    assert np.allclose(wide["T000"], wide["T001"]) and np.allclose(wide["T000"], wide["T002"])
    assert not np.allclose(wide["T000"], 100.0)


def test_the_volatilities_and_drift_are_as_configured() -> None:
    config = MarketConfig(tickers=300, days=400, rho=0.0, market_drift=0.001, market_vol=0.01, idio_vol=0.03, seed=5)
    _, returns = synthetic.log_returns(config)
    days = returns[1:]
    assert math.isclose(days.mean(axis=1).std(), 0.01, rel_tol=0.1)
    assert math.isclose((days - days.mean(axis=1, keepdims=True)).std(), 0.03, rel_tol=0.02)
    assert math.isclose(days.mean(), 0.001, abs_tol=0.0015)


def test_the_planted_edge_is_recovered_by_a_linear_model() -> None:
    # TODO 1.1's check: about 99,800 pairs, so the standard error is about 0.003; 0.015 is five of them.
    assert abs(recovered(MarketConfig(rho=0.1, seed=11)) - 0.1) < 0.015
    assert abs(recovered(MarketConfig(rho=0.3, seed=12)) - 0.3) < 0.015


def test_with_no_edge_nothing_is_recovered() -> None:
    assert abs(recovered(MarketConfig(rho=0.0, seed=13))) < 0.015


def test_delisting_ends_a_ticker_at_its_first_close_under_the_line() -> None:
    market = synthetic.generate(MarketConfig(tickers=50, days=300, idio_vol=0.04, delist_below=0.6, seed=2))
    last = market.prices.group_by("ticker").agg(pl.col("close").last(), pl.col("close").min().alias("low"), pl.len())
    delisted = last.filter(pl.col("len") < 300)
    assert delisted.height > 0
    assert (delisted["close"] < 60).all() and (delisted["close"] == delisted["low"]).all()
    survivors = last.filter(pl.col("len") == 300)
    assert (survivors["low"] >= 60).all()
    assert market.universe.height == market.prices.height == market.features.height


def test_last_days_by_hand() -> None:
    closes = np.array([[100.0, 100.0], [40.0, 90.0], [20.0, 80.0]])
    assert synthetic.last_days(closes, 0.5).tolist() == [1, 2]
    assert synthetic.last_days(closes, None).tolist() == [2, 2]
    assert synthetic.last_days(closes, 0.3).tolist() == [2, 2]
    assert synthetic.last_days(np.array([[100.0], [50.0], [49.0]]), 0.5).tolist() == [2]  # on the line is not under


def test_tickers_are_named_in_order() -> None:
    assert synthetic.tickers(3) == ["T000", "T001", "T002"]


def test_one_return_rebuilt_from_harness_md_alone() -> None:
    # HAR-10, independently: one generator, drawn market, edge, noise; then the formula for row t+1.
    config = MarketConfig(tickers=3, days=4, rho=0.4, market_drift=0.002, market_vol=0.01, idio_vol=0.03, seed=9)
    rng = np.random.default_rng(9)
    market, edge, noise = rng.standard_normal(4), rng.standard_normal((4, 3)), rng.standard_normal((4, 3))
    t, i = 1, 2
    expected = 0.002 + 0.01 * market[t + 1] + 0.03 * (0.4 * edge[t, i] + math.sqrt(1 - 0.4**2) * noise[t + 1, i])
    edges, returns = synthetic.log_returns(config)
    assert math.isclose(returns[t + 1, i], expected, rel_tol=0, abs_tol=1e-15)
    assert np.array_equal(edges, edge)


def test_an_empty_market_keeps_its_column_types() -> None:
    market = synthetic.generate(MarketConfig(tickers=0, days=3))
    assert market.prices.schema == {"ticker": pl.String, "date": pl.Date, "close": pl.Float64}
    assert market.prices.height == 0 and len(market.calendar) == 3
