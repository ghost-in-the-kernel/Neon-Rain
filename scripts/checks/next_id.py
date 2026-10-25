"""The next free R-nnn or J-nnn, after fetching origin main so two sessions do not take one number (R-028 (2)).

The number is one past the largest heading id in the local file and in origin/main's copy. A failed fetch is
reported, and the local answer still stands, marked as not checked. Run by scripts/next_id.py.
"""
import re
import subprocess
from pathlib import Path

# Where each kind of record lives, relative to the repository root. Item (4) of R-028 splits the journal into
# numbered files: it changes the "journal" paths here and nothing else.
KINDS: dict[str, tuple[str, tuple[str, ...]]] = {
    "decision": ("R", ("theGhost.md",)),
    "journal": ("J", ("docs/JOURNAL.md",)),
}


def highest(text: str, prefix: str) -> int:
    """The largest number among `### P-nnn` headings: highest("### J-004 x\\n### J-010 y", "J") gives 10; none gives 0."""
    found = [int(n) for n in re.findall(rf"^### {prefix}-(\d+)\b", text, re.MULTILINE)]
    return max(found, default=0)


def format_id(prefix: str, number: int) -> str:
    """format_id("R", 29) gives "R-029"."""
    return f"{prefix}-{number:03d}"


def fetch(root: Path) -> str | None:
    """Fetches origin main; None when it worked, else the reason it did not."""
    done = subprocess.run(["git", "-C", str(root), "fetch", "-q", "origin", "main"], capture_output=True, text=True)
    return None if done.returncode == 0 else (done.stderr.strip() or f"git fetch exited {done.returncode}")


def remote_text(root: Path, path: str) -> str:
    """A file's text on origin/main; empty when the ref or the file is not there (git then prints nothing to stdout)."""
    done = subprocess.run(["git", "-C", str(root), "show", f"origin/main:{path}"], capture_output=True, text=True)
    return done.stdout


def local_text(root: Path, path: str) -> str:
    """A file's text in the working tree; empty when it is not there."""
    file = root / path
    return file.read_text() if file.is_file() else ""


def next_id(root: Path, kind: str) -> tuple[str, str | None]:
    """(the next id, None) when the fetch worked; (the next id from the local copies, the fetch's failure) when not."""
    prefix, paths = KINDS[kind]
    failure = fetch(root)
    texts = [local_text(root, p) for p in paths] + ([] if failure else [remote_text(root, p) for p in paths])
    return format_id(prefix, max(highest(t, prefix) for t in texts) + 1), failure
