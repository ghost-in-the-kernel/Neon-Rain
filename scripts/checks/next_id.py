"""The next free R-nnn or J-nnn, after fetching origin main so two sessions do not take one number (R-028 (2)).

The number is one past the largest heading id in the local file and in origin/main's copy. A failed fetch is
reported, and the local answer still stands, marked as not checked. Run by scripts/next_id.py.
"""
import re
import subprocess
from pathlib import Path

# Where each kind of record lives, relative to the repository root: a file, or a folder (a path ending in "/") whose
# .md files are all read. The journal is the folder docs/journal/, ten ids to a file (R-028 (4)).
KINDS: dict[str, tuple[str, tuple[str, ...]]] = {
    "decision": ("R", ("theGhost.md",)),
    "journal": ("J", ("docs/journal/",)),
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


def local_texts(root: Path, path: str) -> list[str]:
    """The texts at `path` in the working tree: one for a file, one per .md file for a folder."""
    if path.endswith("/"):
        return [p.read_text() for p in sorted((root / path).glob("*.md"))]
    return [local_text(root, path)]


def remote_texts(root: Path, path: str) -> list[str]:
    """The texts at `path` on origin/main: one for a file, one per .md file for a folder; none where it is not there."""
    if not path.endswith("/"):
        return [remote_text(root, path)]
    done = subprocess.run(["git", "-C", str(root), "ls-tree", "--name-only", "origin/main", path], capture_output=True, text=True)
    return [remote_text(root, name) for name in done.stdout.splitlines() if name.endswith(".md")]


def next_id(root: Path, kind: str) -> tuple[str, str | None]:
    """(the next id, None) when the fetch worked; (the next id from the local copies, the fetch's failure) when not."""
    prefix, paths = KINDS[kind]
    failure = fetch(root)
    texts = [t for p in paths for t in local_texts(root, p)]
    texts += [] if failure else [t for p in paths for t in remote_texts(root, p)]
    return format_id(prefix, max([highest(t, prefix) for t in texts], default=0) + 1), failure
