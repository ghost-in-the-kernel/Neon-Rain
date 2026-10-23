"""TODO 1.6 (ROADMAP 1.6): the harness attacked with broken inputs, each check red on the break, green on the honest one.

Each test builds the broken input and the honest one on the synthetic market (HAR-10), the only market where the right
answer is known, and asserts that the harness catches the first and passes the second. A model the harness must be
shown to catch (the memorizer) lives here, never under neonrain/models/ (R-002). The mirror test of ROADMAP 1.6
is test/test_mirror.py (HAR-07's metrics against test/mirror_har07.py, written blind, R-015c).
"""
from datetime import date

import numpy as np
import polars as pl
import pytest

from neonrain import targets
from neonrain.harness import dispersion, market, metrics, split, synthetic
from neonrain.harness.market import Market, StampRefused
from neonrain.harness.split import Fold

KEYS = ["ticker", "date"]
CEILING = 0.60  # HAR-12: a direction accuracy at or above this is impossibly high for the planted edges used here
BUCKETS = 8  # the memorizer's hash buckets for names it has not seen


def positions(calendar: list[date]) -> pl.DataFrame:
    """Each date's position on the calendar, as split.positions gives it."""
    return split.positions(calendar)


# --- A feature that peeks one day ahead (HAR-12) ---------------------------------------------------------------


def leak_market() -> Market:
    """60 tickers, 300 days, the strongest honest edge used here (ρ = 0.3: 0.55 accuracy at 3 days)."""
    return synthetic.generate(synthetic.MarketConfig(tickers=60, days=300, rho=0.3, seed=3))


def with_peek(m: Market, lie: bool) -> pl.DataFrame:
    """The market's features plus `peek`: the return to the ticker's next row, which only t+1 knows.

    Its stamp is honestly that next row's date, or with `lie` the cell's own date (a check that cannot tell). On a
    ticker's last row there is no next row: a null value, a null stamp.
    """
    prices = m.prices.sort(KEYS)
    ahead = pl.col("close").shift(-1).over("ticker")
    peek = prices.select(*KEYS, (ahead / pl.col("close") - 1.0).alias("peek"),
                         pl.col("date").shift(-1).over("ticker").alias("peek_stamp"))
    found = m.features.join(peek, on=KEYS)
    return found.with_columns(pl.col("date").alias("peek_stamp")) if lie else found


def directions(m: Market, horizon: int) -> pl.DataFrame:
    """ticker, date, direction of the rows that have a direction label."""
    frame = targets.labels(m.prices, m.universe, m.calendar, horizon, min_tickers=10).frame
    return frame.filter(pl.col("direction").is_not_null()).select(*KEYS, "direction")


def rule_accuracy(features: pl.DataFrame, column: str, labelled: pl.DataFrame, lag: int) -> float:
    """HAR-12's leak check rule: predict 1 where the feature, lagged `lag` rows within its ticker, is in the top half
    of its date (rank fraction above 0.5), and score that against the direction labels."""
    ordered = features.sort(KEYS)
    lagged = ordered.select(*KEYS, pl.col(column).shift(lag).over("ticker").alias("value"))
    rows = lagged.drop_nulls("value").join(labelled, on=KEYS)
    fraction = (pl.col("value").rank().over("date") - 1.0) / (pl.len().over("date") - 1.0)
    found = metrics.accuracy(rows.select((fraction > 0.5).cast(pl.Float64).alias("score"), "direction"))
    assert found is not None
    return found


def leak_flagged(features: pl.DataFrame, column: str, labelled: pl.DataFrame) -> bool:
    """HAR-12's leak check: impossibly accurate (at least CEILING) and at least half its edge gone with a one-day lag."""
    now = rule_accuracy(features, column, labelled, 0)
    lagged = rule_accuracy(features, column, labelled, 1)
    return now >= CEILING and lagged - 0.5 <= (now - 0.5) / 2


def test_the_stamp_check_refuses_a_feature_that_peeks_a_day_ahead() -> None:
    m = leak_market()
    market.check_stamps(m.features)  # honest: the planted edge is known at the close of t
    peeking = with_peek(m, lie=False)
    message = r"feature 'peek' refused at cell \(T000, 2000-01-03\): stamp 2000-01-04 is after the cell's date \(and \d+ more cells\)"
    with pytest.raises(StampRefused, match=message):
        market.check_stamps(peeking)
    with pytest.raises(StampRefused, match="feature 'peek' refused"):
        market.check_market(m._replace(features=peeking))


def test_a_peek_that_slips_past_the_stamp_check_is_caught_by_its_impossible_accuracy() -> None:
    m = leak_market()
    lying = with_peek(m, lie=True)
    market.check_stamps(lying)  # the stamp check is blind to a stamp that lies: this is the second line
    labelled = directions(m, 3)
    assert rule_accuracy(lying, "peek", labelled, 0) > 0.65  # impossibly high; the honest edge is below
    assert rule_accuracy(lying, "edge", labelled, 0) < 0.58
    assert leak_flagged(lying, "peek", labelled)
    assert not leak_flagged(lying, "edge", labelled)


