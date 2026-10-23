"""The journal's numbering and classes, and the conflict rule: an open conflict states both objectives and is
waiting on Ghost in HANDOFF.md (CLAUDE.md; J-023)."""
from pathlib import Path

from scripts.checks import journal

QUEUE = "## For Ghost: waiting on you\n\n1. J-002: two objectives.\n\n## Waiting on a run\n"


def entry(number: int, kind: str, extra: str = "") -> str:
    return f"### J-{number:03d} Something\n- **Who:** x\n{extra}- **Class:** {kind}\n\n"


CONFLICT = entry(2, "conflict", "- **Mine:** make split.py faster\n- **Theirs:** freeze split.py for 1.7\n")


def test_the_real_journal_holds(root: Path) -> None:
    text = (root / "docs" / "JOURNAL.md").read_text()
    assert journal.problems(text, (root / "docs" / "HANDOFF.md").read_text()) == []
    assert len(journal.entries(text)) >= 22


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
