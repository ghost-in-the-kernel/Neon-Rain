"""Every reported number in docs/RESULTS.md has its trials line, both dispersions and its findings
(test/test_results.py; P-07, R-014, HAR-13)."""
import re

TRIALS_COLUMNS: list[str] = ["config_hash", "date", "horizon", "metric", "mean", "dispersion", "trials_so_far", "note"]
DISPERSION = re.compile(r"±.*\[.*,.*\]")
FINDING = re.compile(r"\bNR-F-\d{2}\b")


def cells(line: str) -> list[str]:
    """A table line's cells, trimmed: "| a | b |" gives ["a", "b"]."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


# Unsure: only tables with a Run column are held; the scorer's agreement (5.3) and the forward test (7) have
# no config_hash of their own yet, and their rule is theirs to write when those phases open.
def reported_rows(results: str) -> list[dict[str, str]]:
    """The data rows of every table with a Run column, as {header: cell}; "*(none yet)*" rows left out."""
    rows = []
    header: list[str] = []
    for line in results.splitlines():
        if not line.startswith("|"):
            header = []
        elif not header:
            header = cells(line)
        elif not line.startswith("| ---") and "Run" in header and not line.startswith("| *(none yet)*"):
            rows.append(dict(zip(header, cells(line), strict=False)))
    return rows


def trial_hashes(trials: str) -> set[str]:
    """The config_hash column of harness/trials.tsv."""
    return {line.split("\t")[0] for line in trials.splitlines()[1:] if line.strip()}


def row_problems(row: dict[str, str], hashes: set[str]) -> list[str]:
    """One reported row against P-07: its trials line, a dispersion on both axes, a finding cited."""
    run = row.get("Run", "")
    found = [] if run in hashes else [f"{run or '?'} has no line in harness/trials.tsv"]
    for axis in ("Folds", "Groups"):
        column = next((name for name in row if name.startswith(axis)), axis)
        if not DISPERSION.search(row.get(column, "")):
            found.append(f"{run or '?'} has no dispersion on the {axis.lower()} axis (mean ± sd [min, max])")
    if not FINDING.search(row.get("Findings", "")):
        found.append(f"{run or '?'} cites no finding (NR-F-nn)")
    return found


def problems(results: str, trials: str) -> list[str]:
    """Everything wrong with RESULTS.md given trials.tsv; [] when every number has its evidence."""
    header = trials.splitlines()[0].split("\t") if trials.strip() else []
    found = [] if header == TRIALS_COLUMNS else [f"harness/trials.tsv's header is {header}, not HAR-09's"]
    for row in reported_rows(results):
        found += row_problems(row, trial_hashes(trials))
    return found
