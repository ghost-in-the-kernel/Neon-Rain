"""The journal's numbering and classes, the conflict rule (an open conflict states both objectives and is waiting on
Ghost in HANDOFF.md; CLAUDE.md, J-023), the ten-ids-a-file layout and the generated index (R-028 (4))."""
import subprocess
import sys
from pathlib import Path

from scripts.checks import journal

QUEUE = "## For Ghost: waiting on you\n\n1. J-002: two objectives.\n\n## Waiting on a run\n"


def entry(number: int, kind: str, extra: str = "") -> str:
    return f"### J-{number:03d} Something\n- **Who:** x\n{extra}- **Class:** {kind}\n\n"


CONFLICT = entry(2, "conflict", "- **Mine:** make split.py faster\n- **Theirs:** freeze split.py for 1.7\n")


def test_the_real_journal_holds(root: Path) -> None:
    files = journal.read_files(root)
    text = journal.joined(files)
    assert journal.problems(text, (root / "docs" / "HANDOFF.md").read_text()) == []
    assert journal.file_problems(files) == []
    assert len(journal.entries(text)) >= 51


def test_an_open_conflict_listed_for_ghost_holds() -> None:
    assert journal.problems(entry(1, "trial") + CONFLICT, QUEUE) == []


def test_an_open_conflict_not_listed_for_ghost_is_caught() -> None:
    found = journal.problems(entry(1, "trial") + CONFLICT, "## For Ghost\n\n1. R-011.\n## Waiting\n\nJ-002\n")
    assert found == ["J-002 is an open conflict not listed in HANDOFF.md's For Ghost section"]
    assert journal.problems(entry(1, "trial") + CONFLICT, "") == found


def test_a_conflict_resolved_by_ghost_need_not_wait() -> None:
    resolved = CONFLICT.replace("- **Class:**", "- **Resolved:** Ghost, 2026-10-24: freeze wins.\n- **Class:**")
    assert journal.problems(entry(1, "trial") + resolved, "") == []
    by_agent = CONFLICT.replace("- **Class:**", "- **Resolved:** the agents agreed.\n- **Class:**")
    assert journal.problems(entry(1, "trial") + by_agent, "")[0].startswith("J-002 is an open conflict")


def test_a_conflict_must_state_both_objectives() -> None:
    bare = entry(1, "trial") + entry(2, "conflict")
    assert journal.problems(bare, QUEUE) == [
        "J-002 is a conflict with no Mine objective", "J-002 is a conflict with no Theirs objective"
    ]


def test_unknown_classes_and_numbering_are_caught() -> None:
    assert journal.problems(entry(1, "sabotage"), "") == ["J-001 has class 'sabotage', not one of 10"]
    assert journal.problems(entry(1, "trial") + entry(3, "trial"), "") == ["entry 2 is J-003, expected J-002"]
    assert journal.problems(entry(1, "trial") + entry(1, "trial"), "") == ["entry 2 is J-001, expected J-002"]


def test_every_entry_is_read() -> None:
    text = entry(1, "trial") + entry(2, "nonsense") + entry(3, "rumour")
    assert journal.problems(text, "") == ["J-002 has class 'nonsense', not one of 10", "J-003 has class 'rumour', not one of 10"]
    assert journal.entries(entry(1, "trial"))["J-001"] == {"Who": "x", "Class": "trial"}


def test_an_entry_with_no_class_line_is_caught() -> None:
    assert journal.problems("### J-001 Something\n- **Who:** x\n\n", "") == ["J-001 has class '', not one of 10"]


def test_problems_of_every_kind_are_all_reported() -> None:
    text = entry(1, "trial") + entry(3, "conflict")
    assert journal.problems(text, "") == [
        "entry 2 is J-003, expected J-002",
        "J-003 is a conflict with no Mine objective",
        "J-003 is a conflict with no Theirs objective",
        "J-003 is an open conflict not listed in HANDOFF.md's For Ghost section",
    ]


def test_the_for_ghost_section_ends_at_the_next_heading() -> None:
    assert journal.waiting_on_ghost("# x\n## For Ghost: y\n1. J-002\n## Next\nJ-009\n") == "## For Ghost: y\n1. J-002\n"
    assert journal.waiting_on_ghost("# x\n## Other\n") == ""
    two = "## For Ghost: a\n1. J-002\n## Middle\n## For Ghost: b\n2. J-005\n"
    assert journal.waiting_on_ghost(two) == "## For Ghost: a\n1. J-002\n## For Ghost: b\n2. J-005\n"


def test_an_entry_belongs_in_the_file_its_number_names() -> None:
    assert [journal.file_name(n) for n in (1, 10, 11, 20, 51, 100, 101)] == [
        "J-001-010.md", "J-001-010.md", "J-011-020.md", "J-011-020.md", "J-051-060.md", "J-091-100.md", "J-101-110.md"
    ]
    right = {"J-001-010.md": entry(1, "trial") + entry(10, "trial"), "J-011-020.md": entry(11, "trial")}
    assert journal.file_problems(right) == []
    assert journal.file_problems({"J-091-100.md": entry(91, "trial") + entry(100, "trial")}) == []
    assert journal.file_problems({"J-091-100.md": entry(100, "trial") + entry(101, "trial")}) == [
        "J-101 is in J-091-100.md, expected J-101-110.md"
    ]
    wrong = {"J-001-010.md": entry(1, "trial") + entry(11, "trial"), "J-011-020.md": entry(10, "trial")}
    assert journal.file_problems(wrong) == [
        "J-011 is in J-001-010.md, expected J-011-020.md", "J-010 is in J-011-020.md, expected J-001-010.md"
    ]


