"""The baseline runner (TODO 3.1 a): a score frame through the frozen harness, at every horizon, each period apart.

Given prices, the universe, the calendar and a score for each cell (ticker, date, score, stamp), `evaluate` runs
HAR-02's labels (handed in, see below), HAR-03's folds, HAR-05's ticker groups, HAR-07's metrics, the portfolio at the
three costs of HAR-06 and R-021, and keeps every (fold, group) cell, so HAR-08's dispersion can be read off any metric.
It reimplements nothing of the harness: every number is a call into `neonrain.harness`.
A signal that looks back is computed on the uncut prices; the runner is given the prices cut at the universe's
first date (`scripts/baseline_run.py`). The stamp check (HAR-12) holds what a score claims, not what it read.

**How folds fall within a period (R-026).** The folds are HAR-03's, laid on the whole calendar and the same for all
four horizons and both periods (J-015). A period is then a selection of test dates: a cell's test rows, and the rows its
portfolio trades, are those of the fold's test span that fall on the period's side of `periods.BOUNDARY`. A fold whose
test span crosses the boundary is a cell in both periods, each with its own dates; a fold with no test date in a period
is no cell there. Training is never cut by period, and a baseline with no model trains on nothing. A sleeve opened
on the period's last test date runs on past the boundary (HAR-07), so a period's portfolio can hold days of the other.

**A baseline with a model (TODO 3.2 a).** Given a `Fit`, the market's features are the feature table (not a score
frame) and the runner fits one model for each (horizon, fold, held-out group): the rows are HAR-05's, from
`split.cell`: the fold's purged training rows of the other four groups (HAR-03), labelled with HAR-02's `direction`
(a tie has none and is left out), and the model scores every feature row of the held-out group's test span. A
fold's two periods share its model, since training is never cut by period. The scores then go through the same cells
as a fixed score frame's, so the metrics, the portfolio and the lines are the harness's alike. A `Fit` sees only
those training rows' features and labels, never a test row, a date or a ticker.

**Labels are handed in, not imported.** `baselines` may import `harness` and `universe` and not `targets`
(docs/modules.json), so the caller passes `labels_for(horizon)`, `neonrain.targets.labels` with the market bound in,
and the same `min_tickers` it used. Pure apart from what the caller's functions do (HAR-11).

**Progress (TODO 3.2 b).** `evaluate` takes an optional `progress`, called as `progress(horizon, fold, folds)` once
each time a (horizon, fold) is done, so a run of hours can say it is alive. It is told nothing of the data and changes
no number; left out, nothing is called.
"""
from collections.abc import Callable
from typing import NamedTuple, Protocol

import numpy as np
import polars as pl

from neonrain.harness import metrics, portfolio, split
from neonrain.harness.market import Market, check_market
from neonrain.universe import periods

KEYS = ["ticker", "date"]
PERIOD_NAMES = (periods.SURVIVOR_ONLY, periods.FROM_BOUNDARY)
GEOMETRY = {"embargo": split.EMBARGO, "step": split.STEP, "min_train": split.MIN_TRAIN}
GROUP_SEED = 0  # HAR-05's default seed
LEVELS = sorted({*portfolio.COST_LEVELS_BPS, portfolio.DEFAULT_COST_BPS})


class Progress(Protocol):
    """Told after each (horizon, fold) of a run is done: the horizon, the fold's number and how many folds there are."""

    def __call__(self, horizon: int, fold: int, folds: int) -> None: ...


class Labelled(Protocol):
    """What the runner reads of `neonrain.targets.Labels` (HAR-02): the frame and its four counts."""

    frame: pl.DataFrame
    dropped_missing: int
    dropped_ties: int
    dropped_thin_dates: int
    delisting_ends: int


class Scorer(Protocol):
    """A fitted model: the features of some rows (the run's columns, sorted by name) to one score each, in [0, 1]."""

    def __call__(self, features: pl.DataFrame) -> np.ndarray: ...


class Fit(Protocol):
    """A model baseline: the training rows' features (the run's columns, sorted by name) and their direction labels
    (1 up, 0 down) to a fitted `Scorer`. Given the same rows it must give the same scores (HAR-01)."""

    def __call__(self, features: pl.DataFrame, direction: np.ndarray) -> Scorer: ...


