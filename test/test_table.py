"""The feature table (TODO 2.5) on a tiny invented market: 25 tickers over 90 days, prices from a seeded generator.

No real price is in this file (R-006).
"""
import random
from datetime import date, timedelta

import polars as pl
import pytest

from neonrain.features import indicators, normalize, returns, table, volatility, volume
from neonrain.harness import market

DAYS = [date(2001, 1, 1) + timedelta(days=i) for i in range(90)]
TICKERS = [f"T{i:02d}" for i in range(25)]
LITERAL = [
    "ticker", "date",
    "ret_3", "ret_3_stamp", "ret_5", "ret_5_stamp", "ret_21", "ret_21_stamp", "ret_63", "ret_63_stamp",
    "vol_5", "vol_5_stamp", "vol_21", "vol_21_stamp", "vol_63", "vol_63_stamp",
    "volr_5", "volr_5_stamp", "volr_21", "volr_21_stamp", "volr_63", "volr_63_stamp",
    "rsi_14", "rsi_14_stamp", "macd", "macd_stamp", "macd_hist", "macd_hist_stamp",
    "mar_5", "mar_5_stamp", "mar_21", "mar_21_stamp", "mar_63", "mar_63_stamp",
]


def invented(seed: int = 1) -> pl.DataFrame:
    """Prices for every ticker on every day: a seeded random walk and a seeded volume."""
    rng = random.Random(seed)
    rows = []
    for ticker in TICKERS:
        close = 50.0
        for day in DAYS:
            close *= 1 + rng.uniform(-0.03, 0.03)
            rows.append((ticker, day, close, rng.uniform(1e3, 1e5)))
    return pl.DataFrame(rows, schema={"ticker": pl.String, "date": pl.Date, "close": pl.Float64, "volume": pl.Float64}, orient="row")


def everyone() -> pl.DataFrame:
    """A universe of every ticker on every day."""
    return pl.DataFrame([(t, d) for t in TICKERS for d in DAYS], schema=market.KEYS, orient="row")


def built(prices: pl.DataFrame, members: pl.DataFrame | None = None) -> pl.DataFrame:
    """The table of `prices` on the invented calendar."""
    return table.feature_table(prices, DAYS, everyone() if members is None else members)


def test_the_column_order_is_fixed() -> None:
    assert table.columns() == LITERAL
    assert built(invented()).columns == LITERAL


def test_columns_are_the_families_in_order() -> None:
    families = [returns, volatility, volume, indicators]
    assert table.columns() == ["ticker", "date", *(c for f in families for c in f.feature_columns())]


def test_one_row_per_universe_cell_sorted() -> None:
    members = everyone().filter(~((pl.col("ticker") == "T03") & (pl.col("date") < DAYS[10])))
    result = built(invented(), members)
    assert result.select("ticker", "date").equals(members.sort("ticker", "date"))


def test_types() -> None:
    schema = built(invented()).schema
    assert schema["ticker"] == pl.String and schema["date"] == pl.Date
    for name in LITERAL[2:]:
        assert schema[name] == (pl.Date if name.endswith("_stamp") else pl.Float64)


def test_the_table_passes_the_harness() -> None:
    result = built(invented())
    market.check_stamps(result)
    market.check_market(market.Market(invented(), everyone(), result, DAYS))


def test_each_feature_is_its_family_normalized() -> None:
    prices = invented()
    result = built(prices)
    for family in (returns.returns, volatility.volatility, volume.volume_ratios, indicators.indicators):
        ranked = normalize.normalize(family(prices, DAYS), everyone())
        assert result.select(ranked.columns).equals(ranked)


def test_values_and_nulls() -> None:
    result = built(invented())
    assert result["ret_3"].null_count() == 25 * 3  # a window needs 3 earlier sessions: the first 3 days are null
    assert result["ret_63"].null_count() == 25 * 63
    assert result.filter(pl.col("date") == DAYS[-1])["ret_63"].is_not_null().all()
    assert result.filter(pl.col("ret_3").is_not_null())["ret_3"].abs().max() <= 0.5
    assert result.filter(pl.col("ret_63").is_null())["ret_63_stamp"].is_not_null().sum() == 0


@pytest.mark.parametrize("cut", [30, 60, 85])
def test_a_later_price_moves_no_earlier_row(cut: int) -> None:
    prices = invented()
    changed = prices.with_columns(
        close=pl.when(pl.col("date") > DAYS[cut]).then(pl.col("close") * 3.7 + 11).otherwise(pl.col("close")),
        volume=pl.when(pl.col("date") > DAYS[cut]).then(pl.col("volume") * 0.1).otherwise(pl.col("volume")),
    )
    before, after = built(prices), built(changed)
    assert before.filter(pl.col("date") <= DAYS[cut]).equals(after.filter(pl.col("date") <= DAYS[cut]))
    assert not before.filter(pl.col("date") > DAYS[cut]).equals(after.filter(pl.col("date") > DAYS[cut]))


def test_a_name_outside_the_universe_takes_no_part() -> None:
    members = everyone().filter(pl.col("ticker") != "T00")
    ranked = built(invented(), members)
    assert "T00" not in ranked["ticker"].to_list()
    assert ranked.height == 24 * len(DAYS)


def test_a_universe_cell_without_a_price_row_keeps_a_null_row() -> None:
    prices = invented().filter(~((pl.col("ticker") == "T01") & (pl.col("date") == DAYS[80])))
    result = built(prices)
    row = result.filter((pl.col("ticker") == "T01") & (pl.col("date") == DAYS[80]))
    assert row.height == 1
    assert row.select(LITERAL[2:]).null_count().row(0) == (1,) * len(LITERAL[2:])


def test_same_input_same_table() -> None:
    assert built(invented()).equals(built(invented()))


def test_the_universe_in_any_order_gives_the_same_table() -> None:
    members = everyone().sample(fraction=1.0, shuffle=True, seed=3)
    assert members.equals(everyone()) is False
    assert built(invented(), members).equals(built(invented()))
