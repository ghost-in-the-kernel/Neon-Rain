"""theGhost.md's shape: ids, fields, statuses, supersessions and conflicts (test/test_ghost.py)."""
import re

FIELDS: tuple[str, ...] = ("Decision", "Why", "Held by", "Source", "Status", "See also", "subject")
PLAIN_STATUSES: tuple[str, ...] = ("proposed", "in force", "withdrawn", "refused")
HEADING = re.compile(r"^### (R-\d{3}): ", re.MULTILINE)
FIELD_LINE = re.compile(r"^- \*\*([^*]+):\*\* ?(.*)$", re.MULTILINE)
CONFLICTS = re.compile(r"^- \*\*conflicts-with:\*\* (.*)$", re.MULTILINE)
SUPERSEDED = re.compile(r"^superseded by (R-\d{3})$")


def split_entries(text: str) -> dict[str, str]:
    """The entries by id, each its text up to the next heading; a duplicated id keeps its last text.

    For "### R-001: a\\nbody\\n### R-002: b\\n" it returns {"R-001": "### R-001: a\\nbody\\n", "R-002": ...}.
    """
    headings = list(HEADING.finditer(text))
    bounds = [m.start() for m in headings] + [len(text)]
    return {m.group(1): text[bounds[i]:bounds[i + 1]] for i, m in enumerate(headings)}


def fields_of(entry: str) -> dict[str, str]:
    """An entry's `- **Name:** value` lines as {name: first line of value}."""
    return {m.group(1): m.group(2).strip() for m in FIELD_LINE.finditer(entry)}


def id_problems(text: str) -> list[str]:
    """Ids that are duplicated or out of sequence: R-001, R-002, ... with no gap."""
    ids = HEADING.findall(text)
    problems = [f"{rid} appears {ids.count(rid)} times" for rid in sorted(set(ids)) if ids.count(rid) > 1]
    for position, rid in enumerate(ids, start=1):
        if rid != f"R-{position:03d}":
            problems.append(f"entry {position} is {rid}, expected R-{position:03d}")
            break
    return problems


def status_problem(rid: str, status: str, entries: dict[str, str]) -> str | None:
    """What is wrong with one entry's status, or None: one of the five words, a supersession two-sided."""
    if status in PLAIN_STATUSES:
        return None
    match = SUPERSEDED.match(status)
    if match is None:
        return f"{rid} has status {status!r}, not one of the five"
    successor = match.group(1)
    if successor not in entries:
        return f"{rid} is superseded by {successor}, which does not exist"
    if rid not in entries[successor]:
        return f"{rid} is superseded by {successor}, which does not name it back"
    return None


def entry_problems(entries: dict[str, str]) -> list[str]:
    """Missing fields and bad statuses, entry by entry."""
    problems = []
    for rid, entry in entries.items():
        fields = fields_of(entry)
        problems += [f"{rid} has no {name} line" for name in FIELDS if name not in fields]
        problem = status_problem(rid, fields["Status"], entries) if "Status" in fields else None
        problems += [problem] if problem else []
    return problems


# Decision: P-05 (two in-force decisions on one subject that say they conflict cannot both stand)
def conflict_problems(entries: dict[str, str]) -> list[str]:
    """In-force pairs on one subject where one names the other on a `conflicts-with:` line; a name that is no entry."""
    problems = []
    for rid, entry in entries.items():
        fields = fields_of(entry)
        named = [other for line in CONFLICTS.findall(entry) for other in re.findall(r"R-\d{3}", line)]
        for other in named:
            if other not in entries:
                problems.append(f"{rid} conflicts with {other}, which does not exist")
                continue
            both = fields.get("Status") == fields_of(entries[other]).get("Status") == "in force"
            if both and fields_of(entries[other]).get("subject") == fields.get("subject"):
                problems.append(f"{rid} and {other} are both in force on {fields.get('subject')!r} and conflict")
    return problems


def problems(text: str) -> list[str]:
    """Everything wrong with theGhost.md's text; [] when it holds."""
    entries = split_entries(text)
    return id_problems(text) + entry_problems(entries) + conflict_problems(entries)
