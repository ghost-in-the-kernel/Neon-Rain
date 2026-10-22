"""Every reported number in docs/RESULTS.md has its trials line, both dispersions and its findings
(test/test_results.py; P-07, R-014, HAR-13)."""
import re

TRIALS_COLUMNS: list[str] = ["config_hash", "date", "horizon", "metric", "mean", "dispersion", "trials_so_far", "note"]
TABLE = re.compile(r"(?:^\|.*(?:\n|$))+", re.MULTILINE)
DISPERSION = re.compile(r"±.*\[.*,.*\]")
FINDING = re.compile(r"\bNR-F-\d{2}\b")


def cells(line: str) -> list[str]:
    """A table line's cells, trimmed: "| a | b |" gives ["a", "b"]."""
    return [cell.strip() for cell in line.strip().split("|")[1:-1]]


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
    return found


def problems(results: str, trials: str) -> list[str]:
    """Everything wrong with RESULTS.md given trials.tsv; [] when every number has its evidence."""
    first = trials.partition("\n")[0]
    found = [] if first == "\t".join(TRIALS_COLUMNS) else [f"harness/trials.tsv's header is {first!r}, not HAR-09's"]
    for row in reported_rows(results):
        found += row_problems(row, trial_hashes(trials))
    return found
