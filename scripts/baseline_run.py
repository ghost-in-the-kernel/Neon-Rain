"""Run a baseline through the runner on the real WIKI data and append its trials lines (TODO 3.1; R-007, R-026).

    PYTHONPATH=. python scripts/baseline_run.py zero|momentum <neon-rain-data clone> <YYYY-MM-DD>

The date is the run's date for harness/trials.tsv (the clock is read nowhere in neonrain/, MOD-05). Loads the prices
through `prices.load` (refused unless every hash checks), ranks the universe (membership), cuts the calendar to the
sessions from the universe's first date to the last price date, and runs the baseline through
`neonrain.baselines.runner` at all four horizons, each period apart. Prints each stage's time and, per line written,
its period, horizon, metric and mean. No price is written anywhere; the only file touched is harness/trials.tsv.
"""
import sys
import time
from datetime import date
from functools import partial
from pathlib import Path

from neonrain import targets
from neonrain.baselines import momentum, record, runner, zero
from neonrain.universe import calendar, membership, prices, verified

ROOT = Path(__file__).resolve().parents[1]
BASELINES = {zero.NAME: lambda prices, members, every: zero.scores(members), momentum.NAME: momentum.scores}


def stage(name: str, started: float) -> float:
    """Print how long a stage took, return the time now."""
    now = time.monotonic()
    print(f"{name}: {now - started:.1f}s", flush=True)
    return now


def main(argv: list[str]) -> int:
    """Run the named baseline and append its lines; 0 on success, 2 on misuse."""
    if len(argv) != 3 or argv[0] not in BASELINES:
        print(__doc__, file=sys.stderr)
        return 2
    day = date.fromisoformat(argv[2])
    manifest = (ROOT / "data" / "MANIFEST.md").read_text()
    now = time.monotonic()
    every = calendar.sessions(1998, 2017)
    loaded = prices.load(Path(argv[1]) / "wiki" / "prices", manifest, every)
    now = stage("load prices", now)
    members = membership.universe(prices.for_membership(loaded.prices), every)
    now = stage("universe", now)
    sessions = [d for d in every if members["date"].min() <= d <= loaded.prices["date"].max()]
    frame = loaded.prices.filter(loaded.prices["date"].is_between(sessions[0], sessions[-1]))
    market = runner.scored_market(frame, members, sessions, BASELINES[argv[0]](loaded.prices, members, every))
    now = stage(f"market ({len(sessions)} sessions {sessions[0]} to {sessions[-1]}, {members.height} universe cells)", now)
    run = runner.Run(argv[0], [], {prices.DATASET: verified.manifest_hash(manifest, prices.DATASET)})
    labels_for = partial(targets.labels, frame, members, sessions, min_tickers=run.min_tickers)
    parts = runner.evaluate(market, labels_for, run)
    now = stage("evaluate", now)
    for line in record.record(ROOT / "harness" / "trials.tsv", day, run, parts):
        print(*line, sep="\t")
    stage("record", now)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
