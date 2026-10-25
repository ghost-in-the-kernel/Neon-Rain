"""docs/ESCALATIONS.md holds, and planted breaks in each rule are caught (R-028 (3))."""
from pathlib import Path

from scripts.checks import escalations

HEAD = "| Date | Journal | Task | Kind | Route taken | What was found | Status |\n| --- | --- | --- | --- | --- | --- | --- |\n"
ASKING = "## For Ghost: waiting on you\n\n1. Three escalations of `hard` have no fix: a routing pass.\n\n## Waiting on a run\n"


def row(kind: str = "hard", status: str = "open", journal: str = "J-032", date: str = "2026-10-23") -> str:
    """One register row: row() gives an open `hard` row citing J-032."""
    return f"| {date} | {journal} | task | {kind} | route | found | {status} |\n"


def test_the_real_register_holds(root: Path) -> None:
    register = (root / "docs" / "ESCALATIONS.md").read_text()
    assert escalations.problems(register, (root / "docs" / "HANDOFF.md").read_text()) == []
    assert escalations.rows(register), "the back-filled J-032 row is there"


def test_a_register_of_good_rows_holds() -> None:
    register = HEAD + row("hard") + row("not-read", "fixed the row") + row("no-advisor", "Ghost 2026-10-25: briefed")
    assert escalations.problems(register, "") == []


def test_an_unknown_kind_is_caught() -> None:
    assert escalations.problems(HEAD + row("vibes"), "") == ["the row on 2026-10-23 has kind 'vibes', not one of 6"]


def test_conflict_is_not_a_kind() -> None:
    assert escalations.problems(HEAD + row("conflict"), "") == ["the row on 2026-10-23 has kind 'conflict', not one of 6"]


def test_an_empty_cell_is_caught() -> None:
    broken = HEAD + "| 2026-10-23 | J-032 | task | hard |  | found | open |\n"
    assert escalations.problems(broken, "") == ["the row on 2026-10-23 has an empty Route taken cell"]


def test_a_missing_field_is_caught() -> None:
    assert escalations.problems(HEAD + "| 2026-10-23 | J-032 | task | hard | route | found |\n", "") == ["a row on 2026-10-23 has 6 cells, not 7"]


def test_a_journal_cell_that_is_no_j_number_is_caught() -> None:
    assert escalations.problems(HEAD + row(journal="somewhere"), "") == ["the row on 2026-10-23 cites 'somewhere', not a J-number"]


def test_a_status_that_is_none_of_the_three_is_caught() -> None:
    assert escalations.problems(HEAD + row(status="maybe"), "") == ["the row on 2026-10-23 has status 'maybe', not open, fixed or Ghost"]


def test_a_status_may_carry_punctuation_after_its_word() -> None:
    assert escalations.problems(HEAD + row(status="fixed: the pointer"), "") == []


def test_a_wrong_header_and_a_missing_table_are_caught() -> None:
    assert escalations.problems("| Date | Kind |\n| --- | --- |\n", "") == ["the table's columns are ['Date', 'Kind'], not " + str(list(escalations.COLUMNS))]
    assert escalations.problems("no table here\n", "") == ["docs/ESCALATIONS.md has no table headed Date"]


def test_a_table_not_headed_date_is_not_the_register() -> None:
    assert escalations.rows("| Id | Kind |\n| --- | --- |\n| a | b |\n") == []


def test_two_open_of_a_kind_hold_and_three_without_a_for_ghost_item_are_caught() -> None:
    two = HEAD + row() * 2
    assert escalations.problems(two, "") == []
    three = two + row()
    message = "3 open escalations of kind 'hard' and no numbered For Ghost item about escalations names it"
    assert escalations.problems(three, "") == [message]
    assert escalations.problems(three, ASKING) == []


def test_the_for_ghost_item_must_be_about_escalations_and_name_the_kind() -> None:
    three = HEAD + row() * 3
    other_kind = ASKING.replace("`hard`", "`not-read`")
    unrelated = ASKING.replace("escalations", "things")
    outside = "## Waiting on a run\n\n1. Three escalations of `hard`.\n"
    for handoff in (other_kind, unrelated, outside):
        assert len(escalations.problems(three, handoff)) == 1


def test_an_item_naming_the_kind_in_another_item_does_not_count() -> None:
    handoff = "## For Ghost: waiting on you\n\n1. Escalations are a topic.\n2. A `hard` thing, unrelated.\n"
    assert len(escalations.problems(HEAD + row() * 3, handoff)) == 1


def test_fixed_and_ghost_resolved_rows_do_not_count() -> None:
    register = HEAD + row() + row(status="fixed the row") + row(status="Ghost 2026-10-26: routed")
    assert escalations.problems(register, "") == []


def test_each_kind_is_counted_on_its_own() -> None:
    register = HEAD + row("hard") * 2 + row("not-read") * 2
    assert escalations.problems(register, "") == []


def test_every_bad_row_is_reported_not_only_the_last() -> None:
    assert len(escalations.problems(HEAD + row("vibes") + row("hmm", date="2026-10-24"), "")) == 2


def test_two_tables_headed_date_are_both_read() -> None:
    assert len(escalations.rows(HEAD + row() + "\n" + HEAD + row() + row())) == 3


def test_a_status_word_must_be_exact() -> None:
    assert escalations.problems(HEAD + row(status="openX"), "") == ["the row on 2026-10-23 has status 'openX', not open, fixed or Ghost"]
    for status in ("open: waiting", "fixed, by the row", "Ghost; routed"):
        assert escalations.problems(HEAD + row(status=status), "") == []
