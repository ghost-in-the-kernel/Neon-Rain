"""The tree baseline (R-007 d, TODO 3.2 a): a LightGBM classifier of the direction label, one fitted per grid cell.

**The score** is the model's probability that the cell's direction label is 1 (an excess return above the day's
universe median), in (0, 1): HAR-07 reads a score above 0.5 as a predicted up and ranks by it, so it needs no
rescaling. The runner (`neonrain.baselines.runner`) hands `fit` the training rows of one cell (HAR-05, purged
by HAR-03) as a frame of feature columns and their direction labels, and the fitted `Scorer` the features of the
held-out group's test rows; this module sees no date, no ticker and no label of a test row. Tied rows have no
direction and are left out of training by the runner. A null feature is a missing value to LightGBM, which learns
which branch it takes; it is no row dropped.

**One configuration, fixed, no search** (HAR-09): `HYPERPARAMETERS` is the whole set, carried in the config hash's
`model.hyperparameters` (HAR-01), so a change is a different run, and a search would be trials counted as such. There is
no validation set and no early stopping: the number of rounds is one of the hyperparameters.

**Deterministic** (HAR-01: two runs with one hash give identical numbers). A fixed `seed` (which LightGBM spreads to
its bagging, feature-fraction and data seeds), `deterministic` and `force_row_wise`, and a fixed `num_threads`, since the
order in which threads add up a histogram changes the last bits of a sum; the thread count is in the hash for that
reason, and four threads run on a box with fewer cores. Pure apart from LightGBM's own work (HAR-11).
"""
from collections.abc import Callable

import lightgbm as lgb
import numpy as np
import polars as pl

Scorer = Callable[[pl.DataFrame], np.ndarray]

NAME = "tree"
ROUNDS = "num_boost_round"
# Decision: R-034 (the set, chosen blind and fixed: no validation set, no early stopping, no search)
HYPERPARAMETERS: dict[str, object] = {
    "objective": "binary", "learning_rate": 0.05, ROUNDS: 200, "num_leaves": 31, "min_data_in_leaf": 1000,
    "feature_fraction": 0.8, "bagging_fraction": 0.5, "bagging_freq": 1, "lambda_l2": 10.0,
    "seed": 0, "deterministic": True, "force_row_wise": True, "num_threads": 4, "verbose": -1,
}


def fit(features: pl.DataFrame, direction: np.ndarray, hyperparameters: dict[str, object] = HYPERPARAMETERS) -> Scorer:
    """A booster fitted on `features` (Float64 columns, nulls allowed) and `direction` (1 up, 0 down); the scorer it
    gives returns one probability per row of a frame of the same columns, in the frame's row order."""
    params = dict(hyperparameters)
    rounds = int(params.pop(ROUNDS))  # type: ignore[call-overload]
    booster = lgb.train(params, lgb.Dataset(features.to_numpy(), label=direction), num_boost_round=rounds)
    return lambda rows: booster.predict(rows.to_numpy())
