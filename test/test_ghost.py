"""theGhost.md holds its shape; and each way it can break, planted, is caught (TODO 0.5)."""
from pathlib import Path

from scripts.checks import ghost


def entry(rid: str, status: str = "in force", subject: str = "method", extra: str = "") -> str:
    """A complete entry, e.g. entry("R-001") is a well-formed in-force decision on 'method'."""
    return (
        f"### {rid}: a decision\n- **Decision:** d\n- **Why:** w\n- **Held by:** h\n- **Source:** s\n"
        f"- **Status:** {status}\n- **See also:** R-001\n- **subject:** {subject}\n{extra}\n"
    )


def test_the_real_file_holds(root: Path) -> None:
    assert ghost.problems((root / "theGhost.md").read_text()) == []


def test_a_clean_pair_holds() -> None:
    assert ghost.problems(entry("R-001") + entry("R-002")) == []


def test_a_duplicated_id_is_caught() -> None:
    found = ghost.problems(entry("R-001") + entry("R-001"))
    assert "R-001 appears 2 times" in found


def test_a_gap_in_the_sequence_is_caught() -> None:
    assert ghost.problems(entry("R-001") + entry("R-003")) == ["entry 2 is R-003, expected R-002"]


def test_a_missing_field_is_caught() -> None:
    broken = entry("R-001").replace("- **Held by:** h\n", "")
    assert ghost.problems(broken) == ["R-001 has no Held by line"]


def test_an_unknown_status_is_caught() -> None:
    assert ghost.problems(entry("R-001", status="maybe")) == ["R-001 has status 'maybe', not one of the five"]


def test_a_one_sided_supersession_is_caught() -> None:
    text = entry("R-001", status="superseded by R-002") + entry("R-002").replace("R-001", "R-002")
    assert ghost.problems(text) == ["R-001 is superseded by R-002, which does not name it back"]


def test_a_supersession_by_nothing_is_caught() -> None:
    found = ghost.problems(entry("R-001", status="superseded by R-009"))
    assert found == ["R-001 is superseded by R-009, which does not exist"]


def test_a_two_sided_supersession_holds() -> None:
    assert ghost.problems(entry("R-001", status="superseded by R-002") + entry("R-002")) == []


def test_two_in_force_entries_in_conflict_are_caught_until_one_is_superseded() -> None:
    conflicting = entry("R-001") + entry("R-002", extra="- **conflicts-with:** R-001")
    assert ghost.problems(conflicting) == ["R-002 and R-001 are both in force on 'method' and conflict"]
    resolved = entry("R-001", status="superseded by R-002") + entry("R-002", extra="- **conflicts-with:** R-001")
    assert ghost.problems(resolved) == []


def test_a_conflict_across_subjects_is_not_one() -> None:
    text = entry("R-001", subject="toolchain") + entry("R-002", extra="- **conflicts-with:** R-001")
    assert ghost.problems(text) == []


def test_a_conflict_with_no_entry_is_caught() -> None:
    found = ghost.problems(entry("R-001", extra="- **conflicts-with:** R-009"))
    assert found == ["R-001 conflicts with R-009, which does not exist"]


def test_a_conflict_after_an_entry_that_is_not_in_force_is_still_caught() -> None:
    text = entry("R-001", status="proposed") + entry("R-002") + entry("R-003", extra="- **conflicts-with:** R-002")
    assert ghost.problems(text) == ["R-003 and R-002 are both in force on 'method' and conflict"]


def test_a_proposed_entry_in_conflict_is_not_one_yet() -> None:
    assert ghost.problems(entry("R-001") + entry("R-002", status="proposed", extra="- **conflicts-with:** R-001")) == []


def test_problems_in_several_entries_are_all_reported() -> None:
    text = entry("R-001", status="maybe") + entry("R-002").replace("- **Why:** w\n", "") + entry("R-003", status="later")
    assert ghost.problems(text) == [
        "R-001 has status 'maybe', not one of the five",
        "R-002 has no Why line",
        "R-003 has status 'later', not one of the five",
    ]


def test_an_entry_with_no_status_line_is_reported_once() -> None:
    assert ghost.problems(entry("R-001").replace("- **Status:** in force\n", "")) == ["R-001 has no Status line"]


def test_entries_are_split_at_their_headings() -> None:
    assert ghost.split_entries("intro\n### R-001: a\nx\n### R-002: b\ny\n") == {
        "R-001": "### R-001: a\nx\n", "R-002": "### R-002: b\ny\n"
    }


def test_every_name_on_a_conflicts_line_is_read() -> None:
    text = entry("R-001") + entry("R-002", extra="- **conflicts-with:** R-009, R-001")
    assert ghost.problems(text) == [
        "R-002 conflicts with R-009, which does not exist",
        "R-002 and R-001 are both in force on 'method' and conflict",
    ]
