"""Counts from cross-sectional normalization on the real sample (TODO 2.4); only counts are printed, no value (R-006).

    PYTHONPATH=. python scripts/probe/wiki_normalize.py <neon-rain-data clone>

Loads `<clone>/wiki/prices` as `wiki_prices.py` does, builds the universe frame (neonrain.universe.membership) and two
families (returns and volume ratios) on the calendar of 1998 to 2017, normalizes each, runs the harness's stamp check
and layout check on the result, and prints: the universe's cells, the family's cells outside the universe (left out),
the normalized cells with a value for each feature, the dates below the fewest names, and the largest absolute mean of
a date's cross-section (0 up to rounding).
"""
import sys
from pathlib import Path

import polars as pl

from neonrain.features import normalize, returns, volume
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
        members = prices.universe(loaded.prices, sessions)
        print(f"universe cells: {members.height}; dates: {members['date'].n_unique()}")
        for label, frame in (("returns", returns.returns(loaded.prices, sessions)), ("volume", volume.volume_ratios(loaded.prices, sessions))):
            result = normalize.normalize(frame, members)
            market.check_stamps(result)
            outside = frame.join(members, on=["ticker", "date"], how="anti").height
            print(f"{label}: family cells {frame.height}; outside the universe (left out) {outside}; normalized cells {result.height}")
            for name in normalize.feature_names(result):
                valued = result.filter(pl.col(name).is_not_null())
                thin = result.group_by("date").agg(pl.col(name).is_not_null().sum().alias("n")).filter(pl.col("n") < normalize.MIN_NAMES)
                spread = valued.group_by("date").agg(pl.col(name).mean().abs().alias("m"))["m"].max()
                print(f"  {name}: with a value {valued.height}; without {result.height - valued.height}; dates under the fewest {thin.height}; largest |mean| {spread:.2e}")
    except Exception as refusal:  # noqa: BLE001 - a verification refusal, a layout fault or a stamp refusal
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
