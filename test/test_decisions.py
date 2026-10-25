"""docs/decisions.md is the generated index of theGhost.md, and a stale one is caught (R-028 (2), AGT-05)."""
import subprocess
import sys
from pathlib import Path

from scripts.checks import decisions

LOG = (
    "# Log\n\n"
    "### R-001: first | with a bar\n- **Decision:** d\n- **Status:** in force\n- **subject:** method\n\n"
    "### R-002: second\n- **Decision:** d\n- **Status:** superseded by R-003\n- **subject:** data\n\n"
    "### R-003: third, no subject\n- **Status:** proposed\n\n"
    "### R-004: a: colon in the title\n- **Decision:** d\n"
)


def project(tmp_path: Path, index: str | None) -> Path:
    """A throwaway root holding the invented log and, if given, an index."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "theGhost.md").write_text(LOG)
    if index is not None:
        (tmp_path / "docs" / "decisions.md").write_text(index)
    return tmp_path


def test_the_index_has_a_row_per_entry_in_file_order() -> None:
    rows = decisions.render(LOG).removeprefix(decisions.HEADER).splitlines()
    assert rows == [
        "| R-001 | first \\| with a bar | in force | method |",
        "| R-002 | second | superseded by R-003 | data |",
        "| R-003 | third, no subject | proposed |  |",
        "| R-004 | a: colon in the title |  |  |",
    ]


def test_the_header_names_the_command_and_ends_the_text_with_one_newline() -> None:
    text = decisions.render(LOG)
    assert text.startswith("# Decisions, one line each\n")
    assert decisions.COMMAND in decisions.HEADER
    assert text.endswith("|\n") and not text.endswith("\n\n")


def test_a_current_index_holds(tmp_path: Path) -> None:
    assert decisions.stale_problems(project(tmp_path, decisions.render(LOG))) == []


def test_a_stale_index_is_caught_and_names_the_command(tmp_path: Path) -> None:
    stale = decisions.render(LOG).replace("| second |", "| old title |")
    assert decisions.stale_problems(project(tmp_path, stale)) == [
        f"docs/decisions.md is stale or missing: run `{decisions.COMMAND}`"
    ]


def test_a_missing_index_is_caught(tmp_path: Path) -> None:
    assert len(decisions.stale_problems(project(tmp_path, None))) == 1


def test_the_real_index_is_current(root: Path) -> None:
    assert decisions.stale_problems(root) == []


def test_the_command_checks_the_real_index(root: Path) -> None:
    done = subprocess.run([sys.executable, "-I", str(root / "scripts" / "decisions_index.py"), "--check"], capture_output=True, text=True)
    assert (done.returncode, done.stdout.strip()) == (0, "docs/decisions.md is current")
