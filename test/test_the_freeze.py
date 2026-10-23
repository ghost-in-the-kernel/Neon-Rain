"""TODO 1.7 (HAR-14, HAR-13): the goldens, what writes them, and what catches a harness change that moves one.

This file is named to sort after the unit tests of the harness: mutmut tries a mutant against the tests in file order,
and these are the slow ones. What holds the goldens (writing, checking, a decision in force) is test_golden_files.py. The harness itself is tried on the synthetic market of
goldens.MARKET, computed once for the module; `harness/goldens/` is compared to it when the directory exists.
"""
import json
from pathlib import Path

import polars as pl
import pytest

from neonrain import targets
from neonrain.harness import dispersion, goldens, metrics, portfolio, split, synthetic, trials
from neonrain.harness.market import Market

GHOST = (
    "### R-002: One\n- **Status:** in force\n\n"
    "### R-003: Two\n- **Status:** proposed\n\n"
    "### R-004: Three\n- **Status:** superseded by R-005\n\n"
    "### R-020: Four\n- **Status:** in force\n"
)
SMALL = synthetic.MarketConfig(tickers=40, days=330, rho=0.1, delist_below=0.5, seed=1)
MID = synthetic.MarketConfig(tickers=120, days=330, rho=0.1, delist_below=0.5, seed=1)


COMPUTED: dict[str, dict[str, str]] = {}


@pytest.fixture
def computed() -> dict[str, str]:
    """The goldens of goldens.MARKET, computed once: by the test below, or by whichever test needs them first."""
    if "market" not in COMPUTED:
        COMPUTED["market"] = goldens.compute()
    return COMPUTED["market"]


# --- The pieces ------------------------------------------------------------------------------------------------------


def edges(values: list[float], days: list[str] | None = None) -> Market:
    """A market whose features hold only ticker, date and edge: tickers A, B, ... on each given date."""
    days = days or ["2000-01-03"]
    rows = [(chr(65 + i), pl.Series([day]).str.to_date()[0], v) for day in days for i, v in enumerate(values)]
    features = pl.DataFrame(rows, schema={"ticker": pl.String, "date": pl.Date, "edge": pl.Float64}, orient="row")
    return Market(features, features, features, [])


def test_a_score_is_the_edges_rank_fraction_among_the_dates_tickers() -> None:
    scored = goldens.edge_scores(edges([1.0, 3.0, 2.0, 5.0], ["2000-01-03", "2000-01-04"]))
    assert scored.columns == ["ticker", "date", "score"]
    assert scored["score"].to_list() == [0.0, 2 / 3, 1 / 3, 1.0] * 2


def test_tied_edges_share_the_average_rank_and_a_lone_ticker_scores_zero() -> None:
    assert goldens.edge_scores(edges([1.0, 1.0, 2.0]))["score"].to_list() == [0.25, 0.25, 1.0]
    assert goldens.edge_scores(edges([7.0]))["score"].to_list() == [0.0]


def test_a_date_of_two_tickers_scores_zero_and_one() -> None:
    assert goldens.edge_scores(edges([4.0, 9.0]))["score"].to_list() == [0.0, 1.0]


def test_a_single_cell_still_gives_its_metrics() -> None:
    assert goldens.metric_values(CELLS[:1]) == {"accuracy": {(0, 0): 0.5}, "dsr_1": {(0, 0): None}, "ic": {(0, 0): 0.0}}


def test_the_label_summary_holds_the_counts_and_the_means_of_the_columns() -> None:
    frame = pl.DataFrame({"forward": [0.1, 0.3], "excess": [-1.0, 3.0], "direction": [0, 1], "rank": [0.0, 1.0]})
    assert goldens.label_summary(targets.Labels(frame, 1, 2, 3, 4)) == {
        "rows": 2, "dropped_missing": 1, "dropped_ties": 2, "dropped_thin_dates": 3, "delisting_ends": 4,
        "mean_forward": pytest.approx(0.2), "mean_excess": 1.0, "mean_direction": 0.5, "mean_rank": 0.5}


CELLS = [{"fold": f, "group": g, "train_rows": 9, "test_rows": 9, "accuracy": 0.5 + f / 10 + g / 100, "dsr_1": None,
          "ic": {"mean": float(f + g), "t": 1.0}} for f in (0, 1) for g in (0, 1)]


def test_every_scalar_metric_is_listed_by_cell_and_the_ic_by_its_mean() -> None:
    found = goldens.metric_values(CELLS)
    assert sorted(found) == ["accuracy", "dsr_1", "ic"]
    assert found["accuracy"] == {(0, 0): 0.5, (0, 1): 0.51, (1, 0): 0.6, (1, 1): 0.61}
    assert found["dsr_1"] == {(0, 0): None, (0, 1): None, (1, 0): None, (1, 1): None}
    assert found["ic"] == {(0, 0): 0.0, (0, 1): 1.0, (1, 0): 1.0, (1, 1): 2.0}


