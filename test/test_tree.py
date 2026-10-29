"""The tree baseline and the runner's per-cell fit (TODO 3.2 a) on the synthetic market, never real data: that a model
sees only its cell's training rows, that a repeat gives the same scores, the score's range, the hyperparameters in the
config hash, and that a run leaves its lines. Trials go to temporary files only (HAR-09)."""
from collections.abc import Callable
from datetime import date
from functools import partial
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from neonrain import targets
from neonrain.baselines import record, runner, tree
from neonrain.harness import split, synthetic
from neonrain.universe import periods

GEOMETRY = {"embargo": 63, "step": 40, "min_train": 100, "window": None}
HORIZON = 3
SMALL = {**tree.HYPERPARAMETERS, "min_data_in_leaf": 20, tree.ROUNDS: 20, "num_threads": 2}
KEYS = ["ticker", "date"]


def run_of(hyperparameters: dict[str, object]) -> runner.Run:
    return runner.Run("tree", ["edge"], {"synthetic": "seed-3"}, GEOMETRY, min_tickers=5, horizons=(HORIZON,),
                      hyperparameters=hyperparameters)  # type: ignore[arg-type]


def evaluated(market: synthetic.Market, fit: runner.Fit, run: runner.Run) -> dict[int, runner.Horizon]:
    labels_for = partial(targets.labels, market.prices, market.universe, market.calendar, min_tickers=run.min_tickers)
    return runner.evaluate(market, labels_for, run, fit)


def encoded(market: synthetic.Market) -> synthetic.Market:
    """The market whose one feature, `edge`, says where its row is: position on the calendar plus ticker number / 100,
    so a fit that is shown a row can be told which row it was (the model sees no date and no ticker, only this)."""
    places = {d: i for i, d in enumerate(market.calendar)}
    names = {t: i for i, t in enumerate(sorted(market.features["ticker"].unique()))}
    edge = [places[d] + names[t] / 100.0 for t, d in zip(market.features["ticker"], market.features["date"])]
    return market._replace(features=market.features.with_columns(edge=pl.Series(edge, dtype=pl.Float64)))


