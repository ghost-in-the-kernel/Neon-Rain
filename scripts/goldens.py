"""Check the goldens against the harness, or write them (docs/HARNESS.md HAR-14, AGT-05).

    .venv/bin/python scripts/goldens.py                       # exit 1 and say how each golden differs
    .venv/bin/python scripts/goldens.py --write               # the freeze: the first write, no decision
    .venv/bin/python scripts/goldens.py --write --decision R-0nn   # a change, under a decision in force

--write refuses a change to a golden that comes with no decision in force in theGhost.md.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from neonrain.harness import goldens  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / "harness" / "goldens"


def main() -> int:
    parser = argparse.ArgumentParser(description="the harness's goldens")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--decision", default=None)
    options = parser.parse_args()
    files = goldens.compute()
    ghost = (ROOT / "theGhost.md").read_text()
    if options.write:
        try:
            written = goldens.write(DIRECTORY, files, ghost, options.decision)
        except goldens.GoldenChange as refused:
            print(f"goldens: refused: {refused}")
            return 1
        print(f"goldens: wrote {len(written)} of {len(files)}")
        return 0
    problems = goldens.check(DIRECTORY, files, ghost)
    print("\n".join(problems) if problems else f"goldens: {len(files)} identical")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