def test_the_dispersion_of_each_metric_is_har08s_as_plain_data() -> None:
    found = goldens.dispersions(CELLS)
    assert list(found) == ["accuracy", "dsr_1", "ic"]
    expected = dispersion.dispersion(goldens.metric_values(CELLS)["ic"])
    assert found["ic"] == {"folds": expected.folds._asdict(), "groups": expected.groups._asdict(),
                           "undefined_cells": 0, "fits_names": False}
    assert found["dsr_1"] == {"folds": None, "groups": None, "undefined_cells": 4, "fits_names": False}
    assert found["accuracy"]["folds"] == {
        "mean": pytest.approx(0.555), "sd": pytest.approx(0.0707106781), "low": pytest.approx(0.505),
        "high": pytest.approx(0.605), "count": 2}


def test_a_cell_holds_what_the_harness_gives_for_that_fold_and_group() -> None:
    market = synthetic.generate(MID)
    scored = goldens.edge_scores(market)
    found = targets.labels(market.prices, market.universe, market.calendar, 5)
    rows = found.frame.join(scored, on=goldens.KEYS)
    fold = split.folds(len(market.calendar), **goldens.GEOMETRY)[1]
    cell = goldens.cell_numbers(market, rows, scored, fold, 3, 5)
    groups = split.ticker_groups(market.features["ticker"].unique().to_list(), split.GROUPS, goldens.GROUP_SEED)
    train, test = split.cell(rows, fold, market.calendar, 5, groups, 3)
    held = [name for name, group in groups.items() if group == 3]
    tested = split.testing(scored, fold, market.calendar).filter(pl.col("ticker").is_in(held))
    net = portfolio.daily(tested, market.prices, market.calendar, 5, 25.0)["net"].to_numpy()
    default = portfolio.daily(tested, market.prices, market.calendar, 5, 10.0)["net"].to_numpy()
    assert (cell["fold"], cell["group"]) == (1, 3)
    assert (cell["train_rows"], cell["test_rows"]) == (train.height, test.height)
    assert cell["accuracy"] == metrics.accuracy(test) and cell["balanced_accuracy"] == metrics.balanced_accuracy(test)
    assert cell["ic"] == metrics.information_coefficient(test.select("date", "score", "rank"))._asdict()
    assert cell["sharpe_25bps"] == metrics.sharpe(net)
    assert cell["sharpe_0bps"] != cell["sharpe_10bps"] != cell["sharpe_25bps"]
    assert cell["dsr_1"] == metrics.deflated_sharpe(default, 1, goldens.VARIANCE)
    assert cell["dsr_5"] == metrics.deflated_sharpe(default, 5, goldens.VARIANCE) != cell["dsr_1"]


def test_a_horizons_grid_is_every_fold_by_every_group_in_that_order() -> None:
    market = synthetic.generate(SMALL)
    summary, cells = goldens.horizon_cells(market, goldens.edge_scores(market), 3)
    assert summary["rows"] == targets.labels(market.prices, market.universe, market.calendar, 3).frame.height
    assert [(c["fold"], c["group"]) for c in cells] == [(f, g) for f in (0, 1) for g in range(split.GROUPS)]


# --- The harness on the synthetic market -------------------------------------------------------------------------------


@pytest.mark.slow  # runs the whole harness on HAR-14's market (6 s): before a push, not in the fast loop or mutmut
def test_the_harness_on_the_synthetic_market_gives_these_goldens() -> None:
    found = COMPUTED["market"] = goldens.compute()
    assert_the_goldens_are_these_files(found)
    assert_the_config_hash_golden_is_the_hash_of_the_config_and_the_frozen_version(found)
    assert_the_market_has_delistings_and_only_one_groups_ic_is_undefined(found)
    assert_the_splits_golden_records_the_folds_the_groups_and_the_default_folds(found)
    assert_every_cell_holds_every_metric(found)


def assert_the_goldens_are_these_files(computed: dict[str, str]) -> None:
    assert sorted(computed) == ["config_hash.json", "synthetic_cells.json", "synthetic_dispersion.json",
                                "synthetic_labels.json", "synthetic_splits.json"]
    assert all(text.endswith("\n") for text in computed.values())


def assert_the_config_hash_golden_is_the_hash_of_the_config_and_the_frozen_version(computed: dict[str, str]) -> None:
    found = json.loads(computed["config_hash.json"])
    assert found["harness_version"] == trials.HARNESS_VERSION == "1"
    assert found["hash"] == trials.config_hash(**goldens.CONFIG)  # type: ignore[arg-type]
    assert found["config"]["split"] == {**goldens.GEOMETRY, "window": None, "k": 5, "seed": goldens.GROUP_SEED}
    assert found["config"]["target"]["horizons"] == list(targets.HORIZONS)


