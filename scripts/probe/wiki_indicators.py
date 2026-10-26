"""Counts from the indicator family on the real sample (TODO 2.3); only counts are printed, no price or indicator (R-006).

    PYTHONPATH=. python scripts/probe/wiki_indicators.py <neon-rain-data clone>

Loads `<clone>/wiki/prices` as `wiki_prices.py` does, builds the indicator family on the calendar of 1998 to 2017,
runs the harness's stamp check on the frame, and prints for each feature the cells with a value and the cells without,
and how many values are infinite or nan (none is expected). For the RSI also the cells where the window is flat
(null with every close present), the case that has no value by choice.
"""
import sys
from pathlib import Path

import polars as pl

from neonrain.features import common, indicators
from neonrain.harness import market
from neonrain.universe import calendar, prices

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str]) -> int:
    """Print the counts; 0 on success, 1 on a refusal, 2 on misuse."""
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    sessions = calendar.sessions(1998, 2017)
    try:
        loaded = prices.load(Path(argv[0]) / "wiki" / "prices", (ROOT / "data" / "MANIFEST.md").read_text(), sessions)
        frame = indicators.indicators(loaded.prices, sessions)
        market.check_stamps(frame)
    except Exception as refusal:  # noqa: BLE001 - a verification refusal, a layout fault or a stamp refusal
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    own = loaded.prices
    print(f"cells: {frame.height}; tickers: {frame['ticker'].n_unique()}; stamps pass the harness's check")
    print(f"rows: {own.height}; unusable close {own.filter(~common.usable(indicators.CLOSE)).height}")
    for column in indicators.feature_columns():
        if column.endswith(indicators.STAMP_SUFFIX):
            continue
        valued = frame[column].is_not_null().sum()
        bad = frame.filter(pl.col(column).is_infinite() | pl.col(column).is_nan()).height
        print(f"{column}: with a value {valued}; without {frame.height - valued}; infinite or nan {bad}")
    flat = frame.filter(pl.col(indicators.rsi_name()).is_null() & pl.col("macd").is_not_null()).height
    print(f"rsi null where the 26-session MACD window is whole (so only a flat 14-change window): {flat}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
