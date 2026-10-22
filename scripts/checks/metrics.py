"""The agent's metrics of docs/AGENT.md, measured from the files (scripts/metrics.py, test/test_metrics.py)."""
import re
from pathlib import Path

from scripts.checks import ghost, results

SOURCE_DIRS: tuple[str, ...] = ("neonrain", "scripts", "test")
TIMED: tuple[str, ...] = ("Fast loop (s)", "Full check, `precommit.sh` (min)")


def python_lines(root: Path, tops: tuple[str, ...]) -> list[int]:
    """The line count of every .py file under the given top-level folders."""
    return [len(p.read_text().splitlines()) for top in tops for p in sorted((root / top).rglob("*.py"))]


def routing_files(claude: str) -> int:
    """The most files one routing row of CLAUDE.md opens: backticked names in its "Start here" cell."""
    rows = [line.split("|") for line in claude.splitlines() if line.startswith("| ") and not line.startswith("| Task")]
    return max((len(re.findall(r"`[^`]+`", row[2])) for row in rows if len(row) > 3), default=0)


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
    named = {line.split("|")[1].strip() for line in manifest.splitlines()[2:] if line.startswith("| ")}
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
        "Largest source file (lines)": max(python_lines(root, SOURCE_DIRS), default=0),
        "Files a routing row opens": routing_files((root / "CLAUDE.md").read_text()),
        "Decisions without `See also`": without_see_also((root / "theGhost.md").read_text()),
        "Results without a trials line": results_lacking(root, "trials.tsv"),
        "Results without dispersion": results_lacking(root, "dispersion"),
        "Datasets without a manifest line": unlisted_datasets(root),
        "Docs lines per source line": docs_per_source(root),
    }
