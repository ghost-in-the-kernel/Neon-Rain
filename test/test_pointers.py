"""CLAUDE.md's situational pointers reach real files (J-028): a pointer to nothing costs an agent a wasted read."""
from pathlib import Path

from scripts.checks import pointers

CLAUDE = "# x\n\n## When X happens, read Y\n\n- A: `docs/a.md`.\n- B: `docs/rules/b.md` (R-1).\n\n## Next\n\n`docs/c.md`\n"


def test_the_real_pointers_hold(root: Path) -> None:
    text = (root / "CLAUDE.md").read_text()
    assert pointers.problems(text, root) == []
    assert "docs/rules/escalation.md" in pointers.pointed(text) and "docs/rules/conflict.md" in pointers.pointed(text)


def test_only_the_when_section_is_read() -> None:
    assert pointers.pointed(CLAUDE) == ["docs/a.md", "docs/rules/b.md"]


def test_a_pointer_to_nothing_is_caught(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("")
    assert pointers.problems(CLAUDE, tmp_path) == ["CLAUDE.md points at docs/rules/b.md, which does not exist"]
    (tmp_path / "docs" / "rules").mkdir()
    (tmp_path / "docs" / "rules" / "b.md").mkdir()
    assert pointers.problems(CLAUDE, tmp_path) == ["CLAUDE.md points at docs/rules/b.md, which does not exist"]


def test_no_when_section_is_caught(tmp_path: Path) -> None:
    assert pointers.problems("# x\n\n## Other\n", tmp_path) == ["CLAUDE.md has no 'When X happens, read Y' section"]
