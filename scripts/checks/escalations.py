"""docs/ESCALATIONS.md: a known kind, no empty cell, a known status, and three open of a kind listed for Ghost (R-028 (3)).

Adapted from Ghost-Core's registers check (read only, R-028); the kinds are Neon Rain's own.
"""
import re

from scripts.checks import tables

KINDS: tuple[str, ...] = ("missing-row", "not-read", "wrong-row", "stale-pointer", "hard", "no-advisor")
COLUMNS: tuple[str, ...] = ("Date", "Journal", "Task", "Kind", "Route taken", "What was found", "Status")
STATUSES: tuple[str, ...] = ("open", "fixed", "Ghost")
RAISED_AT = 3
JOURNAL_ID = re.compile(r"^J-\d{3,}$")
FOR_GHOST = re.compile(r"^## For Ghost.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
ITEM = re.compile(r"^(?=\d+\. )", re.MULTILINE)


def rows(register: str) -> list[list[str]]:
    """The body rows of the register's table (the one whose header starts with Date), each row's stripped cells."""
    found: list[list[str]] = []
    for table in tables.TABLE.findall(register):
        lines = table.splitlines()
        if tables.cells(lines[0])[:1] == [COLUMNS[0]]:
            found += [tables.cells(line) for line in lines[2:]]
    return found


def header_problems(register: str) -> list[str]:
    """[] when the register has a table headed with exactly COLUMNS; else one line."""
    for table in tables.TABLE.findall(register):
        if tables.cells(table.splitlines()[0])[:1] == [COLUMNS[0]]:
            heads = tables.cells(table.splitlines()[0])
            return [] if tuple(heads) == COLUMNS else [f"the table's columns are {heads}, not {list(COLUMNS)}"]
    return ["docs/ESCALATIONS.md has no table headed Date"]


def row_problems(cells: list[str]) -> list[str]:
    """One row: seven non-empty cells, a J-number, a known kind, a status that starts open, fixed or Ghost."""
    if len(cells) != len(COLUMNS):
        return [f"a row on {cells[0]} has {len(cells)} cells, not {len(COLUMNS)}"]
    date, journal, _, kind, _, _, status = cells
    found = [f"the row on {date} has an empty {name} cell" for name, cell in zip(COLUMNS, cells) if not cell]
    if journal and not JOURNAL_ID.match(journal):
        found.append(f"the row on {date} cites {journal!r}, not a J-number")
    if kind and kind not in KINDS:
        found.append(f"the row on {date} has kind {kind!r}, not one of {len(KINDS)}")
    if status and status.split()[0].rstrip(",:;") not in STATUSES:
        found.append(f"the row on {date} has status {status!r}, not open, fixed or Ghost")
    return found


# Decision: R-028 (3) (three open escalations of one kind go to Ghost until a row names his resolution)
def problems(register: str, handoff: str) -> list[str]:
    """Every row's problems; and a kind with RAISED_AT or more open rows that no numbered For Ghost item about escalations names."""
    found = header_problems(register)
    open_by_kind: dict[str, int] = {}
    for cells in rows(register):
        found += row_problems(cells)
        if len(cells) == len(COLUMNS) and cells[6].startswith("open"):
            open_by_kind[cells[3]] = open_by_kind.get(cells[3], 0) + 1
    items = [item for section in FOR_GHOST.findall(handoff) for item in ITEM.split(section)]
    about_escalations = [item for item in items if "escalation" in item.lower()]
    for kind, count in open_by_kind.items():
        if count >= RAISED_AT and not any(f"`{kind}`" in item for item in about_escalations):
            found.append(f"{count} open escalations of kind {kind!r} and no numbered For Ghost item about escalations names it")
    return found
