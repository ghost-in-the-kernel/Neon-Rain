"""docs/decisions.md, the one-line index of theGhost.md (R-028 (2), AGT-05): its text, and whether it is stale.

Written by `python3 -I scripts/decisions_index.py`; test/test_decisions.py fails when the file differs from `render`.
Parsing is ghost.py's (split_entries, fields_of); this module only formats.
"""
from pathlib import Path

from scripts.checks import ghost

COMMAND = "python3 -I scripts/decisions_index.py"
HEADER = (
    "# Decisions, one line each\n\n"
    f"Written by `{COMMAND}` from `theGhost.md`; do not edit here. "
    "Search `### R-012` in theGhost.md for the entry.\n\n"
    "| Id | Decision | Status | subject |\n| --- | --- | --- | --- |\n"
)


def title_of(entry: str) -> str:
    """An entry's heading after its id: title_of("### R-001: a rule\\nbody") gives "a rule"."""
    return entry.splitlines()[0].split(": ", 1)[1]


def cell(value: str) -> str:
    """A table cell: a `|` in a title would split the row, so it is escaped."""
    return value.replace("|", "\\|")


def render(text: str) -> str:
    """The index for theGhost.md's text: the header and one table row per entry, in file order."""
    rows = []
    for rid, entry in ghost.split_entries(text).items():
        fields = ghost.fields_of(entry)
        rows.append(f"| {rid} | {cell(title_of(entry))} | {cell(fields.get('Status', ''))} | {cell(fields.get('subject', ''))} |")
    return HEADER + "\n".join(rows) + "\n"


def stale_problems(root: Path) -> list[str]:
    """[] when docs/decisions.md is exactly the index of theGhost.md; else one line naming the command."""
    index = root / "docs" / "decisions.md"
    if index.exists() and index.read_text() == render((root / "theGhost.md").read_text()):
        return []
    return [f"docs/decisions.md is stale or missing: run `{COMMAND}`"]
