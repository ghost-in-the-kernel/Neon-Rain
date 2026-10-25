"""scripts/next_id.py gives the next number after the larger of the local and origin/main copies (R-028 (2))."""
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.checks import next_id


def git(cwd: Path, args: list[str]) -> None:
    """Runs git in cwd, quietly and with a fixed author."""
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(cwd)] + args, check=True, capture_output=True)


def log(last: int, prefix: str = "R") -> str:
    """A log whose headings run 1 to `last`, with a stray mention of a larger id that is not a heading."""
    return "".join(f"### {prefix}-{n:03d}: t\nbody mentions {prefix}-099\n" for n in range(1, last + 1))


@pytest.fixture
def repos(tmp_path: Path) -> tuple[Path, Path]:
    """(a clone, a second clone) of a bare remote holding theGhost.md with R-001..R-003 and docs/JOURNAL.md with J-001..J-002."""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, ["init", "-q", "-b", "main"])
    (seed / "docs").mkdir()
    (seed / "theGhost.md").write_text(log(3))
    (seed / "docs" / "JOURNAL.md").write_text(log(2, "J"))
    git(seed, ["add", "."])
    git(seed, ["commit", "-q", "-m", "seed"])
    git(seed, ["push", "-q", str(remote), "main"])
    for name in ("a", "b"):
        subprocess.run(["git", "clone", "-q", str(remote), str(tmp_path / name)], check=True)
    return tmp_path / "a", tmp_path / "b"


def test_highest_counts_headings_only() -> None:
    assert next_id.highest("### J-004 x\n### J-010 y\nJ-099 in prose\n", "J") == 10
    assert next_id.highest("nothing", "J") == 0
    assert next_id.highest("### R-004: x\n", "J") == 0


def test_format_pads_to_three_digits() -> None:
    assert next_id.format_id("R", 9) == "R-009"
    assert next_id.format_id("J", 1000) == "J-1000"


def test_the_local_number_wins_when_main_is_behind(repos: tuple[Path, Path]) -> None:
    a, _ = repos
    (a / "theGhost.md").write_text(log(5))
    assert next_id.next_id(a, "decision") == ("R-006", None)


def test_the_fetched_number_wins_when_local_is_behind(repos: tuple[Path, Path]) -> None:
    a, b = repos
    (b / "theGhost.md").write_text(log(7))
    (b / "docs" / "JOURNAL.md").write_text(log(4, "J"))
    git(b, ["commit", "-q", "-a", "-m", "more"])
    git(b, ["push", "-q", "origin", "main"])
    assert next_id.next_id(a, "decision") == ("R-008", None)
    assert next_id.next_id(a, "journal") == ("J-005", None)


def test_a_failed_fetch_is_reported_and_the_local_answer_stands(repos: tuple[Path, Path]) -> None:
    a, _ = repos
    git(a, ["remote", "set-url", "origin", str(a / "nowhere.git")])
    found, failure = next_id.next_id(a, "decision")
    assert found == "R-004"
    assert isinstance(failure, str) and "nowhere.git" in failure


def test_a_failed_fetch_ignores_a_stale_remote_ref(repos: tuple[Path, Path]) -> None:
    a, b = repos
    (b / "theGhost.md").write_text(log(7))
    git(b, ["commit", "-q", "-a", "-m", "more"])
    git(b, ["push", "-q", "origin", "main"])
    next_id.fetch(a)
    git(a, ["remote", "set-url", "origin", str(a / "nowhere.git")])
    assert next_id.next_id(a, "decision")[0] == "R-004"


def test_a_missing_file_counts_as_none(tmp_path: Path) -> None:
    assert next_id.local_text(tmp_path, "theGhost.md") == ""
    assert next_id.remote_text(tmp_path, "theGhost.md") == ""


def test_the_command_prints_the_id_here(root: Path) -> None:
    done = subprocess.run([sys.executable, "-I", str(root / "scripts" / "next_id.py"), "decision"], capture_output=True, text=True)
    assert done.returncode == 0 and done.stdout.startswith("R-0")


def test_the_command_refuses_another_kind(root: Path) -> None:
    done = subprocess.run([sys.executable, "-I", str(root / "scripts" / "next_id.py"), "tithe"], capture_output=True, text=True)
    assert done.returncode == 2 and "usage" in done.stderr


def test_the_command_marks_an_unchecked_answer(tmp_path: Path, root: Path) -> None:
    # A copy of the scripts in a repository with no origin: the fetch fails.
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "next_id.py").write_text((root / "scripts" / "next_id.py").read_text())
    (tmp_path / "scripts" / "checks").mkdir()
    (tmp_path / "scripts" / "checks" / "__init__.py").write_text("")
    (tmp_path / "scripts" / "checks" / "next_id.py").write_text((root / "scripts" / "checks" / "next_id.py").read_text())
    (tmp_path / "theGhost.md").write_text(log(2))
    git(tmp_path, ["init", "-q"])
    done = subprocess.run([sys.executable, "-I", str(tmp_path / "scripts" / "next_id.py"), "decision"], capture_output=True, text=True)
    assert done.stdout.strip() == "R-003 (local copy only; NOT checked against main)"
    assert "fetch of origin main failed" in done.stderr