def assert_the_market_has_delistings_and_only_one_groups_ic_is_undefined(computed: dict[str, str]) -> None:
    labels = json.loads(computed["synthetic_labels.json"])
    assert sorted(labels, key=int) == ["3", "5", "21", "63"]
    assert all(found["delisting_ends"] > 0 and found["dropped_missing"] == 0 for found in labels.values())
    cells = json.loads(computed["synthetic_cells.json"])
    assert all(len(found) == 2 * split.GROUPS for found in cells.values())
    spread = json.loads(computed["synthetic_dispersion.json"])
    assert sorted(spread, key=int) == ["3", "5", "21", "63"]
    for found in spread.values():
        # one group is too thin on every test date for an IC (HAR-07): two undefined cells, four groups left
        assert {name: metric["undefined_cells"] for name, metric in found.items()} == {
            name: 2 if name == "ic" else 0 for name in found}
        assert [found["ic"]["groups"]["count"], found["ic"]["folds"]["count"]] == [4, 2]
        assert all(metric["groups"]["count"] == 5 for name, metric in found.items() if name != "ic")
        assert all(metric["folds"]["count"] == 2 for metric in found.values())


def assert_the_splits_golden_records_the_folds_the_groups_and_the_default_folds(computed: dict[str, str]) -> None:
    found = json.loads(computed["synthetic_splits.json"])
    assert [fold["train_end"] for fold in found["folds"]] == [163, 203]
    assert found["default_folds"][0] == {"number": 0, "train_start": 0, "train_end": 819, "test_start": 882,
                                          "test_end": 1008}
    assert found["groups"] == split.ticker_groups(synthetic.tickers(150), split.GROUPS, 5)
    assert sorted(set(found["groups"].values())) == list(range(split.GROUPS))


def assert_every_cell_holds_every_metric(computed: dict[str, str]) -> None:
    cell = json.loads(computed["synthetic_cells.json"])["63"][0]
    assert sorted(cell) == ["accuracy", "balanced_accuracy", "dsr_1", "dsr_5", "fold", "group", "ic", "sharpe_0bps",
                            "sharpe_10bps", "sharpe_25bps", "test_rows", "train_rows"]
    assert sorted(cell["ic"]) == ["dates", "dropped_flat", "dropped_thin", "mean", "standard_error", "t"]
    assert (cell["fold"], cell["group"]) == (0, 0) and cell["train_rows"] > cell["test_rows"] > 0


@pytest.mark.slow  # runs the whole harness on HAR-14's market (6 s): before a push, not in the fast loop or mutmut
def test_the_goldens_of_the_repository_are_the_harnesss_output(root: Path, computed: dict[str, str]) -> None:
    directory = root / "harness" / "goldens"
    if not (directory / goldens.INDEX).is_file():
        pytest.xfail("harness/goldens/ is not written: whether a run's output may enter the repository waits on Ghost")
    assert goldens.check(directory, computed, (root / "theGhost.md").read_text()) == []


# --- A harness change that moves a number is caught -------------------------------------------------------------------


def named(found: list[str]) -> list[str]:
    """The golden each line of check names."""
    return [line.split(" differs")[0] for line in found]


@pytest.mark.slow  # runs the whole harness on HAR-14's market (6 s): before a push, not in the fast loop or mutmut
def test_a_broken_metric_is_caught_in_the_cells_and_their_dispersion(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, computed: dict[str, str]) -> None:
    goldens.write(tmp_path, computed, GHOST)
    monkeypatch.setattr(metrics, "accuracy", lambda frame: 0.5)
    assert named(goldens.check(tmp_path, goldens.compute(), GHOST)) == ["synthetic_cells.json",
                                                                          "synthetic_dispersion.json"]


@pytest.fixture(scope="module")
def small() -> dict[str, str]:
    return goldens.compute(SMALL)


@pytest.mark.slow
def test_the_same_config_gives_the_same_texts(small: dict[str, str]) -> None:
    assert goldens.compute(SMALL) == small


@pytest.mark.slow
def test_a_changed_group_count_is_caught_in_the_splits(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, small: dict[str, str]) -> None:
    goldens.write(tmp_path, small, GHOST)
    monkeypatch.setattr(split, "GROUPS", 4)
    assert "synthetic_splits.json" in named(goldens.check(tmp_path, goldens.compute(SMALL), GHOST))


@pytest.mark.slow
def test_a_changed_cost_level_is_caught_in_the_cells(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, small: dict[str, str]) -> None:
    goldens.write(tmp_path, small, GHOST)
    monkeypatch.setattr(portfolio, "COST_LEVELS_BPS", (0.0, 10.0, 30.0))
    assert "synthetic_cells.json" in named(goldens.check(tmp_path, goldens.compute(SMALL), GHOST))
