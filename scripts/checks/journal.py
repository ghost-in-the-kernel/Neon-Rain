"""docs/JOURNAL.md's entries are numbered in order with a known class, and every open conflict is waiting on Ghost
in docs/HANDOFF.md's "For Ghost" section (test/test_journal.py; CLAUDE.md, "When another agent's work conflicts")."""
import re

CLASSES: tuple[str, ...] = (
    "contradiction", "ambiguity", "failure-caught", "failure-missed", "decision", "measurement", "direction",
    "trial", "deferred", "conflict",
)
HEADING = re.compile(r"^### (J-\d{3}) ", re.MULTILINE)
FIELD = re.compile(r"^- \*\*([^*]+):\*\* ?(.*)$", re.MULTILINE)


def entries(journal: str) -> dict[str, dict[str, str]]:
    """Each entry's fields by id: "### J-001 x\\n- **Class:** trial\\n" gives {"J-001": {"Class": "trial"}}."""
    heads = list(HEADING.finditer(journal))
    bounds = [m.start() for m in heads] + [len(journal)]
    return {m.group(1): dict(FIELD.findall(journal[bounds[i]:bounds[i + 1]])) for i, m in enumerate(heads)}


def number_problems(journal: str) -> list[str]:
    """Ids J-001, J-002, ... each once, in order."""
    for position, found in enumerate(HEADING.findall(journal), start=1):
        if found != f"J-{position:03d}":
            return [f"entry {position} is {found}, expected J-{position:03d}"]
    return []


def waiting_on_ghost(handoff: str) -> str:
    """The text of HANDOFF.md's "For Ghost" section, up to the next heading; "" if there is none."""
    return "".join(re.findall(r"^## For Ghost.*?(?=^## |\Z)", handoff, flags=re.MULTILINE | re.DOTALL))


# Decision: J-023 (a conflict goes to Ghost at once, both objectives stated; open until Ghost resolves it)
def conflict_problems(fields: dict[str, str], entry: str, queue: str) -> list[str]:
    """One conflict entry: both objectives written, and, unless Ghost resolved it, listed for Ghost."""
    found = [f"{entry} is a conflict with no {name} objective" for name in ("Mine", "Theirs") if not fields.get(name)]
    if "Ghost" not in str(fields.get("Resolved")) and entry not in queue:
        found.append(f"{entry} is an open conflict not listed in HANDOFF.md's For Ghost section")
    return found


def problems(journal: str, handoff: str) -> list[str]:
    """Everything wrong with the journal given the handoff; [] when it holds."""
    found = number_problems(journal)
    queue = waiting_on_ghost(handoff)
    for entry, fields in entries(journal).items():
        kind = fields.get("Class", "")
        if kind not in CLASSES:
            found.append(f"{entry} has class {kind!r}, not one of {len(CLASSES)}")
        if kind == "conflict":
            found += conflict_problems(fields, entry, queue)
    return found