# --- A universe with the delisted names removed (HAR-02, HAR-10) -------------------------------------------------

MARGIN = 0.02  # the inflation of the mean 63-day forward return that counts as caught


def survivorship_market() -> Market:
    """300 tickers over 300 days with the worst performers delisted at 60% of their start price (about 80 of them)."""
    config = synthetic.MarketConfig(tickers=300, days=300, rho=0.0, idio_vol=0.03, delist_below=0.6, seed=0)
    return synthetic.generate(config)


def mean_forward(m: Market, removed: list[str]) -> tuple[float, int]:
    """The mean 63-day forward return over the label cells, and the cells ending in a delisting, with `removed`
    tickers taken out of prices and universe entirely, as a survivors-only source would give them."""
    keep = ~pl.col("ticker").is_in(removed)
    found = targets.labels(m.prices.filter(keep), m.universe.filter(keep), m.calendar, 63, min_tickers=10)
    return float(found.frame["forward"].mean()), found.delisting_ends


def delisted(m: Market) -> list[str]:
    """The tickers whose last price comes before the calendar's last date."""
    last = m.prices.group_by("ticker").agg(pl.col("date").max().alias("last"))
    return sorted(last.filter(pl.col("last") < m.calendar[-1])["ticker"].to_list())


def test_a_universe_without_its_delisted_names_shows_inflated_returns() -> None:
    m = survivorship_market()
    gone = delisted(m)
    honest, honest_ends = mean_forward(m, [])
    assert len(gone) >= 50 and honest_ends > 0  # the market really delists, or this test would prove nothing
    biased, biased_ends = mean_forward(m, gone)
    assert biased - honest > MARGIN  # the inflation
    assert biased_ends == 0  # and HAR-02's own count of delistings falls to zero
    # Control: the same number of tickers taken out at random, from all of them, is no inflation.
    random = [str(t) for t in np.random.default_rng(0).choice(synthetic.tickers(300), size=len(gone), replace=False)]
    shrunk, shrunk_ends = mean_forward(m, random)
    assert abs(shrunk - honest) < MARGIN and shrunk_ends > 0


# --- A label that crosses the embargo (HAR-03, HAR-04) ------------------------------------------------------------

GRID_DAYS = 1140  # two folds with the defaults


def grid_labels(horizon: int) -> tuple[pl.DataFrame, list[date], dict[str, int]]:
    """One horizon's labels on a 40-ticker market long enough for two folds, the calendar and the ticker groups."""
    m = synthetic.generate(synthetic.MarketConfig(tickers=40, days=GRID_DAYS, seed=5))
    frame = targets.labels(m.prices, m.universe, m.calendar, horizon, min_tickers=10).frame
    return frame, m.calendar, split.ticker_groups(synthetic.tickers(40), 5, 0)


def crossing(train: pl.DataFrame, fold: Fold, calendar: list[date], horizon: int) -> int:
    """Training rows whose label window [t, t+h] reaches the embargo (t+h ≥ b) or that lie outside [a, b). Brute force
    on calendar positions, worked without split.py."""
    index = {day: position for position, day in enumerate(calendar)}
    return sum(1 for day in train["date"] if not fold.train_start <= index[day] or index[day] + horizon >= fold.train_end)


def short_embargo(fold: Fold) -> bool:
    """Whether the gap between the training span's end and the test span's start is under 63 trading days (HAR-03)."""
    return fold.test_start - fold.train_end < split.LONGEST


def unpurged(rows: pl.DataFrame, fold: Fold, calendar: list[date]) -> pl.DataFrame:
    """The broken training set: every row dated in [a, b), the purge of HAR-03 left out."""
    at = rows.join(positions(calendar), on="date")
    return at.filter((pl.col("position") >= fold.train_start) & (pl.col("position") < fold.train_end)).drop("position")


@pytest.mark.parametrize("horizon", targets.HORIZONS)
def test_a_training_label_that_reaches_the_embargo_is_caught_and_the_purged_grid_is_clean(horizon: int) -> None:
    rows, calendar, groups = grid_labels(horizon)
    folds = split.folds(len(calendar))
    assert len(folds) == 2
    for fold in folds:
        assert crossing(unpurged(rows, fold, calendar), fold, calendar, horizon) >= horizon * 40  # caught: h dates × tickers
        assert not short_embargo(fold)
        for held_out in range(5):
            train, test = split.cell(rows, fold, calendar, horizon, groups, held_out)
            assert crossing(train, fold, calendar, horizon) == 0
            assert test.height > 0 and set(test["ticker"]).isdisjoint(train["ticker"])


def test_a_fold_with_a_short_embargo_is_caught_and_refused() -> None:
    honest = split.folds(GRID_DAYS)[0]
    short = Fold(0, 0, honest.train_end, honest.train_end + 21, honest.train_end + 21 + 126)
    assert short_embargo(short) and not short_embargo(honest)
    with pytest.raises(ValueError, match="embargo is 21"):
        split.folds(GRID_DAYS, embargo=21)