class Run(NamedTuple):
    """What a run is, apart from its data: all of it goes into the config hash (HAR-01)."""

    name: str
    feature_columns: list[str]
    data_manifest: dict[str, str]
    geometry: dict[str, int | None] = {**GEOMETRY, "window": None}
    group_seed: int = GROUP_SEED
    groups: int = split.GROUPS
    min_tickers: int = metrics.MIN_TICKERS
    horizons: tuple[int, ...] = split.HORIZONS
    hyperparameters: dict[str, object] = {}


class Cell(NamedTuple):
    """One (fold, group) cell in one period: the held-out group's test rows, scored."""

    fold: int
    group: int
    test_rows: int
    accuracy: float | None
    balanced_accuracy: float | None
    ic: metrics.IC
    nets: dict[float, np.ndarray]  # the after-cost daily series at each of LEVELS


class Horizon(NamedTuple):
    """One horizon: its label counts (whole sample, HAR-02) and its cells in each period."""

    horizon: int
    found: Labelled
    cells: dict[str, list[Cell]]


# Decision: R-026 (a period selects the test dates of HAR-03's folds, laid on the whole calendar)
def in_period(period: str) -> pl.Expr:
    """Whether a row's date falls in `period`: before periods.BOUNDARY, or on it and after."""
    before = pl.col("date") < periods.BOUNDARY
    return before if period == periods.SURVIVOR_ONLY else ~before


def scored_market(prices: pl.DataFrame, universe: pl.DataFrame, calendar: list, scores: pl.DataFrame) -> Market:
    """The harness's Market with the score as its one feature, stamped; refused (HAR-12) if the layout or a stamp is wrong."""
    if list(scores.columns) != [*KEYS, "score", "stamp"]:
        raise ValueError(f"the score frame has columns {scores.columns}, expected ticker, date, score, stamp")
    if scores["score"].null_count() or scores["score"].is_nan().any():
        raise ValueError("the score frame has a null or NaN score: a cell without a score is left out of it")
    market = Market(prices, universe, scores.rename({"stamp": "score_stamp"}), calendar)
    check_market(market)
    return market


def window_prices(prices: pl.DataFrame, calendar: list, fold: split.Fold, horizon: int) -> pl.DataFrame:
    """The prices a fold's portfolios read: the test span and `horizon` dates past it, where the last sleeves end."""
    last = min(fold.test_end + horizon, len(calendar) - 1)
    return prices.filter(pl.col("date").is_between(calendar[fold.test_start], calendar[last]))


# Decision: R-021 (a cell's portfolio is scored on every row of its test span that has a score, at all three costs)
def make_cell(fold: int, group: int, test: pl.DataFrame, tested: pl.DataFrame, prices: pl.DataFrame,
              calendar: list, run: Run, horizon: int) -> Cell:
    """HAR-07's metrics on one held-out group's test rows `test` (labelled) and `tested` (every scored row)."""
    nets = {bps: portfolio.daily(tested, prices, calendar, horizon, bps)["net"].to_numpy() for bps in LEVELS}
    ic = metrics.information_coefficient(test.select("date", "score", "rank"), run.min_tickers)
    return Cell(fold, group, test.height, metrics.accuracy(test), metrics.balanced_accuracy(test), ic, nets)


def period_cells(fold: split.Fold, test: pl.DataFrame, tested: pl.DataFrame, prices: pl.DataFrame,
                 groups: dict[str, int], calendar: list, run: Run, horizon: int) -> list[Cell]:
    """The cells of one fold within one period: one per group that has a scored row on the period's test dates."""
    found = []
    for group in range(run.groups):
        held = [name for name, number in groups.items() if number == group]
        mine = tested.filter(pl.col("ticker").is_in(held))
        if mine.height:
            found.append(make_cell(fold.number, group, test.filter(pl.col("ticker").is_in(held)), mine,
                                   prices.filter(pl.col("ticker").is_in(held)), calendar, run, horizon))
    return found


def fixed_rows(market: Market, found: Labelled) -> Callable[[split.Fold], tuple[pl.DataFrame, pl.DataFrame]]:
    """A fold's test rows (labelled and scored) and every scored row of its test span, from the market's score frame."""
    scores = market.features.select(*KEYS, "score")
    rows = found.frame.join(scores, on=KEYS)
    return lambda fold: (split.testing(rows, fold, market.calendar), split.testing(scores, fold, market.calendar))


