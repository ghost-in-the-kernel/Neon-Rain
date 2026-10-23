"""docs/NAVIGATION-LOG.md: a last review named by its commit, and every debrief complete (test/test_navigation.py)."""
import re

FIELDS: tuple[str, ...] = ("Task", "Opened", "Complaints", "Suggestions")
REVIEW = re.compile(r"^Last review: ([0-9a-f]{7,40}) ", re.MULTILINE)
ENTRY = re.compile(r"^### ", re.MULTILINE)
FIELD = re.compile(r"^- \*\*([^*]+):\*\* ?(.*)$", re.MULTILINE)


def last_review(log: str) -> str:
    """The commit of the last review: "Last review: 10fd67e (…)" gives "10fd67e"; "" unless there is exactly one."""
    found = REVIEW.findall(log)
    return found[0] if len(found) == 1 else ""


def debriefs(log: str) -> list[tuple[str, dict[str, str]]]:
    """Each entry under "## Entries" as its heading and its fields."""
    entries = log.partition("\n## Entries\n")[2]
    parts = ENTRY.split(entries)[1:]
    return [(part.splitlines()[0], dict(FIELD.findall(part))) for part in parts]


def problems(log: str) -> list[str]:
    """A missing last-review line, or a debrief with a field missing or empty ("none" says there was none)."""
    found = [] if last_review(log) else ["not exactly one 'Last review: <commit> (…)' line"]
    for heading, fields in debriefs(log):
        found += [f"debrief '{heading}' has no {name}" for name in FIELDS if not fields.get(name)]
    return found
