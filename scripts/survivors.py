"""Read `mutmut results` on stdin; print each survivor docs/MUTATION.md does not explain; exit 1 if any.

    .venv/bin/mutmut results | .venv/bin/python scripts/survivors.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.checks import mutation  # noqa: E402

DOC = Path(__file__).resolve().parent.parent / "docs" / "MUTATION.md"


def main() -> int:
    results = sys.stdin.read()
    doc = DOC.read_text()
    missing = mutation.unexplained(results, doc)
    for name in missing:
        print(f"unexplained survivor: {name} (`.venv/bin/mutmut show {name}`; kill it or explain it in docs/MUTATION.md)")
    for name in mutation.stale(results, doc):
        print(f"stale line in docs/MUTATION.md: {name} no longer survives; remove it")
    print(f"survivors: {len(mutation.survivors(results))}, unexplained: {len(missing)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
