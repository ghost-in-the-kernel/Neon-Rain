"""CLAUDE.md's "When X happens, read Y" lines point at files that exist (test/test_pointers.py, J-028)."""
import re
from pathlib import Path

SECTION = re.compile(r"^## When .*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
PATH = re.compile(r"`([\w./-]+\.md)`")


def pointed(claude: str) -> list[str]:
    """The .md paths named in backticks in the When section, in order."""
    return [path for section in SECTION.findall(claude) for path in PATH.findall(section)]


def problems(claude: str, root: Path) -> list[str]:
    """Each pointed-at file that does not exist, and a CLAUDE.md with no When section."""
    found = [] if SECTION.search(claude) else ["CLAUDE.md has no 'When X happens, read Y' section"]
    return found + [f"CLAUDE.md points at {path}, which does not exist" for path in pointed(claude) if not (root / path).is_file()]
