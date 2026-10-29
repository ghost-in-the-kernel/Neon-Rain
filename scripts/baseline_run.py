"""Run a baseline through the runner on the real WIKI data and append its trials lines (TODO 3.1; R-007, R-026).

    PYTHONPATH=. python scripts/baseline_run.py zero|momentum|reversal <neon-rain-data clone> <YYYY-MM-DD>
    PYTHONPATH=. python scripts/baseline_run.py tree <neon-rain-data clone> <YYYY-MM-DD> <progress log>

The date is the run's date for harness/trials.tsv (the clock is read nowhere in neonrain/, MOD-05). Loads the prices
through `prices.load` (refused unless every hash checks), ranks the universe (membership), cuts the calendar to the
sessions from the universe's first date to the last price date, and runs the baseline through
`neonrain.baselines.runner` at all four horizons, each period apart. Prints each stage's time and, per line written,
its period, horizon, metric and mean. No price is written anywhere; the only file touched is harness/trials.tsv.

**The tree (TODO 3.2 b)** is a model, not a score: its market's features are the feature table, fetched from the
artifact store and verified by hash (`feature_table.load`, never a local copy), and the runner fits one LightGBM
model for each (horizon, fold, held-out group) (R-034). The third argument is a log file, outside this repository
(refused if inside it), to which one line is appended as each (horizon, fold) is done: its UTC time, the horizon, the
fold, the seconds since the start. It is the only sign of life in a run of hours; follow it with `tail -f`.
"""
import sys
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from functools import partial
from pathlib import Path

import polars as pl

from neonrain import targets
from neonrain.baselines import momentum, record, reversal, runner, tree, zero
from neonrain.harness.market import Market, check_market
from neonrain.universe import calendar, membership, prices, verified
from scripts.fetch import artifacts, feature_table

ROOT = Path(__file__).resolve().parents[1]
BASELINES = {zero.NAME: lambda prices, members, every: zero.scores(members), momentum.NAME: momentum.scores,
             reversal.NAME: reversal.scores}


FITTED = tree.NAME  # a baseline with a model: it takes a progress log, and its market holds the feature table


def tree_run(manifest: str) -> runner.Run:
    """The tree's run: the sixteen feature columns of the feature table, R-034's hyperparameters, and both datasets'
    hashes (the prices and the feature table) in its config (HAR-01)."""
    return runner.Run(tree.NAME, feature_table.feature_names(),
                      {prices.DATASET: verified.manifest_hash(manifest, prices.DATASET),
                       feature_table.DATASET: verified.manifest_hash(manifest, feature_table.DATASET)},
                      hyperparameters=tree.HYPERPARAMETERS)


def feature_market(frame: pl.DataFrame, members: pl.DataFrame, sessions: list[date], features: pl.DataFrame) -> Market:
    """The harness's Market whose features are the feature table, cut to the sessions; refused (HAR-12) if a stamp is late."""
    cut = features.filter(pl.col("date").is_between(sessions[0], sessions[-1]))
    if not cut.select(runner.KEYS).equals(members.select(runner.KEYS).sort(runner.KEYS)):
        raise ValueError("the feature table's cells are not the universe's: it was built from other prices or another universe")
    market = Market(frame, members, cut, sessions)
    check_market(market)
    return market


def progress_line(stamp: datetime, seconds: float, horizon: int, fold: int, folds: int) -> str:
    """One line of the progress log: the UTC time, the horizon, the fold (of how many), the seconds since the start."""
    return f"{stamp.astimezone(UTC).isoformat(timespec='seconds')}\thorizon {horizon}\tfold {fold + 1} of {folds}\t{seconds:.0f}s"


def progress_log(path: Path, started: float, now: Callable[[], tuple[datetime, float]]) -> runner.Progress:
    """A `runner.Progress` that appends `progress_line` to `path` and flushes, so `tail -f` shows it at once."""
    def write(horizon: int, fold: int, folds: int) -> None:
        stamp, seconds = now()
        with path.open("a") as handle:
            handle.write(progress_line(stamp, seconds - started, horizon, fold, folds) + "\n")
    return write


def log_outside(path: Path) -> bool:
    """Whether a log path lies outside this repository (a log is never kept in it)."""
    return ROOT not in path.resolve().parents


def stage(name: str, started: float) -> float:
    """Print how long a stage took, return the time now."""
    now = time.monotonic()
    print(f"{name}: {now - started:.1f}s", flush=True)
    return now


def main(argv: list[str]) -> int:
    """Run the named baseline and append its lines; 0 on success, 2 on misuse."""
    if not argv or argv[0] not in [*BASELINES, FITTED] or len(argv) != (4 if argv[0] == FITTED else 3):
        print(__doc__, file=sys.stderr)
        return 2
    log = Path(argv[3]) if len(argv) == 4 else None
    if log is not None and not log_outside(log):
        print(f"the progress log {log} is inside the repository; give a path outside it", file=sys.stderr)
        return 2
    day = date.fromisoformat(argv[2])
    manifest = (ROOT / "data" / "MANIFEST.md").read_text()
    started = now = time.monotonic()
    every = calendar.sessions(1998, 2017)
    loaded = prices.load(Path(argv[1]) / "wiki" / "prices", manifest, every)
    now = stage("load prices", now)
    members = membership.universe(prices.for_membership(loaded.prices), every)
    now = stage("universe", now)
    sessions = [d for d in every if members["date"].min() <= d <= loaded.prices["date"].max()]
    frame = loaded.prices.filter(loaded.prices["date"].is_between(sessions[0], sessions[-1]))
    if log is None:
        market = runner.scored_market(frame, members, sessions, BASELINES[argv[0]](loaded.prices, members, every))
        run = runner.Run(argv[0], [], {prices.DATASET: verified.manifest_hash(manifest, prices.DATASET)})
    else:
        features = feature_table.load(manifest, artifacts.default_clone(), artifacts.default_remote())
        now = stage(f"feature table {features.shape}", now)
        market = feature_market(frame, members, sessions, features)
        run = tree_run(manifest)
    now = stage(f"market ({len(sessions)} sessions {sessions[0]} to {sessions[-1]}, {members.height} universe cells)", now)
    labels_for = partial(targets.labels, frame, members, sessions, min_tickers=run.min_tickers)
    if log is None:
        parts = runner.evaluate(market, labels_for, run)
    else:
        clock = lambda: (datetime.now(UTC), time.monotonic())  # noqa: E731 - the one clock read, for the log's lines
        parts = runner.evaluate(market, labels_for, run, tree.fit, progress_log(log, started, clock))
    now = stage("evaluate", now)
    for line in record.record(ROOT / "harness" / "trials.tsv", day, run, parts):
        print(*line, sep="\t")
    stage("record", now)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
