"""HAR-08 by hand (R-015d): every number carries its spread over folds and over groups."""
import math

import pytest

from neonrain.harness import dispersion
from neonrain.harness.dispersion import Axis


def test_both_axes_by_hand() -> None:
    # Fold 0: groups 1, 3 → 2. Fold 1: groups 2, 4 → 3. Folds: mean 2.5, sd √0.5. Groups: 1.5 and 3.5.
    found = dispersion.dispersion({(0, 0): 1.0, (0, 1): 3.0, (1, 0): 2.0, (1, 1): 4.0})
    assert found.folds == Axis(2.5, pytest.approx(math.sqrt(0.5)), 2.0, 3.0, 2)
    assert found.groups == Axis(2.5, pytest.approx(math.sqrt(2.0)), 1.5, 3.5, 2)
    assert (found.undefined_cells, found.fits_names) == (0, False)


def test_an_undefined_cell_is_left_out_of_both_averages_and_counted() -> None:
    # (1, 1) undefined: fold 1 is 2 alone; group 1 is 3 alone.
    found = dispersion.dispersion({(0, 0): 1.0, (0, 1): 3.0, (1, 0): 2.0, (1, 1): None})
    assert (found.folds.mean, found.folds.low, found.folds.high) == (2.0, 2.0, 2.0)
    assert (found.groups.low, found.groups.high, found.groups.count) == (1.5, 3.0, 2)
    assert found.undefined_cells == 1


def test_a_fold_with_nothing_defined_leaves_its_axis() -> None:
    found = dispersion.dispersion({(0, 0): 1.0, (0, 1): 3.0, (1, 0): None, (1, 1): None})
    assert found.folds == Axis(2.0, None, 2.0, 2.0, 1) and found.undefined_cells == 2
    assert found.groups == Axis(2.0, pytest.approx(math.sqrt(2.0)), 1.0, 3.0, 2)


def test_nothing_defined_has_no_axes() -> None:
    found = dispersion.dispersion({(0, 0): None, (0, 1): None})
    assert found == dispersion.Dispersion(None, None, 2, False)


def test_a_wide_group_spread_fits_names() -> None:
    # Groups average 0.1 and −0.05: mean 0.025, sd ≈ 0.106 > 0.025, so the mean means nothing (R-014).
    found = dispersion.dispersion({(0, 0): 0.1, (0, 1): -0.05, (1, 0): 0.1, (1, 1): -0.05})
    assert found.fits_names is True
    steady = dispersion.dispersion({(0, 0): 0.1, (0, 1): 0.08, (1, 0): 0.1, (1, 1): 0.08})
    assert steady.fits_names is False


def test_a_negative_mean_is_judged_by_its_size() -> None:
    # Mean −0.09, sd ≈ 0.014: the spread is small against |mean|, so it is not flagged.
    assert dispersion.dispersion({(0, 0): -0.1, (0, 1): -0.08}).fits_names is False
    assert dispersion.dispersion({(0, 0): -0.01, (0, 1): 0.05}).fits_names is True


def test_one_group_cannot_be_judged() -> None:
    assert dispersion.dispersion({(0, 0): 0.1, (1, 0): -0.5}).fits_names is False


def test_cells_are_read_in_order_whatever_order_they_come_in() -> None:
    cells = {(1, 1): 4.0, (0, 1): 3.0, (1, 0): 2.0, (0, 0): 1.0}
    assert dispersion.averages(cells, 0) == [2.0, 3.0] and dispersion.averages(cells, 1) == [1.5, 3.5]


def test_a_spread_equal_to_the_mean_does_not_exceed_it() -> None:
    # Groups 0, 1, 2: mean 1, sd exactly 1. HAR-08 flags an sd that exceeds the mean, so this is not flagged.
    found = dispersion.dispersion({(0, 0): 0.0, (0, 1): 1.0, (0, 2): 2.0})
    assert found.groups.sd == 1.0 and found.groups.mean == 1.0 and found.fits_names is False
