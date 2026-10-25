"""The tithe guard's count and verdict (R-012, R-028 (1)), called by scripts/commit.sh; never a git hook.

R-012: every eighth commit is a tithe. The commits since the last one whose subject starts `tithe:` are
counted (merges not counted; all of them when there is none yet). A tithe is DUE once seven have landed,
because the next commit would be the eighth. A `tithe:` commit is always accepted; any other is refused
while a tithe is due. Kept under scripts/ and not scripts/checks/: it is not a document check, and
test/test_commit_script.py drives it through scripts/commit.sh against throwaway repositories.

Usage: commit_guard.py [git commit arguments]   exit 0 to go on, 1 refused. With --check: report only.
"""
import subprocess
import sys

EVERY = 8
PREFIX = "tithe:"


def since_last_tithe(subjects: list[str]) -> int:
    """Commits before the first subject starting `tithe:`, newest first; all of them if none."""
    for n, subject in enumerate(subjects):
        if subject.startswith(PREFIX):
            return n
    return len(subjects)


def subject_of(args: list[str]) -> str:
    """The first line of the message in git-commit arguments: -m, --message, -F or --file (never `-`); else empty."""
    for i, arg in enumerate(args):
        value = None
        if arg in ("-m", "--message", "-F", "--file"):
            value = args[i + 1] if i + 1 < len(args) else ""
        elif arg.startswith("--message="):
            value = arg[len("--message="):]
        elif arg.startswith("--file="):
            value = arg[len("--file="):]
        elif arg.startswith(("-m", "-F")):
            value = arg[2:]
        if value is None:
            continue
        if arg.startswith(("-F", "--file")):
            try:
                with open(value) as f:
                    value = f.readline()
            except OSError:
                return ""
        return value.lstrip().split("\n", 1)[0]
    return ""


def verdict(subject: str, count: int) -> tuple[bool, str]:
    """Whether the commit may go on, and the line to say."""
    if subject.startswith(PREFIX):
        return True, f"commit: tithe accepted ({count} commits since the last tithe)"
    if count >= EVERY - 1:
        return False, (
            f"commit: refused; a tithe is due ({count} commits since the last `tithe:` commit; every {EVERY}th "
            f"commit is a tithe, R-012, so after {EVERY - 1} the next one must start `{PREFIX}`). "
            "Read docs/rules/tithe.md, make the tithe commit, then this one."
        )
    return True, f"commit: {count} of {EVERY - 1} commits since the last tithe; the {EVERY}th is the tithe"


def history() -> list[str]:
    """Subjects of the non-merge commits on HEAD, newest first; none in a repository with no commit."""
    done = subprocess.run(["git", "log", "--no-merges", "--format=%s"], capture_output=True, text=True)
    return done.stdout.splitlines() if done.returncode == 0 else []


def main(argv: list[str]) -> int:
    """Print the verdict; 0 to go on, 1 if refused. --check reports a commit of any other kind and commits nothing."""
    check = argv[:1] == ["--check"]
    ok, line = verdict("" if check else subject_of(argv), since_last_tithe(history()))
    print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
