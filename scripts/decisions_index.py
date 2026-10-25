"""Writes docs/decisions.md, one line per entry of theGhost.md (R-028 (2)); with --check it only compares.

Run: python3 -I scripts/decisions_index.py          writes the index
     python3 -I scripts/decisions_index.py --check  exit 1 when the index is stale
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.checks import decisions  # noqa: E402


def main(argv: list[str]) -> int:
    """Writes the index, or with --check reports whether it is current: 0 when current, 1 when stale."""
    if "--check" in argv:
        found = decisions.stale_problems(ROOT)
        print("\n".join(found) or "docs/decisions.md is current")
        return 1 if found else 0
    text = decisions.render((ROOT / "theGhost.md").read_text())
    (ROOT / "docs" / "decisions.md").write_text(text)
    print(f"wrote docs/decisions.md, {text.count(chr(10)) - decisions.HEADER.count(chr(10))} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
