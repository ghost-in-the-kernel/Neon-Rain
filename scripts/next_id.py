"""Prints the next free decision (R-nnn) or journal (J-nnn) id, after fetching origin main (R-028 (2)).

Run: python3 -I scripts/next_id.py decision
     python3 -I scripts/next_id.py journal
Take an id from it before writing the entry. If the fetch fails it says so and prints the local answer.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.checks import next_id  # noqa: E402


def main(argv: list[str]) -> int:
    """Prints the id; exit 2 for a kind that is not decision or journal."""
    if len(argv) != 1 or argv[0] not in next_id.KINDS:
        print("usage: next_id.py decision|journal", file=sys.stderr)
        return 2
    found, failure = next_id.next_id(ROOT, argv[0])
    if failure:
        print(f"fetch of origin main failed: {failure}", file=sys.stderr)
        print(f"{found} (local copy only; NOT checked against main)")
    else:
        print(found)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
