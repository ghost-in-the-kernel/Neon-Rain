"""HAR-14 and HAR-13: the goldens, the harness's own numbers on one fixed synthetic market, and what holds them.

`compute` runs the harness (labels, folds, groups, metrics, portfolio, dispersion, config hash) on the market
of `MARKET` and returns each golden's text; `write` records them in `harness/goldens/` beside an index of their
hashes; `check` says every way the directory and the harness disagree. A harness change that moves a number
makes `check` name the golden, so the change either leaves every golden identical or is written with a decision
in force (`write(..., decision=)`), which the index keeps. Pure apart from the files `write` is given (HAR-11).
"""
import hashlib
import json
import re
from pathlib import Path

import polars as pl

from neonrain import targets
from neonrain.harness import dispersion, metrics, portfolio, split, synthetic, trials
from neonrain.harness.market import Market

MARKET = synthetic.MarketConfig(tickers=150, days=330, rho=0.1, delist_below=0.5, seed=7)
GEOMETRY = {"embargo": split.EMBARGO, "step": 40, "min_train": 100}  # small folds keep the grid fast (HAR-14)
DEFAULT_DAYS = 1200  # the calendar on which the default folds of HAR-03 are recorded
GROUP_SEED = 5
DIGITS = 12  # significant digits kept in a golden's floats (HAR-14)
INDEX = "index.json"
FIRST = "1.7"  # who wrote a golden first: the freeze itself
VARIANCE = 0.0004  # the variance of the Sharpes tried, for the deflated Sharpe of five trials
TRIALS = (1, 5)
KEYS = ["ticker", "date"]
CONFIG = {"feature_columns": ["edge"], "target": {"horizons": list(targets.HORIZONS), "min_tickers": 20},
          "split": {**GEOMETRY, "window": None, "k": split.GROUPS, "seed": GROUP_SEED},
          "cost": {"levels_bps": list(portfolio.COST_LEVELS_BPS), "default_bps": portfolio.DEFAULT_COST_BPS},
          "model_name": "edge-rank", "hyperparameters": {}, "data_manifest": {"synthetic": "seed-7"}}
DECISION = re.compile(r"R-\d{3}")


class GoldenChange(Exception):
    """A golden that would change without a decision in force to say why."""


def rounded(value: object) -> object:
    """Every float in a nested value cut to DIGITS significant digits: 1/3 gives 0.333333333333."""
    if isinstance(value, float):
        return float(f"{value:.{DIGITS - 1}e}")
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [rounded(item) for item in value]
    return value


def dumped(value: object) -> str:
    """A golden's text: rounded floats, sorted keys, one-space indent, a final line break; NaN is refused."""
    return json.dumps(rounded(value), indent=1, sort_keys=True, allow_nan=False) + "\n"


def sha256(text: str) -> str:
    """The SHA-256 of a text's UTF-8 bytes, in lowercase hex."""
    return hashlib.sha256(text.encode()).hexdigest()


def edge_scores(market: Market) -> pl.DataFrame:
    """The golden model: each ticker's score on a date is its edge's rank fraction among that date's tickers."""
    ranked = pl.col("edge").rank("average").over("date") - 1.0
    width = (pl.len().over("date") - 1.0).clip(lower_bound=1.0)
    return market.features.select(*KEYS, (ranked / width).alias("score"))


def label_summary(found: targets.Labels) -> dict[str, object]:
    """One horizon's label counts (HAR-02) and the means of its columns."""
    frame = found.frame
    return {"rows": frame.height, "dropped_missing": found.dropped_missing, "dropped_ties": found.dropped_ties,
            "dropped_thin_dates": found.dropped_thin_dates, "delisting_ends": found.delisting_ends,
            "mean_forward": frame["forward"].mean(), "mean_excess": frame["excess"].mean(),
            "mean_direction": frame["direction"].mean(), "mean_rank": frame["rank"].mean()}