def test_a_file_with_no_entry_is_caught() -> None:
    assert journal.file_problems({"J-001-010.md": "# Journal\n"}) == ["J-001-010.md holds no entry"]


def test_the_files_are_read_in_name_order_and_joined() -> None:
    assert journal.joined({"J-011-020.md": "b", "J-001-010.md": "a"}) == "ab"
    text = journal.joined({"J-011-020.md": entry(11, "trial"), "J-001-010.md": "".join(entry(n, "trial") for n in range(1, 11))})
    assert journal.number_problems(text) == []


def folder(tmp_path: Path, index: str | None) -> Path:
    """A throwaway root with two journal files and, if given, an index."""
    (tmp_path / "docs" / "journal").mkdir(parents=True)
    (tmp_path / "docs" / "journal" / "J-011-020.md").write_text(entry(11, "decision").replace("Something", "b | c"))
    (tmp_path / "docs" / "journal" / "J-001-010.md").write_text(entry(1, "trial") + entry(2, "conflict"))
    (tmp_path / "docs" / "journal" / "notes.md").write_text("### J-099 not a journal file\n")
    if index is not None:
        (tmp_path / "docs" / "journal" / "INDEX.md").write_text(index)
    return tmp_path


def test_the_index_has_a_row_per_entry_in_id_order(tmp_path: Path) -> None:
    files = journal.read_files(folder(tmp_path, None))
    assert list(files) == ["J-001-010.md", "J-011-020.md"]
    assert journal.render(files).removeprefix(journal.HEADER).splitlines() == [
        "| J-001 | Something | trial | `J-001-010.md:1` |",
        "| J-002 | Something | conflict | `J-001-010.md:5` |",
        "| J-011 | b \\| c | decision | `J-011-020.md:1` |",
    ]
    assert journal.render(files).endswith("|\n") and not journal.render(files).endswith("\n\n")
    assert journal.COMMAND in journal.HEADER and "docs/JOURNAL.md" in journal.HEADER


def test_an_entry_with_no_class_has_an_empty_class_cell() -> None:
    assert journal.index_rows({"J-001-010.md": "### J-001 Bare\n- **Who:** x\n"}) == ["| J-001 | Bare |  | `J-001-010.md:1` |"]


def test_an_entrys_line_is_its_heading_line_in_its_file() -> None:
    text = "# Journal\n\nintro\n### J-001 A\n- **Class:** trial\n\n### J-002 B\n- **Class:** trial\n"
    assert journal.heading_lines(text) == {"J-001": 4, "J-002": 7}
    assert journal.heading_lines("### J-001 A\n") == {"J-001": 1}
    assert journal.heading_lines("") == {}
    assert journal.heading_lines("\n### J-001 A\n\n### J-002 B\n") == {"J-001": 2, "J-002": 4}
    assert journal.index_rows({"J-001-010.md": text}) == [
        "| J-001 | A | trial | `J-001-010.md:4` |", "| J-002 | B | trial | `J-001-010.md:7` |"
    ]


def test_an_index_with_a_wrong_line_is_stale(tmp_path: Path) -> None:
    root = folder(tmp_path, None)
    index = root / "docs" / "journal" / "INDEX.md"
    index.write_text(journal.render(journal.read_files(root)))
    assert journal.stale_problems(root) == []
    index.write_text(index.read_text().replace("`J-001-010.md:5`", "`J-001-010.md:4`"))
    assert len(journal.stale_problems(root)) == 1


def test_a_stale_or_missing_index_is_caught_and_names_the_command(tmp_path: Path) -> None:
    root = folder(tmp_path, None)
    assert journal.stale_problems(root) == [f"docs/journal/INDEX.md is stale or missing: run `{journal.COMMAND}`"]
    (root / "docs" / "journal" / "INDEX.md").write_text(journal.render(journal.read_files(root)))
    assert journal.stale_problems(root) == []
    (root / "docs" / "journal" / "INDEX.md").write_text(journal.render(journal.read_files(root)) + "x\n")
    assert len(journal.stale_problems(root)) == 1


def test_the_real_index_is_current(root: Path) -> None:
    assert journal.stale_problems(root) == []


def test_the_command_writes_and_checks_the_index(tmp_path: Path, root: Path) -> None:
    (tmp_path / "scripts" / "checks").mkdir(parents=True)
    for name in ("journal_index.py", "checks/__init__.py", "checks/journal.py", "checks/decisions.py", "checks/ghost.py"):
        (tmp_path / "scripts" / name).write_text((root / "scripts" / name).read_text())
    folder(tmp_path, None)
    command = [sys.executable, "-I", str(tmp_path / "scripts" / "journal_index.py")]
    checked = subprocess.run(command + ["--check"], capture_output=True, text=True)
    assert checked.returncode == 1 and journal.COMMAND in checked.stdout
    written = subprocess.run(command, capture_output=True, text=True)
    assert written.returncode == 0 and "3 rows" in written.stdout
    checked = subprocess.run(command + ["--check"], capture_output=True, text=True)
    assert checked.returncode == 0 and "current" in checked.stdout
