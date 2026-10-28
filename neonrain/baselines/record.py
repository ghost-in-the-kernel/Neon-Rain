"""The trials lines of a baseline run (HAR-09, HAR-01): one per (horizon, metric) for each period, and nothing else.

Each period is a run of its own: the period is in the config hash's `split`, so the two periods' lines never share a
hash (HAR-01 would call two different means under one hash, horizon and metric a conflict). Every line's note names
the period and the whole-sample label counts of its horizon (HAR-02, HAR-13). The DSR needs the trial count and the
variance of the Sharpes tried, which only the trials file knows, so a horizon's DSR line is written after that
horizon's other lines (HAR-07, HAR-09). A repeat of a run is no conflict at its DSR (HAR-01).
"""
import statistics
from datetime import date
from pathlib import Path
from typing import NamedTuple

from neonrain.baselines.runner import PERIOD_NAMES, Cell, Horizon, Run, scalar_metrics
from neonrain.harness import dispersion, metrics, portfolio, trials

SHARPE_FOR_DSR = f"Sharpe_{int(portfolio.DEFAULT_COST_BPS)}bps"
CellValues = dict[tuple[int, int], float | None]


class Line(NamedTuple):
    """One line written, for the caller to print: its period, horizon, metric, mean and trials_so_far."""

    period: str
    horizon: int
    metric: str
    mean: float | None
    trials_so_far: int


class Where(NamedTuple):
    """Where a period's lines go: the trials file, the run's date, the period's config hash, the period."""

    path: Path
    day: date
    config_hash: str
    period: str


def config_hash(run: Run, period: str) -> str:
    """HAR-01's hash of one period of a run: the period sits in `split`, beside the geometry and the group seed."""
    split_config = {**run.geometry, "k": run.groups, "seed": run.group_seed, "period": period}
    return trials.config_hash(
        feature_columns=run.feature_columns,
        target={"horizons": list(run.horizons), "min_tickers": run.min_tickers},
        split=split_config,
        cost={"levels_bps": list(portfolio.COST_LEVELS_BPS), "default_bps": portfolio.DEFAULT_COST_BPS},
        model_name=run.name, hyperparameters={}, data_manifest=run.data_manifest)


def count_note(period: str, part: Horizon, cells: list[Cell]) -> str:
    """The note every line of a (period, horizon) carries: period, cells and rows, then HAR-02's whole-sample counts."""
    found = part.found
    return (f"period={period}; cells={len(cells)}; test_rows={sum(c.test_rows for c in cells)}; "
            f"dropped_missing={found.dropped_missing}; dropped_ties={found.dropped_ties}; "
            f"dropped_thin_dates={found.dropped_thin_dates}; delisting_ends={found.delisting_ends} (whole sample)")


def ic_note(cells: list[Cell]) -> str:
    """HAR-07's IC counts over a period's cells: dates averaged, and the dates dropped as thin or flat."""
    return (f"IC dates={sum(c.ic.dates for c in cells)}; dropped_thin={sum(c.ic.dropped_thin for c in cells)}; "
            f"dropped_flat={sum(c.ic.dropped_flat for c in cells)}")


def append(where: Where, part: Horizon, metric: str, values: CellValues, extra: str = "") -> Line:
    """One line: the fold-axis mean of `values` (HAR-09) and both axes' dispersion; a missing number says why."""
    cells = part.cells[where.period]
    spread = dispersion.dispersion(values) if values else None
    mean = spread.folds.mean if spread is not None and spread.folds is not None else None
    why = "" if mean is not None else "no number: no cell has this metric defined" if cells else "no test date in this period"
    note = "; ".join(filter(None, [why, count_note(where.period, part, cells), extra]))
    so_far = trials.append_trial(where.path, run=where.config_hash, day=where.day, horizon=part.horizon,
                                 metric=metric, mean=mean, dispersion=spread, note=note)
    return Line(where.period, part.horizon, metric, mean, so_far)


def sharpe_variance(path: Path) -> float | None:
    """The sample variance (divisor: their count less one) of the non-annualized Sharpes in the trials file (HAR-07's V):
    the mean of every `SHARPE_FOR_DSR` line in the file now, each over the square root of 252; a line with no mean is
    left out; None with fewer than two."""
    found = [float(row[4]) / metrics.TRADING_DAYS**0.5 for row in trials.fields_of(path.read_text())
             if row[trials.METRIC] == SHARPE_FOR_DSR and row[4]]
    return statistics.variance(found) if len(found) > 1 else None


def trials_before(path: Path, metric: str) -> int:
    """How many lines of `metric` the trials file holds: HAR-09's trials_so_far for the next one."""
    return sum(1 for row in trials.fields_of(path.read_text()) if row[trials.METRIC] == metric)


# Decision: HAR-09 (N is the lines of the metric before this one, plus this one; V comes from the Sharpes tried)
def dsr_values(where: Where, cells: list[Cell]) -> tuple[CellValues, str]:
    """Each cell's DSR on the default cost's series at this line's N, and the note saying N and where V came from."""
    count = trials_before(where.path, trials.DEFLATED) + 1
    variance = sharpe_variance(where.path)
    shown = "none" if variance is None else repr(variance)
    note = f"N={count}; V={shown} (from the {SHARPE_FOR_DSR} lines)"
    if count > 1 and variance is None:
        return {(c.fold, c.group): None for c in cells}, note + "; fewer than two Sharpes to take a variance of"
    series = portfolio.DEFAULT_COST_BPS
    return {(c.fold, c.group): metrics.deflated_sharpe(c.nets[series], count, variance) for c in cells}, note


def write_period(where: Where, parts: dict[int, Horizon]) -> list[Line]:
    """A period's lines, horizon by horizon: its non-DSR metrics, then its DSR, whose V sees the Sharpes written so far."""
    found = []
    for part in parts.values():
        cells = part.cells[where.period]
        for name, scalar in scalar_metrics().items():
            values = {(c.fold, c.group): scalar(c) for c in cells}
            found.append(append(where, part, name, values, ic_note(cells) if name == "IC" else ""))
        values, note = dsr_values(where, cells)
        found.append(append(where, part, trials.DEFLATED, values, note))
    return found


def record(path: Path, day: date, run: Run, parts: dict[int, Horizon]) -> list[Line]:
    """Append the run's lines to the trials file at `path`, each period under its own config hash; what was written."""
    found = []
    for period in PERIOD_NAMES:
        found += write_period(Where(path, day, config_hash(run, period), period), parts)
    return found