# Decision: HAR-05 (a model is trained on the fold's purged rows of the other groups and scores the held-out group)
def fitted_scores(features: pl.DataFrame, labelled: pl.DataFrame, groups: dict[str, int], run: Run, horizon: int,
                  fold: split.Fold, calendar: list, fit: Fit) -> pl.DataFrame:
    """ticker, date, score for the fold's test span: each group scored by a model fitted on `split.cell`'s training
    rows (the other groups', purged for `horizon`). A group with no feature row in the span is not fitted."""
    names = sorted(run.feature_columns)
    test = split.testing(features, fold, calendar)
    found = []
    for group in range(run.groups):
        mine = test.filter(pl.col("ticker").is_in([name for name, number in groups.items() if number == group]))
        if mine.height:
            train, _ = split.cell(labelled, fold, calendar, horizon, groups, group)
            score = fit(train.select(names), train["direction"].to_numpy())(mine.select(names))
            if score.shape != (mine.height,) or not (score >= 0.0).all() or not (score <= 1.0).all():
                raise ValueError(f"fold {fold.number}, group {group}: the scores are not one per row in [0, 1]")
            found.append(mine.select(KEYS).with_columns(score=pl.Series(score, dtype=pl.Float64)))
    empty = pl.DataFrame(schema={"ticker": pl.String, "date": pl.Date, "score": pl.Float64})
    return pl.concat([empty, *found]).sort(KEYS)


def fitted_rows(market: Market, found: Labelled, groups: dict[str, int], run: Run, horizon: int,
                fit: Fit) -> Callable[[split.Fold], tuple[pl.DataFrame, pl.DataFrame]]:
    """A fold's test rows and scored rows, scored by the models `fit` gives, one per group, as `fitted_scores`."""
    features = market.features.select(*KEYS, *sorted(run.feature_columns))
    labelled = found.frame.filter(pl.col("direction").is_not_null()).select(*KEYS, "direction").join(features, on=KEYS)

    def rows(fold: split.Fold) -> tuple[pl.DataFrame, pl.DataFrame]:
        tested = fitted_scores(features, labelled, groups, run, horizon, fold, market.calendar, fit)
        return split.testing(found.frame, fold, market.calendar).join(tested, on=KEYS).sort(KEYS), tested
    return rows


def evaluate_horizon(market: Market, found: Labelled, groups: dict[str, int], run: Run, horizon: int,
                     fit: Fit | None = None, progress: Progress | None = None) -> Horizon:
    """One horizon's grid: every fold of HAR-03, in each period, by every held-out group of HAR-05."""
    rows_of = fixed_rows(market, found) if fit is None else fitted_rows(market, found, groups, run, horizon, fit)
    cells: dict[str, list[Cell]] = {period: [] for period in PERIOD_NAMES}
    every = split.folds(len(market.calendar), **run.geometry)  # type: ignore[arg-type]
    for fold in every:
        test, tested = rows_of(fold)
        prices = window_prices(market.prices, market.calendar, fold, horizon)
        for period in PERIOD_NAMES:
            there = in_period(period)
            cells[period] += period_cells(fold, test.filter(there), tested.filter(there), prices, groups,
                                          market.calendar, run, horizon)
        if progress is not None:
            progress(horizon, fold.number, len(every))
    return Horizon(horizon, found, cells)


def ticker_groups(market: Market, run: Run) -> dict[str, int]:
    """HAR-05's ticker groups of the run's market: the same for every horizon of the run."""
    return split.ticker_groups(market.features["ticker"].unique().to_list(), run.groups, run.group_seed)


def evaluate(market: Market, labels_for: Callable[[int], Labelled], run: Run, fit: Fit | None = None,
             progress: Progress | None = None) -> dict[int, Horizon]:
    """The run's grid at each of its horizons; `market.features` is the score frame (`scored_market`), or with a `fit`
    the feature table, each model's scores made per cell. `progress`, if given, is called after each (horizon, fold)."""
    groups = ticker_groups(market, run)
    return {h: evaluate_horizon(market, labels_for(h), groups, run, h, fit, progress) for h in run.horizons}


def scalar_metrics() -> dict[str, Callable[[Cell], float | None]]:
    """Each metric a cell reports by its trials-file name, as a function of the cell: accuracy, balanced accuracy,
    the IC's mean and the Sharpe at each cost level (DSR needs the trial count and is made in `record`)."""
    found: dict[str, Callable[[Cell], float | None]] = {
        "accuracy": lambda c: c.accuracy, "balanced_accuracy": lambda c: c.balanced_accuracy, "IC": lambda c: c.ic.mean}
    for bps in portfolio.COST_LEVELS_BPS:
        found[f"Sharpe_{int(bps)}bps"] = lambda c, b=bps: metrics.sharpe(c.nets[b])  # type: ignore[misc]
    return found
