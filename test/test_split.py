"""The grid (TODO 1.3; HAR-03 to HAR-05): folds by hand, purging by hand, and no training label's window reaching
any test date on the synthetic market, checked by brute force at every horizon."""
import hashlib
from datetime import date, timedelta

import polars as pl
import pytest

from neonrain import targets
from neonrain.harness import split, synthetic
from neonrain.harness.split import Fold

CALENDAR = [date(2000, 1, 3) + timedelta(days=d) for d in range(80)]


def rows(tickers: list[str], calendar: list[date]) -> pl.DataFrame:
    """One row per ticker per date, as a labels frame would have."""
    pairs = [(t, d) for t in tickers for d in calendar]
    return pl.DataFrame(pairs, schema={"ticker": pl.String, "date": pl.Date}, orient="row")


def test_the_first_fold_by_hand() -> None:
    # 756 dates must survive purging at 63: b = 756 + 63 = 819; embargo 63 to 882; test 126 to 1008.
    assert split.folds(1008) == [Fold(0, 0, 819, 882, 1008)]
    assert split.folds(1007) == []


def test_folds_roll_forward_by_the_step_and_their_test_spans_tile() -> None:
    found = split.folds(1300)
    assert [f.train_end for f in found] == [819, 945, 1071]
    assert all(f.train_start == 0 for f in found)
    assert all(later.test_start == earlier.test_end for earlier, later in zip(found, found[1:]))
    assert all(f.test_start - f.train_end == 63 and f.test_end - f.test_start == 126 for f in found)


def test_a_rolling_window_moves_the_start() -> None:
    found = split.folds(1300, window=900)
    assert [(f.train_start, f.train_end) for f in found] == [(0, 819), (45, 945), (171, 1071)]


def test_other_steps_and_embargoes() -> None:
    assert split.folds(1000, embargo=100, step=50) == [Fold(0, 0, 819, 919, 969)]
    assert [f.number for f in split.folds(1300, step=1)][-1] == 1300 - 819 - 63 - 1


def test_bad_parameters_are_refused() -> None:
    with pytest.raises(ValueError, match="embargo is 62"):
        split.folds(2000, embargo=62)
    with pytest.raises(ValueError, match="step is 0"):
        split.folds(2000, step=0)
    with pytest.raises(ValueError, match="window is 818: at least 819 to keep 756"):
        split.folds(2000, window=818)
    assert split.folds(2000, window=819)[0] == Fold(0, 0, 819, 882, 1008)


def test_purging_by_hand() -> None:
    # Train [0, 10) at horizon 3: position t stays only if t + 3 < 10, so 0..6 stay and 7, 8, 9 go.
    fold = Fold(0, 0, 10, 73, 80)
    kept = split.training(rows(["A"], CALENDAR), fold, CALENDAR, 3)
    assert kept["date"].to_list() == CALENDAR[:7] and kept.columns == ["ticker", "date"]
    assert split.training(rows(["A"], CALENDAR), fold, CALENDAR, 9)["date"].to_list() == CALENDAR[:1]
    assert split.training(rows(["A"], CALENDAR), Fold(0, 2, 10, 73, 80), CALENDAR, 3)["date"].to_list() == CALENDAR[2:7]


def test_test_rows_are_never_purged() -> None:
    kept = split.testing(rows(["A"], CALENDAR), Fold(0, 0, 10, 73, 79), CALENDAR)
    assert kept["date"].to_list() == CALENDAR[73:79] and kept.columns == ["ticker", "date"]


def test_no_training_label_reaches_a_test_date_at_any_horizon_by_brute_force() -> None:
    # TODO 1.3's check, independently of split.py's arithmetic: each training row's label ends at its date
    # moved h trading dates on, and that date must come before the fold's first test date (and before b).
    market = synthetic.generate(synthetic.MarketConfig(tickers=25, days=1300, seed=3))
    index = {d: i for i, d in enumerate(market.calendar)}
    for horizon in targets.HORIZONS:
        labels = targets.labels(market.prices, market.universe, market.calendar, horizon).frame
        for fold in split.folds(len(market.calendar)):
            train = split.training(labels, fold, market.calendar, horizon)
            ends = [market.calendar[index[d] + horizon] for d in train["date"].unique().to_list()]
            assert max(ends) < market.calendar[fold.train_end] < market.calendar[fold.test_start]
            assert train.height == 25 * (fold.train_end - horizon)


def test_groups_are_the_hash_of_harness_md() -> None:
    expected = int(hashlib.sha256(b"7:T001").hexdigest(), 16) % 5
    assert split.group_of("T001", 5, 7) == expected


def test_every_ticker_is_in_exactly_one_group_reproducibly() -> None:
    names = synthetic.tickers(200)
    first = split.ticker_groups(names, 5, seed=1)
    assert sorted(first) == names and set(first.values()) == {0, 1, 2, 3, 4}
    assert split.ticker_groups(list(reversed(names)) + names[:3], 5, seed=1) == first
    assert split.ticker_groups(names, 5, seed=2) != first
    assert split.ticker_groups(names) == split.ticker_groups(names, 5, seed=0)


def test_an_empty_group_is_refused() -> None:
    with pytest.raises(ValueError, match=r"groups \[.*\] of 5 are empty for 2 tickers with seed 0"):
        split.ticker_groups(["A", "B"], 5, 0)


def test_a_cell_trains_on_the_other_groups_and_tests_on_the_held_out_one() -> None:
    names = synthetic.tickers(40)
    groups = split.ticker_groups(names, 5, 0)
    frame, fold = rows(names, CALENDAR), Fold(0, 0, 10, 73, 80)
    tested = []
    for held_out in range(5):
        train, test = split.cell(frame, fold, CALENDAR, 3, groups, held_out)
        assert set(train["ticker"]) == {t for t, g in groups.items() if g != held_out}
        assert set(test["ticker"]) == {t for t, g in groups.items() if g == held_out}
        assert train["date"].max() == CALENDAR[6] and test["date"].min() == CALENDAR[73]
        tested += test["ticker"].unique().to_list()
    assert sorted(tested) == names


def test_a_ticker_with_no_group_is_refused() -> None:
    groups = split.ticker_groups(synthetic.tickers(40), 5, 0)
    with pytest.raises(ValueError, match=r"tickers with no group: \['ZZZ'\]"):
        split.cell(rows(synthetic.tickers(40) + ["ZZZ"], CALENDAR), Fold(0, 0, 10, 73, 80), CALENDAR, 3, groups, 0)
    extra = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6"]
    with pytest.raises(ValueError, match=r"no group: \['Z1', 'Z2', 'Z3', 'Z4', 'Z5'\]$"):
        split.cell(rows(synthetic.tickers(40) + extra, CALENDAR), Fold(0, 0, 10, 73, 80), CALENDAR, 3, groups, 0)


def test_training_on_one_ticker_is_refused() -> None:
    groups = {"A": 0, "B": 1, "C": 1}
    frame, fold = rows(["A", "B", "C"], CALENDAR), Fold(3, 0, 10, 73, 80)
    split.cell(frame, fold, CALENDAR, 3, groups, 0)
    with pytest.raises(ValueError, match="fold 3, group 1: training has fewer than two tickers"):
        split.cell(frame, fold, CALENDAR, 3, groups, 1)


def test_positions_by_hand() -> None:
    assert split.positions(CALENDAR[:2]).rows() == [(CALENDAR[0], 0), (CALENDAR[1], 1)]
    assert split.positions([]).schema == {"date": pl.Date, "position": pl.Int64}
