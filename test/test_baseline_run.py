"""The baseline script's wiring (TODO 3.2 b) on the synthetic market, never real data: the tree's run (its sixteen
feature columns and R-034's hyperparameters), the progress call the runner makes once for each (horizon, fold), the
log's lines, the refusals of the command line, and that the fixed-score baselines come out the same with or without it."""
from datetime import UTC, datetime, timedelta, timezone
from functools import partial
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from neonrain import targets
from neonrain.baselines import runner, tree, zero
from neonrain.harness import split, synthetic
from neonrain.universe import prices, verified
from scripts import baseline_run
from scripts.fetch import feature_table

GEOMETRY = {"embargo": 63, "step": 40, "min_train": 40, "window": None}
CONFIG = synthetic.MarketConfig(tickers=15, days=250, rho=0.1, delist_below=0.5, seed=3)
HORIZONS = (3, 5)
FOLDS = len(split.folds(250, 63, 40, 40))  # the folds of 250 days at this geometry
FEATURES = ["macd", "macd_hist", "mar_21", "mar_5", "mar_63", "ret_21", "ret_3", "ret_5", "ret_63", "rsi_14", "vol_21",
            "vol_5", "vol_63", "volr_21", "volr_5", "volr_63"]
MANIFEST = (baseline_run.ROOT / "data" / "MANIFEST.md").read_text()


class Calls:
    """A `runner.Progress` that keeps what it is told."""

    def __init__(self) -> None:
        self.told: list[tuple[int, int, int]] = []

    def __call__(self, horizon: int, fold: int, folds: int) -> None:
        self.told.append((horizon, fold, folds))


def constant(features: pl.DataFrame, direction: np.ndarray) -> runner.Scorer:
    """A Fit that scores one half everywhere: the grid is run, no model is."""
    return lambda rows: np.full(rows.height, 0.5)


def run_of(columns: list[str], horizons: tuple[int, ...]) -> runner.Run:
    return runner.Run("zero", columns, {"synthetic": "seed-3"}, GEOMETRY, min_tickers=5, horizons=horizons, groups=2)  # type: ignore[arg-type]


@pytest.fixture(scope="module")
def market() -> synthetic.Market:
    """Built in a fixture, not at import (J-074)."""
    return synthetic.generate(CONFIG)


def labels_for(market: synthetic.Market, run: runner.Run) -> partial:  # type: ignore[type-arg]
    return partial(targets.labels, market.prices, market.universe, market.calendar, min_tickers=run.min_tickers)


@pytest.fixture(scope="module")
def fixed(market: synthetic.Market) -> tuple[dict[int, runner.Horizon], dict[int, runner.Horizon], Calls]:
    """The zero baseline without a progress call and with one."""
    run = run_of([], (3,))
    scored = runner.scored_market(market.prices, market.universe, market.calendar, zero.scores(market.universe))
    calls = Calls()
    return (runner.evaluate(scored, labels_for(market, run), run),
            runner.evaluate(scored, labels_for(market, run), run, progress=calls), calls)


@pytest.fixture(scope="module")
def fitted(market: synthetic.Market) -> Calls:
    """A fitted baseline (a constant model) over the same grid, with a progress call."""
    run = run_of(["edge"], HORIZONS)
    calls = Calls()
    runner.evaluate(market, labels_for(market, run), run, constant, calls)
    return calls


def test_the_tree_run_has_the_sixteen_features_and_the_set_of_r_034() -> None:
    run = baseline_run.tree_run(MANIFEST)
    assert run.name == "tree" and run.feature_columns == FEATURES == feature_table.feature_names()
    assert run.hyperparameters == tree.HYPERPARAMETERS
    assert run.data_manifest == {prices.DATASET: verified.manifest_hash(MANIFEST, prices.DATASET),
                                 feature_table.DATASET: verified.manifest_hash(MANIFEST, feature_table.DATASET)}
    assert run.horizons == (3, 5, 21, 63) and run.groups == 5  # the harness's, as for the other baselines


def test_the_tree_is_named_apart_from_the_fixed_score_baselines() -> None:
    assert baseline_run.FITTED == "tree" and baseline_run.FITTED not in baseline_run.BASELINES
    assert list(baseline_run.BASELINES) == ["zero", "momentum", "reversal"]
    assert "tree <neon-rain-data clone> <YYYY-MM-DD> <progress log>" in baseline_run.__doc__  # the usage line is true