# Decision: R-021 (a cell's portfolio is scored on every universe row of its test span, at all three cost levels)
def cell_numbers(market: Market, rows: pl.DataFrame, scored: pl.DataFrame, fold: split.Fold, group: int,
                 horizon: int) -> dict[str, object]:
    """One (fold, group) cell: its row counts and every HAR-07 metric on the held-out group's test span."""
    groups = split.ticker_groups(market.features["ticker"].unique().to_list(), split.GROUPS, GROUP_SEED)
    train, test = split.cell(rows, fold, market.calendar, horizon, groups, group)
    held = [name for name, found in groups.items() if found == group]
    tested = split.testing(scored, fold, market.calendar).filter(pl.col("ticker").is_in(held))
    prices = market.prices.filter(pl.col("ticker").is_in(held))
    nets = {bps: portfolio.daily(tested, prices, market.calendar, horizon, bps)["net"].to_numpy()
            for bps in sorted({*portfolio.COST_LEVELS_BPS, portfolio.DEFAULT_COST_BPS})}
    ic = metrics.information_coefficient(test.select("date", "score", "rank"))
    default = nets[portfolio.DEFAULT_COST_BPS]
    return {"fold": fold.number, "group": group, "train_rows": train.height, "test_rows": test.height,
            "accuracy": metrics.accuracy(test), "balanced_accuracy": metrics.balanced_accuracy(test),
            "ic": ic._asdict(), **{f"sharpe_{int(b)}bps": metrics.sharpe(nets[b]) for b in portfolio.COST_LEVELS_BPS},
            **{f"dsr_{n}": metrics.deflated_sharpe(default, n, VARIANCE) for n in TRIALS}}


def metric_values(cells: list[dict[str, object]]) -> dict[str, dict[tuple[int, int], float | None]]:
    """Each scalar metric's value in each (fold, group) cell, the IC by its mean."""
    names = [name for name in cells[0] if name not in ("fold", "group", "train_rows", "test_rows", "ic")]
    found = {name: {(c["fold"], c["group"]): c[name] for c in cells} for name in names}  # type: ignore[index]
    found["ic"] = {(c["fold"], c["group"]): c["ic"]["mean"] for c in cells}  # type: ignore[index]
    return found


def dispersions(cells: list[dict[str, object]]) -> dict[str, object]:
    """HAR-08's dispersion of every metric of one horizon's cells, as plain data."""
    out = {}
    for name, values in sorted(metric_values(cells).items()):
        found = dispersion.dispersion(values)
        out[name] = {"folds": found.folds._asdict() if found.folds else None,
                     "groups": found.groups._asdict() if found.groups else None,
                     "undefined_cells": found.undefined_cells, "fits_names": found.fits_names}
    return out


def horizon_cells(market: Market, scored: pl.DataFrame, horizon: int) -> tuple[dict[str, object], list]:
    """One horizon's label summary and its grid of cells (every fold by every group)."""
    found = targets.labels(market.prices, market.universe, market.calendar, horizon)
    rows = found.frame.join(scored, on=KEYS)
    cells = [cell_numbers(market, rows, scored, fold, group, horizon)
             for fold in split.folds(len(market.calendar), **GEOMETRY) for group in range(split.GROUPS)]
    return label_summary(found), cells


# Exempt from mutation (Ghost, J-032; docs/MUTATION.md): compute() runs every harness module, so a test of it
# would rerun for every mutant of every module; its output is the goldens, compared byte for byte before each push.
# pragma: no mutate start
def compute(config: synthetic.MarketConfig = MARKET) -> dict[str, str]:
    """Every golden's file name and text for a synthetic market (HAR-14); the same config gives the same texts."""
    market = synthetic.generate(config)
    scored = edge_scores(market)
    labels, cells, spread = {}, {}, {}
    for horizon in targets.HORIZONS:
        labels[str(horizon)], cells[str(horizon)] = horizon_cells(market, scored, horizon)
        spread[str(horizon)] = dispersions(cells[str(horizon)])
    groups = split.ticker_groups(market.features["ticker"].unique().to_list(), split.GROUPS, GROUP_SEED)
    folds = [fold._asdict() for fold in split.folds(len(market.calendar), **GEOMETRY)]
    defaults = [fold._asdict() for fold in split.folds(DEFAULT_DAYS)]
    return {"synthetic_labels.json": dumped(labels), "synthetic_cells.json": dumped(cells),
            "synthetic_dispersion.json": dumped(spread),
            "synthetic_splits.json": dumped({"folds": folds, "default_folds": defaults, "groups": groups}),
            "config_hash.json": dumped({"config": CONFIG, "harness_version": trials.HARNESS_VERSION,
                                        "hash": trials.config_hash(**CONFIG)})}  # type: ignore[arg-type]
# pragma: no mutate end


def in_force(ghost: str, decision: str) -> bool:
    """Whether theGhost.md has an entry R-nnn whose Status line says `in force`."""
    if DECISION.fullmatch(decision) is None:
        return False
    entry = re.search(rf"^### {decision}: .*?(?=^### |\Z)", ghost, re.MULTILINE | re.DOTALL)
    return entry is not None and re.search(r"^- \*\*Status:\*\* in force$", entry.group(0), re.MULTILINE) is not None


