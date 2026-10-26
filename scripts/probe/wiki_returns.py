"""Counts from the returns family on the real sample (TODO 2.3); only counts are printed, no price or return (R-006).

    PYTHONPATH=. python scripts/probe/wiki_returns.py <neon-rain-data clone>

Loads `<clone>/wiki/prices` as `wiki_prices.py` does, builds the returns family on the calendar of 1998 to 2017,
runs the harness's stamp check on the frame, and prints for each lookback the cells with a value and the cells without.
"""
import sys
from pathlib import Path

import polars as pl

from neonrain.features import returns
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
        frame = returns.returns(loaded.prices, sessions)
        market.check_stamps(frame)
    except Exception as refusal:  # noqa: BLE001 - a verification refusal, a layout fault or a stamp refusal
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    print(f"cells: {frame.height}; tickers: {frame['ticker'].n_unique()}; stamps pass the harness's check")
    for lookback in returns.LOOKBACKS:
        column = returns.name(lookback)
        valued = frame[column].is_not_null().sum()
        infinite = frame.filter(pl.col(column).is_infinite()).height
        print(f"{column}: with a value {valued}; without {frame.height - valued}; infinite {infinite}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
