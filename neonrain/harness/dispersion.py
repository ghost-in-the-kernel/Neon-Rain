"""HAR-08: every number with its dispersion over the two axes of the grid, folds and groups (R-014, P-07)."""
import statistics
from typing import NamedTuple


class Axis(NamedTuple):
    """One axis: mean ± sd, [low, high], over `count` folds or groups."""

    mean: float
    sd: float | None
    low: float
    high: float
    count: int


class Dispersion(NamedTuple):
    """Both axes of one metric, the cells left out as undefined, and R-014's memorization flag."""

    folds: Axis | None
    groups: Axis | None
    undefined_cells: int
    fits_names: bool


def axis(averages: list[float]) -> Axis | None:
    """mean, sd (divisor n − 1, None for one value), min and max of the per-fold or per-group averages."""
    if not averages:
        return None
    spread = statistics.stdev(averages) if len(averages) > 1 else None
    return Axis(statistics.fmean(averages), spread, min(averages), max(averages), len(averages))


def averages(cells: dict[tuple[int, int], float | None], side: int) -> list[float]:
    """The average of the defined cells along each fold (side 0) or group (side 1), in key order."""
    found: dict[int, list[float]] = {}
    for key in sorted(cells):
        value = cells[key]
        if value is not None:
            found.setdefault(key[side], []).append(value)
    return [statistics.fmean(found[k]) for k in sorted(found)]


# Decision: R-014 (a group-axis sd above the group-axis mean's size fits names, not an algorithm)
def dispersion(cells: dict[tuple[int, int], float | None]) -> Dispersion:
    """HAR-08 for one metric given each (fold, group) cell's value, None where it is undefined.

    Cells {(0, 0): 1, (0, 1): 3, (1, 0): 2, (1, 1): 4}: folds average 2 and 3, groups 1.5 and 3.5.
    """
    groups = axis(averages(cells, 1))
    undefined = sum(1 for value in cells.values() if value is None)
    flagged = groups is not None and groups.sd is not None and groups.sd > abs(groups.mean)
    return Dispersion(axis(averages(cells, 0)), groups, undefined, flagged)
