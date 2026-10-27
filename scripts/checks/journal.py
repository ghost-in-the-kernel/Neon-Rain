"""The journal's entries (docs/journal/J-nnn-mmm.md, ten ids to a file, R-028 (4)) are numbered in order, each in its
own file, with a known class, and every open conflict is waiting on Ghost in docs/HANDOFF.md's "For Ghost" section;
docs/journal/INDEX.md is their one-line index (test/test_journal.py; CLAUDE.md, "When another agent's work conflicts")."""
import re
from pathlib import Path

from scripts.checks import decisions

CLASSES: tuple[str, ...] = (
    "contradiction", "ambiguity", "failure-caught", "failure-missed", "decision", "measurement", "direction",
    "trial", "deferred", "conflict",
)
# Decision: R-028 (4) (ten ids to a file: about 20 lines an entry makes 160 to 280 lines, read whole, under AGT-04's 400)
PER_FILE = 10
COMMAND = "python3 -I scripts/journal_index.py"
HEADING = re.compile(r"^### (J-\d{3}) ", re.MULTILINE)
TITLE = re.compile(r"^### (J-\d{3}) (.*)$", re.MULTILINE)
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


def file_name(number: int) -> str:
    """The file that holds entry `number`: file_name(1) and file_name(10) give "J-001-010.md", file_name(11) "J-011-020.md"."""
    first = (number - 1) // PER_FILE * PER_FILE + 1
    return f"J-{first:03d}-{first + PER_FILE - 1:03d}.md"


def read_files(root: Path) -> dict[str, str]:
    """docs/journal/'s J-*.md files by name, in name order."""
    return {p.name: p.read_text() for p in sorted((root / "docs" / "journal").glob("J-*.md"))}


def joined(files: dict[str, str]) -> str:
    """The files' text as one, in name order: what number_problems, entries and problems read."""
    return "".join(files[name] for name in sorted(files))


def file_problems(files: dict[str, str]) -> list[str]:
    """Each entry sits in the file its number names, and no file is empty: ["J-011 is in J-001-010.md, expected J-011-020.md"]."""
    found = []
    for name, text in sorted(files.items()):
        ids = HEADING.findall(text)
        if not ids:
            found.append(f"{name} holds no entry")
        found += [f"{i} is in {name}, expected {file_name(int(i[2:]))}" for i in ids if file_name(int(i[2:])) != name]
    return found


def heading_lines(text: str) -> dict[str, int]:
    """The line (from 1) of each entry's heading in its file: "# x\n### J-001 y\n" gives {"J-001": 2}."""
    return {m.group(1): text[: m.start()].count("\n") + 1 for m in HEADING.finditer(text)}


def index_rows(files: dict[str, str]) -> list[str]:
    """One table row per entry in name order, its place as file:line: "| J-001 | Founding | decision | `J-001-010.md:3` |"."""
    rows = []
    for name in sorted(files):
        classes = {entry: fields.get("Class", "") for entry, fields in entries(files[name]).items()}
        lines = heading_lines(files[name])
        rows += [
            f"| {i} | {decisions.cell(title)} | {classes[i]} | `{name}:{lines[i]}` |" for i, title in TITLE.findall(files[name])
        ]
    return rows


HEADER = (
    "# Journal, one line each\n\n"
    f"Written by `{COMMAND}` from `docs/journal/`; do not edit here. The fields and the rules are in `docs/JOURNAL.md`.\n\n"
    "| Entry | Title | Class | File:line |\n| --- | --- | --- | --- |\n"
)


def render(files: dict[str, str]) -> str:
    """docs/journal/INDEX.md: the header and a row per entry."""
    return HEADER + "\n".join(index_rows(files)) + "\n"


def stale_problems(root: Path) -> list[str]:
    """[] when docs/journal/INDEX.md is exactly the index of the files; else one line naming the command."""
    index = root / "docs" / "journal" / "INDEX.md"
    if index.exists() and index.read_text() == render(read_files(root)):
        return []
    return [f"docs/journal/INDEX.md is stale or missing: run `{COMMAND}`"]
