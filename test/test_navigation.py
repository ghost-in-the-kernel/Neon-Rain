"""docs/NAVIGATION-LOG.md holds its shape: a review commit, and every debrief with its four fields (J-027)."""
from pathlib import Path

from scripts.checks import navigation

HEAD = "# Navigation log\n\nLast review: 10fd67e (2026-10-23)\n\n## Entries\n\n"
ONE = "### 2026-10-24 1.6 (Claude Sonnet)\n- **Task:** 1.6\n- **Opened:** CLAUDE.md, TODO.md\n- **Complaints:** none\n- **Suggestions:** none\n\n"


def test_the_real_log_holds(root: Path) -> None:
    assert navigation.problems((root / "docs" / "NAVIGATION-LOG.md").read_text()) == []


def test_a_complete_debrief_holds() -> None:
    assert navigation.problems(HEAD + ONE + ONE.replace("1.6 (", "1.7 (")) == []
    assert navigation.last_review(HEAD) == "10fd67e"


def test_a_debrief_missing_a_field_is_caught() -> None:
    found = navigation.problems(HEAD + ONE.replace("- **Complaints:** none\n", "") + ONE.replace("none\n- **S", "\n- **S"))
    assert found == ["debrief '2026-10-24 1.6 (Claude Sonnet)' has no Complaints"] * 2


def test_no_review_line_is_caught() -> None:
    missing = ["not exactly one 'Last review: <commit> (…)' line"]
    assert navigation.problems("# Navigation log\n\n## Entries\n\n") == missing
    assert navigation.problems("Last review: notahash (x)\n## Entries\n") == missing
    assert navigation.problems("Last review: abc1234 (x)\nLast review: def5678 (y)\n## Entries\n") == missing


def test_entries_are_read_only_under_the_entries_heading() -> None:
    assert navigation.debriefs("### not one\n" + HEAD + ONE) == [
        ("2026-10-24 1.6 (Claude Sonnet)", {"Task": "1.6", "Opened": "CLAUDE.md, TODO.md", "Complaints": "none", "Suggestions": "none"})
    ]
    assert navigation.debriefs(HEAD) == []
    assert [h for h, _ in navigation.debriefs(HEAD + ONE + "\n## Entries\n\n" + ONE)] == [
        "2026-10-24 1.6 (Claude Sonnet)", "2026-10-24 1.6 (Claude Sonnet)"]