def test_progress_is_told_once_for_each_horizon_and_fold(fixed: tuple, fitted: Calls) -> None:
    assert fitted.told == [(h, f, FOLDS) for h in HORIZONS for f in range(FOLDS)]
    assert fixed[2].told == [(3, f, FOLDS) for f in range(FOLDS)] and FOLDS == 2


def test_a_run_without_progress_and_one_with_it_give_the_same_cells(fixed: tuple) -> None:
    plain, watched, _ = fixed
    assert list(plain) == list(watched) == [3]
    for horizon in (3,):
        for period in runner.PERIOD_NAMES:
            a, b = plain[horizon].cells[period], watched[horizon].cells[period]
            assert len(a) == len(b) and (period != runner.PERIOD_NAMES[0] or a)  # the market lies before the boundary
            for one, two in zip(a, b):
                assert one._replace(nets={}) == two._replace(nets={})
                assert all(np.array_equal(one.nets[k], two.nets[k]) for k in runner.LEVELS)


def test_the_progress_line_has_the_time_horizon_fold_and_seconds() -> None:
    stamp = datetime(2026, 10, 29, 14, 5, 9, 700000, tzinfo=UTC)
    assert baseline_run.progress_line(stamp, 61.6, 21, 0, 12) == "2026-10-29T14:05:09+00:00\thorizon 21\tfold 1 of 12\t62s"
    other = stamp.astimezone(timezone(timedelta(hours=2)))  # the same instant in another zone is written in UTC
    assert baseline_run.progress_line(other, 0, 3, 11, 12).startswith("2026-10-29T14:05:09+00:00\thorizon 3\tfold 12 of 12")


def test_the_log_gets_one_appended_line_for_each_call(tmp_path: Path) -> None:
    log = tmp_path / "run.log"
    log.write_text("earlier\n")
    ticks = iter([(datetime(2026, 10, 29, 1, 0, tzinfo=UTC), 110.0), (datetime(2026, 10, 29, 1, 1, tzinfo=UTC), 170.0)])
    write = baseline_run.progress_log(log, 100.0, lambda: next(ticks))
    write(3, 0, 2)
    assert log.read_text().splitlines() == ["earlier", "2026-10-29T01:00:00+00:00\thorizon 3\tfold 1 of 2\t10s"]
    write(3, 1, 2)
    assert log.read_text().splitlines()[2] == "2026-10-29T01:01:00+00:00\thorizon 3\tfold 2 of 2\t70s"


def test_a_log_inside_the_repository_is_not_outside(tmp_path: Path) -> None:
    root = baseline_run.ROOT
    assert not baseline_run.log_outside(root / "run.log") and not baseline_run.log_outside(root / "harness" / "x.log")
    assert not baseline_run.log_outside(root / "scripts" / ".." / "run.log")
    assert baseline_run.log_outside(tmp_path / "run.log") and baseline_run.log_outside(root.parent / "run.log")


def test_the_command_line_refuses_misuse_before_it_reads_anything(tmp_path: Path) -> None:
    clone, day = str(tmp_path / "no-clone"), "2026-10-29"
    for argv in ([], ["nothing", clone, day], ["zero", clone], ["zero", clone, day, str(tmp_path / "x.log")],
                 ["tree", clone, day], ["tree", clone, day, str(tmp_path / "x.log"), "extra"]):
        assert baseline_run.main(argv) == 2
    inside = baseline_run.ROOT / "tree-progress-test.log"
    assert baseline_run.main(["tree", clone, day, str(inside)]) == 2 and not inside.exists()


def test_the_feature_market_is_the_feature_table_cut_to_the_sessions(market: synthetic.Market) -> None:
    days = market.calendar[10:-10]
    within = pl.col("date").is_between(days[0], days[-1])
    built = baseline_run.feature_market(market.prices.filter(within), market.universe.filter(within), days, market.features)
    assert built.features.select(runner.KEYS).equals(market.features.filter(within).select(runner.KEYS))
    assert built.calendar == days and built.features.height < market.features.height


def test_a_feature_table_of_other_cells_than_the_universes_is_refused(market: synthetic.Market) -> None:
    """The stored table's universe must be the run's: a join on (ticker, date) would drop the difference unseen."""
    with pytest.raises(ValueError, match="not the universe's"):
        baseline_run.feature_market(market.prices, market.universe, market.calendar, market.features.slice(1))
    with pytest.raises(ValueError, match="not the universe's"):
        baseline_run.feature_market(market.prices, market.universe.slice(1), market.calendar, market.features)
