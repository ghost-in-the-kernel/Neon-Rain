"""The agent's metrics of docs/AGENT.md, measured from the files (scripts/metrics.py, test/test_metrics.py)."""
import re
from pathlib import Path

from scripts.checks import ghost, results, tables

SOURCE_DIRS: tuple[str, ...] = ("neonrain", "scripts", "test")
TIMED: tuple[str, ...] = ("Fast loop (s)", "Full check, `precommit.sh` (min)")
# Decision: R-019 (recorded at tithe passes: judged against its target every run, never stale-checked)
AT_TITHE: tuple[str, ...] = ("Largest source file (lines)", "Docs lines per source line")


def python_lines(root: Path, tops: tuple[str, ...]) -> list[int]:
    """The line count of every .py file under the given top-level folders."""
    return [len(p.read_text().splitlines()) for top in tops for p in sorted((root / top).rglob("*.py"))]


def opened(name: str, root: Path) -> int:
    """The files one backticked name opens: a folder ("neonrain/harness/") its .py files, anything else one.
    A folder not built yet counts as one: the row still sends the agent there."""
    folder = root / name
    if name.endswith("/") and folder.is_dir():
        return max(1, len(list(folder.glob("*.py"))))
    return 1


def routing_files(claude: str, root: Path) -> int:
    """The most files one routing row of CLAUDE.md opens, counting its "Start here" cell's backticked names
    (a folder as its files); 0 with no table."""
    for table in tables.TABLE.findall(claude):
        lines = table.splitlines()
        if tables.cells(lines[0])[:2] == ["Task", "Start here"]:
            names = [re.findall(r"`([^`]+)`", tables.cells(line)[1]) for line in lines[2:]]
            return max(sum(opened(name, root) for name in row) for row in names)
    return 0


def largest(root: Path) -> int:
    """The longest of our .py files in lines; 0 when there is none."""
    return max(python_lines(root, SOURCE_DIRS), default=0)


def without_see_also(ghost_text: str) -> int:
    """Decisions whose See also line is missing or empty."""
    return sum(1 for entry in ghost.split_entries(ghost_text).values() if not ghost.fields_of(entry).get("See also"))


def results_lacking(root: Path, phrase: str) -> int:
    """Reported rows with a problem containing `phrase` ("trials.tsv" or "dispersion")."""
    text = (root / "docs" / "RESULTS.md").read_text()
    hashes = results.trial_hashes((root / "harness" / "trials.tsv").read_text())
    rows = results.reported_rows(text)
    return sum(1 for row in rows if any(phrase in p for p in results.row_problems(row, hashes)))


def unlisted_datasets(root: Path) -> int:
    """Entries under data/ but MANIFEST.md that no manifest row names."""
    manifest = (root / "data" / "MANIFEST.md").read_text()
    named = {tables.cells(line)[0] for line in manifest.splitlines()[2:] if line.startswith("|")}
    present = {p.name.split(".")[0] for p in (root / "data").iterdir() if p.name != "MANIFEST.md"}
    return len(present - named)


def docs_per_source(root: Path) -> float | None:
    """Lines of the documents (root and docs/ .md) per line of neonrain/; None while there is no neonrain/."""
    source = sum(python_lines(root, ("neonrain",)))
    if source == 0:
        return None
    documents = sorted(root.glob("*.md")) + sorted((root / "docs").glob("*.md"))
    return round(sum(len(p.read_text().splitlines()) for p in documents) / source, 2)


def measure(root: Path, fast_loop: float | None, full_check: float | None) -> dict[str, float | None]:
    """Every metric by its name in AGENT.md's table; the two timings are measured by precommit.sh and passed in."""
    return {
        "Mandatory context (words)": len((root / "CLAUDE.md").read_text().split()),
        "Fast loop (s)": fast_loop,
        "Full check, `precommit.sh` (min)": full_check,
        "Largest source file (lines)": largest(root),
        "Files a routing row opens": routing_files((root / "CLAUDE.md").read_text(), root),
        "Decisions without `See also`": without_see_also((root / "theGhost.md").read_text()),
        "Results without a trials line": results_lacking(root, "trials.tsv"),
        "Results without dispersion": results_lacking(root, "dispersion"),
        "Datasets without a manifest line": unlisted_datasets(root),
        "Docs lines per source line": docs_per_source(root),
    }
