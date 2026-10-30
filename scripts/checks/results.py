"""Every reported number in docs/RESULTS.md has its trials line, both dispersions, its findings and its period; a run
on WIKI is reported for both periods (test/test_results.py; P-07, R-014, HAR-13, R-026)."""
import re

from neonrain.harness.trials import TRIALS_COLUMNS
from neonrain.universe.periods import FROM_BOUNDARY, SURVIVOR_ONLY
from scripts.checks.tables import TABLE, cells

DISPERSION = re.compile(r"±.*\[.*,.*\]")
FINDING = re.compile(r"\bNR-F-\d{2}\b")
# A run is known to be synthetic or WIKI by its row's Period cell: trials.tsv carries no data column, and one config
# hash names one dataset (HAR-01 hashes the data manifest), so a run has one kind of period (R-026).
SYNTHETIC = "synthetic"
PERIODS = (SYNTHETIC, SURVIVOR_ONLY, FROM_BOUNDARY)


def reported_rows(results: str) -> list[dict[str, str]]:
    """The data rows of every table with a Run column, as {header: cell}; "*(none yet)*" rows left out.

    A row shorter than its header has no key for the missing cells.
    """
    rows = []
    for table in TABLE.findall(results):
        lines = table.splitlines()
        header = cells(lines[0])
        if "Run" in header:
            rows += [dict(zip(header, cells(line))) for line in lines[2:] if not line.startswith("| *(none yet)*")]
    return rows


def cell(row: dict[str, str], prefix: str) -> str:
    """The text of every cell whose header starts with `prefix`, joined; "" when there is none."""
    return " ".join(value for name, value in row.items() if name.startswith(prefix))


def trial_hashes(trials: str) -> set[str]:
    """The config_hash column of harness/trials.tsv: the text before each line's first tab, header left out."""
    return {line.partition("\t")[0] for line in trials.splitlines()[1:]}


def row_problems(row: dict[str, str], hashes: set[str]) -> list[str]:
    """One reported row against P-07: its trials line, a dispersion on both axes, a finding cited."""
    run = cell(row, "Run") or "?"
    found = [] if run in hashes else [f"{run} has no line in harness/trials.tsv"]
    for axis in ("Folds", "Groups"):
        if not DISPERSION.search(cell(row, axis)):
            found.append(f"{run} has no dispersion on the {axis.lower()} axis (mean ± sd [min, max])")
    if not FINDING.search(cell(row, "Findings")):
        found.append(f"{run} cites no finding (NR-F-nn)")
    if cell(row, "Period") not in PERIODS:
        found.append(f"{run} names no period ({', '.join(PERIODS)})")
    return found


def label(row: dict[str, str]) -> str:
    """What a reported number is of: its model (else its run), horizon and metric, the cells it has, joined by spaces.

    A WIKI model has one run per period (one config hash names one period), so a table that carries a Model column
    pairs its periods by the model, and one without pairs them by the run."""
    return " ".join(part for part in (cell(row, "Model") or cell(row, "Run") or "?", cell(row, "Horizon"),
                                      cell(row, "Metric")) if part)


def pairing_problems(rows: list[dict[str, str]]) -> list[str]:
    """R-026: a run, horizon and metric reported for one WIKI period is reported for the other; a pooled number is alone."""
    reported: dict[str, set[str]] = {}
    for row in rows:
        reported.setdefault(label(row), set()).add(cell(row, "Period"))
    return [f"{name} is reported for the {SURVIVOR_ONLY if SURVIVOR_ONLY in have else FROM_BOUNDARY} period only, "
            f"not for the {FROM_BOUNDARY if SURVIVOR_ONLY in have else SURVIVOR_ONLY} (R-026)"
            for name, have in reported.items() if (SURVIVOR_ONLY in have) != (FROM_BOUNDARY in have)]


def problems(results: str, trials: str) -> list[str]:
    """Everything wrong with RESULTS.md given trials.tsv; [] when every number has its evidence."""
    first = trials.partition("\n")[0]
    found = [] if first == "\t".join(TRIALS_COLUMNS) else [f"harness/trials.tsv's header is {first!r}, not HAR-09's"]
    for row in reported_rows(results):
        found += row_problems(row, trial_hashes(trials))
    return found + pairing_problems(reported_rows(results))