def index_text(files: dict[str, str], changed_by: dict[str, str]) -> str:
    """The index: the harness version and, per golden, its SHA-256 and what last changed it (FIRST or a decision)."""
    return dumped({"harness_version": trials.HARNESS_VERSION,
                   "files": {name: {"sha256": sha256(text), "changed_by": changed_by[name]}
                             for name, text in sorted(files.items())}})


def recorded(directory: Path) -> dict[str, dict[str, str]]:
    """The index's files entry, {} where there is no index."""
    path = directory / INDEX
    return json.loads(path.read_text())["files"] if path.is_file() else {}


# Decision: R-002 (a golden changes only under a decision in force, and the index says which)
def write(directory: Path, files: dict[str, str], ghost: str, decision: str | None = None) -> list[str]:
    """Record `files` as the goldens in `directory`; returns the names written or removed.

    The first write is the freeze (FIRST). Afterwards a golden added, removed or whose text differs is a change,
    and needs `decision`: an R-nnn in force in `ghost` (theGhost.md's text), kept in the index. Nothing is written
    when refused.
    """
    old = recorded(directory)
    changed = sorted(name for name, text in files.items() if name not in old or (directory / name).read_text() != text)
    removed = sorted(set(old) - set(files))
    if old and (changed or removed) and decision is None:
        raise GoldenChange(f"{', '.join(changed + removed)} would change: pass a decision in force (HAR-14, R-002)")
    if decision is not None and not in_force(ghost, decision):
        raise GoldenChange(f"{decision} is not an entry in force in theGhost.md (HAR-14)")
    by = {name: entry["changed_by"] for name, entry in old.items() if name in files}
    by |= {name: decision if old and decision else FIRST for name in changed}
    directory.mkdir(parents=True, exist_ok=True)
    for name in changed:
        (directory / name).write_text(files[name])
    for name in removed:
        (directory / name).unlink()
    (directory / INDEX).write_text(index_text(files, by))
    return changed + removed


def first_difference(golden: str, found: str) -> str:
    """The first line where two texts differ: 'line 3: golden "a", harness "b"'."""
    pairs = zip(golden.splitlines() + [""], found.splitlines() + [""])
    number, (a, b) = next((n, p) for n, p in enumerate(pairs, start=1) if p[0] != p[1])
    return f'line {number}: golden "{a.strip()}", harness "{b.strip()}"'


def file_problems(directory: Path, name: str, text: str, entry: dict[str, str] | None) -> list[str]:
    """What is wrong with one golden: missing, unindexed, edited by hand, or not what the harness gives now."""
    path = directory / name
    if not path.is_file():
        return [f"{name} is missing from {directory.name}/ (HAR-14)"]
    held = path.read_text()
    found = [] if entry is not None else [f"{name} is not in {INDEX}"]
    if entry is not None and entry["sha256"] != sha256(held):
        found.append(f"{name} was edited by hand: its hash is not the index's")
    if held != text:
        found.append(f"{name} differs from the harness's output, {first_difference(held, text)} (HAR-13, R-002)")
    return found


def check(directory: Path, files: dict[str, str], ghost: str) -> list[str]:
    """Every disagreement between the goldens on disk and the harness's `files`, [] when there is none."""
    old = recorded(directory)
    found = [] if (directory / INDEX).is_file() else [f"{INDEX} is missing from {directory.name}/ (HAR-14)"]
    for name, text in sorted(files.items()):
        found += file_problems(directory, name, text, old.get(name))
    found += [f"{name} is in {INDEX} and is no golden of the harness" for name in sorted(set(old) - set(files))]
    for name, entry in sorted(old.items()):
        if entry["changed_by"] != FIRST and not in_force(ghost, entry["changed_by"]):
            found.append(f"{name} was changed by {entry['changed_by']}, which is not in force in theGhost.md")
    changed = sorted(name for name, entry in old.items() if entry["changed_by"] != FIRST)
    if changed and int(trials.HARNESS_VERSION) < 2:
        found.append(f"{', '.join(changed)} changed under a decision, and harness_version is still 1 (HAR-01, HAR-14)")
    if (directory / INDEX).is_file():
        version = json.loads((directory / INDEX).read_text())["harness_version"]
        found += [] if version == trials.HARNESS_VERSION else [f"{INDEX} is for harness version {version}"]
    return found
