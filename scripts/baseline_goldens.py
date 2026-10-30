"""The baselines' goldens and RESULTS.md's baseline table, off harness/trials.tsv (TODO 3.3; HAR-13, HAR-14).

    .venv/bin/python scripts/baseline_goldens.py                  # exit 1 and say what disagrees (no data is read)
    .venv/bin/python scripts/baseline_goldens.py --write          # write the four goldens under step 3.3
    .venv/bin/python scripts/baseline_goldens.py --write --decision R-0nn   # a changed one, under a decision in force
    .venv/bin/python scripts/baseline_goldens.py --table          # print the table RESULTS.md must hold

The logic is scripts/checks/baseline_results.py; this only reads and writes the files.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from neonrain.harness import goldens  # noqa: E402
from scripts.checks import baseline_results as results  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / "harness" / "goldens"
STEP = "3.3"


def main() -> int:
    parser = argparse.ArgumentParser(description="the baselines' goldens and results table")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--table", action="store_true")
    parser.add_argument("--decision", default=None)
    options = parser.parse_args()
    trials = (ROOT / results.SOURCE).read_text()
    texts = {results.golden_name(name): results.golden(trials, name, runs) for name, runs in results.BASELINES.items()}
    if options.table:
        print(results.table(texts), end="")
        return 0
    if options.write:
        try:
            written = goldens.write_held(DIRECTORY, texts, (ROOT / "theGhost.md").read_text(), options.decision or STEP)
        except goldens.GoldenChange as refused:
            print(f"baseline goldens: refused: {refused}")
            return 1
        print(f"baseline goldens: wrote {len(written)} of {len(texts)}")
        return 0
    held = {name: (DIRECTORY / name).read_text() if (DIRECTORY / name).is_file() else "" for name in texts}
    found = results.golden_problems(trials, held)
    found += results.table_problems((ROOT / "docs" / "RESULTS.md").read_text(), held)
    found += goldens.held_problems(DIRECTORY, goldens.split_index(DIRECTORY)[0], (ROOT / "theGhost.md").read_text())
    print("\n".join(found) if found else f"baseline goldens: {len(texts)} agree with {results.SOURCE} and RESULTS.md")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
