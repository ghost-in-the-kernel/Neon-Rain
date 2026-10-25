"""scripts/commit.sh refuses any commit but a `tithe:` one while a tithe is due (R-012, R-028 (1)), in a throwaway repo."""
import os
import subprocess
from pathlib import Path

import pytest

from scripts import commit_guard

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "commit.sh"
ENV = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "XDG_"))}
ENV.update(HOME="/nonexistent", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")


def run(repo: Path, args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    """scripts/commit.sh run in repo."""
    return subprocess.run([str(SCRIPT), *args], cwd=repo, env=ENV, capture_output=True, text=True, input=stdin)


def git(repo: Path, args: list[str]) -> str:
    """Stdout of git in repo."""
    return subprocess.run(["git", *args], cwd=repo, env=ENV, capture_output=True, text=True, check=True).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A fresh git repository with no commit and no author configured."""
    git(tmp_path, ["init", "-q"])
    return tmp_path


def commit(repo: Path, subject: str) -> subprocess.CompletedProcess:
    """An empty commit with this subject, through the script."""
    return run(repo, ["--allow-empty", "-m", subject])


def test_seven_pass_and_the_eighth_is_refused(repo: Path) -> None:
    for n in range(7):
        assert commit(repo, f"work {n}").returncode == 0
    done = commit(repo, "work 7")
    assert done.returncode == 1
    assert "docs/rules/tithe.md" in done.stdout and "tithe is due" in done.stdout
    assert git(repo, ["rev-list", "--count", "HEAD"]).strip() == "7"


def test_a_tithe_is_accepted_when_due_and_resets_the_count(repo: Path) -> None:
    for n in range(7):
        commit(repo, f"work {n}")
    assert commit(repo, "tithe: tidy").returncode == 0
    assert run(repo, ["--check"]).returncode == 0
    for n in range(7):
        assert commit(repo, f"more {n}").returncode == 0
    assert commit(repo, "more 7").returncode == 1


def test_a_tithe_is_accepted_when_not_due(repo: Path) -> None:
    assert commit(repo, "work").returncode == 0
    assert commit(repo, "tithe: early").returncode == 0


def test_no_tithe_yet_counts_from_the_first_commit(repo: Path) -> None:
    assert run(repo, ["--check"]).stdout.startswith("commit: 0 of 7")
    commit(repo, "one")
    assert run(repo, ["--check"]).stdout.startswith("commit: 1 of 7")


def test_check_reports_a_due_tithe_and_commits_nothing(repo: Path) -> None:
    for n in range(7):
        commit(repo, f"work {n}")
    done = run(repo, ["--check"])
    assert done.returncode == 1 and "tithe is due" in done.stdout
    assert git(repo, ["rev-list", "--count", "HEAD"]).strip() == "7"


def test_a_commit_is_authored_as_ghost_when_no_config_names_anyone(repo: Path) -> None:
    commit(repo, "work")
    assert git(repo, ["log", "-1", "--format=%an <%ae>"]).strip() == (
        "Ghost <118085043+ghost-in-the-kernel@users.noreply.github.com>")
    assert subprocess.run(["git", "config", "user.name"], cwd=repo, env=ENV, capture_output=True).returncode == 1


def test_configured_author_is_kept(repo: Path) -> None:
    git(repo, ["config", "user.name", "Someone"])
    git(repo, ["config", "user.email", "s@example.org"])
    commit(repo, "work")
    assert git(repo, ["log", "-1", "--format=%an <%ae>"]).strip() == "Someone <s@example.org>"


def test_message_from_a_file_and_from_stdin(repo: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    for n in range(7):
        commit(repo, f"work {n}")
    message = tmp_path_factory.mktemp("msg") / "m.txt"
    message.write_text("work 7\n\nbody\n")
    assert run(repo, ["--allow-empty", "-F", str(message)]).returncode == 1
    assert run(repo, ["--allow-empty", "-F", "-"], stdin="work 7\n").returncode == 1
    done = run(repo, ["--allow-empty", "-F", "-"], stdin="tithe: from stdin\n\nbody\n")
    assert done.returncode == 0
    assert git(repo, ["log", "-1", "--format=%B"]).startswith("tithe: from stdin\n\nbody")


def test_the_count_stops_at_the_newest_tithe() -> None:
    assert commit_guard.since_last_tithe(["work", "tithe: x", "old"]) == 1
    assert commit_guard.since_last_tithe([]) == 0


@pytest.mark.parametrize("args, subject", [
    (["-m", "tithe: a\n\nb"], "tithe: a"), (["--message=tithe: a"], "tithe: a"), (["-mtithe: a"], "tithe: a"),
    (["--allow-empty"], ""), (["-m"], ""), (["-F", "/no/such/file"], ""), ([], ""),
])
def test_subject_of(args: list[str], subject: str) -> None:
    assert commit_guard.subject_of(args) == subject