def decode(frame: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """The calendar position and the ticker number of each row of an encoded frame."""
    edge = frame["edge"].to_numpy()
    where = np.floor(edge + 1e-6)
    return where, np.round((edge - where) * 100.0)


class Recorder:
    """A Fit that records what it was shown, and scores 0.5 for every row."""

    def __init__(self) -> None:
        self.trained: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
        self.scored: list[tuple[np.ndarray, np.ndarray]] = []

    def __call__(self, features: pl.DataFrame, direction: np.ndarray) -> runner.Scorer:
        where, who = decode(features)
        self.trained.append((where, who, direction))

        def score(rows: pl.DataFrame) -> np.ndarray:
            self.scored.append(decode(rows))
            return np.full(rows.height, 0.5)
        return score


@pytest.fixture(scope="module")
def market() -> synthetic.Market:
    """Built in a fixture, not at import (J-074)."""
    return synthetic.generate(synthetic.MarketConfig(tickers=60, days=290, rho=0.3, delist_below=0.5, seed=3))


def grid(market: synthetic.Market, fit: runner.Fit) -> tuple[list[split.Fold], dict[str, int], list[pl.DataFrame]]:
    """The fold, the groups, and each fold's scored test rows from `runner.fitted_rows`: models, no portfolios."""
    run = run_of({})
    found = targets.labels(market.prices, market.universe, market.calendar, HORIZON, min_tickers=run.min_tickers)
    groups = split.ticker_groups(market.features["ticker"].unique().to_list(), run.groups, run.group_seed)
    rows = runner.fitted_rows(market, found, groups, run, HORIZON, fit)
    folds = split.folds(len(market.calendar), **{k: GEOMETRY[k] for k in ("embargo", "step", "min_train")})  # type: ignore[arg-type]
    return folds, groups, [rows(fold)[1] for fold in folds]


@pytest.fixture(scope="module")
def seen(market: synthetic.Market) -> Recorder:
    recorder = Recorder()
    grid(encoded(market), recorder)
    return recorder


@pytest.fixture(scope="module")
def parts(market: synthetic.Market) -> dict[int, runner.Horizon]:
    return evaluated(market, partial(tree.fit, hyperparameters=SMALL), run_of(SMALL))


def test_a_model_is_fitted_for_each_fold_and_group_on_the_other_groups_purged_rows(market: synthetic.Market,
                                                                                  seen: Recorder) -> None:
    """One fold (train ends 163, test 226 to 266) by five groups; the rows shown are those of `split.cell`, counted by hand."""
    folds = split.folds(len(market.calendar), **{k: GEOMETRY[k] for k in ("embargo", "step", "min_train")})  # type: ignore[arg-type]
    assert len(folds) == 1 and len(seen.trained) == 5 and len(seen.scored) == 5
    labels = targets.labels(market.prices, market.universe, market.calendar, HORIZON, min_tickers=5).frame
    names = {t: i for i, t in enumerate(sorted(market.features["ticker"].unique()))}
    groups = split.ticker_groups(list(names), 5, 0)
    places = {d: i for i, d in enumerate(market.calendar)}
    kept = labels.filter(pl.col("direction").is_not_null())
    for call, ((where, who, direction), (test_where, test_who)) in enumerate(zip(seen.trained, seen.scored)):
        fold, group = folds[call // 5], groups[sorted(names)[int(test_who[0])]]
        assert {groups[sorted(names)[int(i)]] for i in test_who} == {group}  # one held-out group is scored
        assert group not in {groups[sorted(names)[int(i)]] for i in who}  # and none of its rows are trained on
        assert where.min() >= fold.train_start and where.max() + HORIZON < fold.train_end  # purged: label ends before b
        assert test_where.min() >= fold.test_start and test_where.max() < fold.test_end  # the test span only
        want = kept.filter(pl.col("ticker").replace_strict(groups) != group)
        want = want.filter(pl.col("date").replace_strict(places).is_between(fold.train_start, fold.train_end - HORIZON - 1))
        assert len(direction) == want.height and direction.sum() == want["direction"].sum()
        assert set(direction.tolist()) == {0, 1}


def test_a_model_is_scored_on_every_feature_row_of_its_groups_test_span(market: synthetic.Market, seen: Recorder) -> None:
    """Every feature row of the span, labelled or not, is scored once: the 5 calls cover each exactly once."""
    spans = [(226, 266)]
    want = sum(1 for d in market.features["date"] if any(a <= market.calendar.index(d) < b for a, b in spans))
    assert sum(len(w) for w, _ in seen.scored) == want


def test_the_same_data_gives_the_same_scores(market: synthetic.Market) -> None:
    rng = np.random.default_rng(1)
    x = pl.DataFrame({"a": rng.random(2000), "b": rng.random(2000)})
    y = (x["a"].to_numpy() + 0.3 * rng.standard_normal(2000) > 0.5).astype(int)
    first, second = tree.fit(x, y, SMALL)(x), tree.fit(x, y, SMALL)(x)
    assert np.array_equal(first, second) and len(set(first.tolist())) > 10
    plain = partial(tree.fit, hyperparameters=SMALL)
    once, twice = grid(market, plain)[2], grid(market, plain)[2]
    assert all(a.equals(b) for a, b in zip(once, twice)) and once[0].columns == ["ticker", "date", "score"]
    assert once[0].height > 0 and once[0]["score"].n_unique() > 100


def test_the_score_is_a_probability_that_follows_the_label() -> None:
    """In (0, 1), above 0.5 where the feature predicts an up label; a null feature is a missing value, not a refusal."""
    rng = np.random.default_rng(2)
    values = rng.random(4000)
    x, y = pl.DataFrame({"a": values}), (values > 0.5).astype(int)
    got = tree.fit(x, y, SMALL)(pl.DataFrame({"a": [0.05, 0.95, None]}))
    assert got.shape == (3,) and np.all((got > 0) & (got < 1))
    assert got[0] < 0.5 < got[1]


def test_the_runner_takes_only_scores_in_zero_one_one_to_a_row(market: synthetic.Market) -> None:
    wrong = (lambda n: np.full(n, 1.5), lambda n: np.full(n, -0.1), lambda n: np.full(n, np.nan),
             lambda n: np.full(3, 0.5), lambda n: np.full(n + 1, 0.5))
    for bad in wrong:
        def fit(features: pl.DataFrame, direction: np.ndarray, bad: Callable[[int], np.ndarray] = bad) -> runner.Scorer:
            return lambda rows: bad(rows.height)
        with pytest.raises(ValueError, match="^fold 0, group 0: the scores are not one per row in"):
            grid(market, fit)


def test_scores_are_taken_as_float64_and_a_fold_with_no_test_row_is_an_empty_frame(market: synthetic.Market) -> None:
    got = grid(market, lambda features, direction: lambda rows: np.full(rows.height, 0.25, dtype=np.float32))[2][0]
    assert got.schema == {"ticker": pl.String, "date": pl.Date, "score": pl.Float64} and got.height > 0
    run = run_of({})
    found = targets.labels(market.prices, market.universe, market.calendar, HORIZON, min_tickers=run.min_tickers)
    groups = split.ticker_groups(market.features["ticker"].unique().to_list(), run.groups, run.group_seed)
    none = runner.fitted_scores(market.features, found.frame, groups, run, HORIZON, split.Fold(0, 0, 100, 5000, 5040),
                                market.calendar, lambda features, direction: lambda rows: np.zeros(rows.height))
    assert none.height == 0 and none.schema == got.schema


def test_the_number_of_rounds_is_the_hyperparameters() -> None:
    """One round of 31 leaves at most; 20 rounds many more distinct scores."""
    rng = np.random.default_rng(3)
    x = pl.DataFrame({"a": rng.random(3000), "b": rng.random(3000)})
    y = (x["a"].to_numpy() + 0.5 * rng.standard_normal(3000) > 0.5).astype(int)
    assert len(set(tree.fit(x, y, {**SMALL, tree.ROUNDS: 1})(x).tolist())) <= 31
    assert len(set(tree.fit(x, y, SMALL)(x).tolist())) > 100


def test_scores_of_zero_and_one_are_taken(market: synthetic.Market) -> None:
    for edge in (0.0, 1.0):
        fit = lambda features, direction, edge=edge: lambda rows: np.full(rows.height, edge)  # noqa: E731
        assert set(grid(market, fit)[2][0]["score"].to_list()) == {edge}


def test_the_hyperparameters_are_the_proposed_set() -> None:
    assert tree.HYPERPARAMETERS == {
        "objective": "binary", "learning_rate": 0.05, "num_boost_round": 200, "num_leaves": 31, "min_data_in_leaf": 1000,
        "feature_fraction": 0.8, "bagging_fraction": 0.5, "bagging_freq": 1, "lambda_l2": 10.0, "seed": 0,
        "deterministic": True, "force_row_wise": True, "num_threads": 4, "verbose": -1}
    assert tree.NAME == "tree" and tree.ROUNDS == "num_boost_round"
    copy = dict(SMALL)
    tree.fit(pl.DataFrame({"a": [0.0, 1.0] * 50}), np.array([0, 1] * 50), copy)
    assert copy == SMALL  # a fit leaves the set it was given as it was


def test_the_config_hash_carries_the_hyperparameters() -> None:
    base = record.config_hash(run_of(SMALL), periods.SURVIVOR_ONLY)
    assert base == record.config_hash(run_of(dict(reversed(SMALL.items()))), periods.SURVIVOR_ONLY)
    assert base != record.config_hash(run_of({**SMALL, "learning_rate": 0.06}), periods.SURVIVOR_ONLY)
    assert base != record.config_hash(run_of({**SMALL, "num_threads": 3}), periods.SURVIVOR_ONLY)
    assert base != record.config_hash(run_of({}), periods.SURVIVOR_ONLY)


def test_a_run_of_the_tree_leaves_its_lines(parts: dict[int, runner.Horizon], tmp_path: Path) -> None:
    cells = [c for cs in parts[HORIZON].cells.values() for c in cs]
    assert cells and all(c.ic.dates > 0 for c in cells) and sum(c.accuracy > 0.5 for c in cells) > len(cells) / 2
    path = tmp_path / "trials.tsv"
    written = record.record(path, date(2026, 10, 29), run_of(SMALL), parts)
    assert len(written) == 14 and {w.metric for w in written} >= {"IC", "DSR", "accuracy"}
    rows = [r.split("\t") for r in path.read_text().splitlines()[1:]]
    assert len(rows) == 14 and "CONFLICT" not in path.read_text()
    assert {r[0] for r in rows} == {record.config_hash(run_of(SMALL), p) for p in runner.PERIOD_NAMES}
