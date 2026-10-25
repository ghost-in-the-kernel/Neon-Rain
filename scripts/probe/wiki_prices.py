"""Counts from loading the real sample through the price loader (TODO 2.2, NR-F-08); only counts are printed (R-006).

    python scripts/probe/wiki_prices.py <neon-rain-data clone>

Loads `<clone>/wiki/prices` (refused unless the index hashes to the manifest row and each year to its index line) on
the calendar of 1998 to 2017, runs the harness's layout checks on the frame, and prints what was left out of it.
"""
import sys
from pathlib import Path

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
    except Exception as refusal:  # noqa: BLE001 - a verification refusal or a layout fault; the message says which
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    market.check_prices(loaded.prices)
    market.check_on_calendar("price", loaded.prices, sessions)
    dates = loaded.prices["date"]
    off = loaded.off_calendar
    print(f"rows in the frame: {loaded.prices.height}; tickers: {loaded.prices['ticker'].n_unique()}; dates: {dates.n_unique()}")
    print(f"first date: {dates.min()}; last date: {dates.max()}; years: {dates.dt.year().n_unique()}")
    print(f"off-calendar rows: {off.height}; off-calendar dates: {off['date'].n_unique()}; tickers on them: {off['ticker'].n_unique()}")
    print(f"sessions of the calendar inside the sample with no row: {len(loaded.empty_sessions)}")
    print(f"sessions of the calendar after the last price date: {sum(1 for day in sessions if day > dates.max())}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