# --- A model that memorizes a ticker (R-014, HAR-05, HAR-08) -----------------------------------------------------

HORIZON = 5
NAMES = 100
SEEDS = range(6)


def named_rows(seed: int) -> tuple[pl.DataFrame, list[date]]:
    """Labels and the edge on a market where names matter: each ticker gets its own steady drift (sd 0.3% a day, drawn
    from `seed`), which the edge feature knows nothing about, so a table of name → mean return can profit from it."""
    m = synthetic.generate(synthetic.MarketConfig(tickers=NAMES, days=GRID_DAYS, rho=0.3, seed=seed))
    drifts = np.random.default_rng(10_000 + seed).normal(0, 0.003, NAMES)
    drift = pl.DataFrame({"ticker": synthetic.tickers(NAMES), "drift": drifts})
    steady = (pl.col("drift") * pl.col("position")).exp()
    prices = m.prices.join(drift, on="ticker").join(positions(m.calendar), on="date")
    prices = prices.select(*KEYS, (pl.col("close") * steady).alias("close"))
    labels = targets.labels(prices, m.universe, m.calendar, HORIZON, min_tickers=10).frame
    return labels.join(m.features.select(*KEYS, "edge"), on=KEYS), m.calendar


def memorizer(train: pl.DataFrame, test: pl.DataFrame) -> pl.DataFrame:
    """The stand-in model: a lookup table of ticker → mean rank label over the training rows. A ticker it has never
    seen gets the mean of the table entries sharing its hash bucket (the hashing trick), the way a name-keyed model
    of fixed size must answer for a name it holds nothing on."""
    table = dict(train.group_by("ticker").agg(pl.col("rank").mean().alias("mean")).iter_rows())
    bucket = {name: int(name[1:]) % BUCKETS for name in synthetic.tickers(NAMES)}
    shared = {b: float(np.mean([v for t, v in table.items() if bucket[t] == b])) for b in set(bucket.values())}
    return test.with_columns(pl.Series("score", [table.get(t, shared[bucket[t]]) for t in test["ticker"]]))


def linear_edge(train: pl.DataFrame, test: pl.DataFrame) -> pl.DataFrame:
    """The honest stand-in: the least-squares slope of the rank label on the edge, fitted pooled over the training rows."""
    x, y = train["edge"].to_numpy(), train["rank"].to_numpy()
    slope = float(np.cov(x, y)[0, 1] / np.var(x, ddof=1))
    return test.with_columns((pl.col("edge") * slope).alias("score"))


def cell_rows(rows: pl.DataFrame, fold: Fold, calendar: list[date], groups: dict[str, int], held_out: int,
              seen: bool) -> tuple[pl.DataFrame, pl.DataFrame]:
    """One grid cell's training and test rows. With `seen` the broken protocol: every ticker trains, the held-out
    group's too (a time split only); otherwise HAR-05's, the group's tickers held out of training."""
    if not seen:
        return split.cell(rows, fold, calendar, HORIZON, groups, held_out)
    names = [t for t, g in groups.items() if g == held_out]
    return (split.training(rows, fold, calendar, HORIZON),
            split.testing(rows, fold, calendar).filter(pl.col("ticker").is_in(names)))


def grid_ic(rows: pl.DataFrame, calendar: list[date], memorizing: bool, seen: bool) -> dispersion.Dispersion:
    """HAR-08's dispersion of the IC over the grid of folds × groups, for the memorizer or the honest linear model."""
    groups = split.ticker_groups(synthetic.tickers(NAMES), 5, 0)
    fit = memorizer if memorizing else linear_edge
    cells: dict[tuple[int, int], float | None] = {}
    for fold in split.folds(len(calendar)):
        for held_out in range(5):
            train, test = cell_rows(rows, fold, calendar, groups, held_out, seen)
            scored = fit(train, test).select("date", "score", "rank")
            cells[(fold.number, held_out)] = metrics.information_coefficient(scored, min_tickers=10).mean
    return dispersion.dispersion(cells)


@pytest.mark.slow
def test_a_name_memorizer_shows_the_group_dispersion_signature_and_a_real_edge_does_not() -> None:
    flagged = 0
    for seed in SEEDS:
        rows, calendar = named_rows(seed)
        leaky, held = grid_ic(rows, calendar, True, True).groups, grid_ic(rows, calendar, True, False)
        edge = grid_ic(rows, calendar, False, False)
        assert leaky is not None and held.groups is not None and edge.groups is not None
        assert leaky.mean > 0.15  # without the group axis the memorizer looks like an algorithm
        assert held.groups.mean < leaky.mean / 2  # held-out groups: most of the edge gone
        assert held.groups.sd is not None and edge.groups.sd is not None and held.groups.sd > 1.2 * edge.groups.sd
        assert edge.groups.mean > 0.05 and not edge.fits_names  # the honest model passes at every seed
        flagged += held.fits_names
    assert flagged >= len(SEEDS) / 2  # R-014's flag, HAR-08: group-axis sd above the group-axis mean
