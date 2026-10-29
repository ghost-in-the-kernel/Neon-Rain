"""Run a baseline through the runner on the real WIKI data and append its trials lines (TODO 3.1; R-007, R-026).

    PYTHONPATH=. python scripts/baseline_run.py zero|momentum|reversal <neon-rain-data clone> <YYYY-MM-DD>
    PYTHONPATH=. python scripts/baseline_run.py tree <neon-rain-data clone> <YYYY-MM-DD> <progress log> <checkpoint dir> [--horizons 3,5,21,63]

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

**The tree is resumable, horizon by horizon.** A horizon takes about 50 minutes and a background task at most two
hours, so each finished horizon is saved in the checkpoint directory (outside this repository, refused if inside it;
`neonrain.baselines.checkpoint`: named by the run's config hash, so another run's file is never read) and a start loads
the horizons already saved instead of computing them. `--horizons 3,5` computes only those that have no checkpoint,
saves them and exits 0 without touching harness/trials.tsv; the lines are appended only when all four horizons are
present (an invocation with no `--horizons` computes whatever is missing, then writes), in the order and with the
content of an uninterrupted run. The fixed-score baselines take neither argument and are unchanged.
"""
import sys
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from functools import partial
from pathlib import Path
from typing import NamedTuple

import polars as pl

from neonrain import targets
from neonrain.baselines import checkpoint, momentum, record, reversal, runner, tree, zero
from neonrain.harness import split
from neonrain.harness.market import Market, check_market
from neonrain.universe import calendar, prices, verified
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
    """Whether a path (a log, a checkpoint directory) lies outside this repository (neither is kept in it)."""
    return ROOT not in path.resolve().parents


def split_horizons(argv: list[str]) -> tuple[list[str], tuple[int, ...] | None]:
    """The arguments without `--horizons a,b`, and the horizons it names (None if it is absent); ValueError if malformed
    or if a horizon is not one of the harness's."""
    if "--horizons" not in argv:
        return argv, None
    at = argv.index("--horizons")
    if at + 1 >= len(argv):
        raise ValueError("--horizons needs a list such as 3,5")
    chosen = tuple(int(h) for h in argv[at + 1].split(","))
    unknown = [h for h in chosen if h not in split.HORIZONS]
    if unknown:
        raise ValueError(f"--horizons {unknown} are not among the harness's {list(split.HORIZONS)}")
    return argv[:at] + argv[at + 2:], chosen


def stage(name: str, started: float) -> float:
    """Print how long a stage took, return the time now."""
    now = time.monotonic()
    print(f"{name}: {now - started:.1f}s", flush=True)
    return now


class Request(NamedTuple):
    """What the command line asked: the baseline, the data clone, the day, the tree's log and checkpoint directory, the
    horizons named (None: all)."""

    name: str
    clone: Path
    day: date
    log: Path | None
    saved: Path | None
    wanted: tuple[int, ...] | None


def read_arguments(argv: list[str]) -> Request:
    """The command line as a `Request`; ValueError with the text to print if it is misused (nothing has been read yet)."""
    argv, wanted = split_horizons(argv)
    fitted = bool(argv) and argv[0] == FITTED
    if not argv or argv[0] not in [*BASELINES, FITTED] or len(argv) != (5 if fitted else 3) or (wanted and not fitted):
        raise ValueError(__doc__)
    log, saved = (Path(argv[3]), Path(argv[4])) if fitted else (None, None)
    for name, path in (("progress log", log), ("checkpoint directory", saved)):
        if path is not None and not log_outside(path):
            raise ValueError(f"the {name} {path} is inside the repository; give a path outside it")
    return Request(argv[0], Path(argv[1]), date.fromisoformat(argv[2]), log, saved, wanted)


def prepare(ask: Request, manifest: str, started: float) -> tuple[Market, runner.Run, Callable[[int], runner.Labelled], float]:
    """Load the data and build the market, the run and the labels' function; the time now."""
    now = started
    every = calendar.sessions(1998, 2017)
    loaded = prices.load(ask.clone / "wiki" / "prices", manifest, every)
    now = stage("load prices", now)
    members = prices.universe(loaded.prices, every)
    now = stage("universe", now)
    sessions = [d for d in every if members["date"].min() <= d <= loaded.prices["date"].max()]
    frame = loaded.prices.filter(loaded.prices["date"].is_between(sessions[0], sessions[-1]))
    if ask.log is None:
        market = runner.scored_market(frame, members, sessions, BASELINES[ask.name](loaded.prices, members, every))
        run = runner.Run(ask.name, [], {prices.DATASET: verified.manifest_hash(manifest, prices.DATASET)})
    else:
        features = feature_table.load(manifest, artifacts.default_clone(), artifacts.default_remote())
        now = stage(f"feature table {features.shape}", now)
        market = feature_market(frame, members, sessions, features)
        run = tree_run(manifest)
    now = stage(f"market ({len(sessions)} sessions {sessions[0]} to {sessions[-1]}, {members.height} universe cells)", now)
    return market, run, partial(targets.labels, frame, members, sessions, min_tickers=run.min_tickers), now


def main(argv: list[str]) -> int:
    """Run the named baseline and append its lines; 0 on success (also when `--horizons` left some horizon for a later
    start, with no line written), 2 on misuse."""
    try:
        ask = read_arguments(argv)
    except ValueError as refused:
        print(refused, file=sys.stderr)
        return 2
    started = time.monotonic()
    market, run, labels_for, now = prepare(ask, (ROOT / "data" / "MANIFEST.md").read_text(), started)
    if ask.log is None or ask.saved is None:
        parts = runner.evaluate(market, labels_for, run)
    else:
        ask.saved.mkdir(parents=True, exist_ok=True)
        clock = lambda: (datetime.now(UTC), time.monotonic())  # noqa: E731 - the one clock read, for the log's lines
        parts = checkpoint.resume(ask.saved, market, labels_for, run, tree.fit, progress_log(ask.log, started, clock),
                                  ask.wanted, lambda text: print(text, flush=True))
    now = stage("evaluate", now)
    if len(parts) < len(run.horizons):
        print(f"horizons present: {list(parts)} of {list(run.horizons)}; no line written", flush=True)
        return 0
    for line in record.record(ROOT / "harness" / "trials.tsv", ask.day, run, parts):
        print(*line, sep="\t")
    stage("record", now)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
