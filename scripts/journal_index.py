"""Writes docs/journal/INDEX.md, one line per journal entry (R-028 (4)); with --check it only compares.

Run: python3 -I scripts/journal_index.py          writes the index
     python3 -I scripts/journal_index.py --check  exit 1 when the index is stale
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.checks import journal  # noqa: E402


def main(argv: list[str]) -> int:
    """Writes the index, or with --check reports whether it is current: 0 when current, 1 when stale."""
    if "--check" in argv:
        found = journal.stale_problems(ROOT)
        print("\n".join(found) or "docs/journal/INDEX.md is current")
        return 1 if found else 0
    text = journal.render(journal.read_files(ROOT))
    (ROOT / "docs" / "journal" / "INDEX.md").write_text(text)
    print(f"wrote docs/journal/INDEX.md, {text.count(chr(10)) - journal.HEADER.count(chr(10))} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
