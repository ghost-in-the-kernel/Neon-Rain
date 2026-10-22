"""docs/HARNESS.md's invariants are numbered in sequence and each is held in neonrain/harness/ (test/test_harness_doc.py)."""
import re
from pathlib import Path

HEADING = re.compile(r"^## (HAR-\d{2}) ", re.MULTILINE)
REFERENCE = re.compile(r"\bHAR-\d{2}\b")


def numbering_problems(document: str) -> list[str]:
    """Headings HAR-01, HAR-02, ... each once and with no gap."""
    numbers = HEADING.findall(document)
    found = [f"{n} appears {numbers.count(n)} times" for n in sorted(set(numbers)) if numbers.count(n) > 1]
    for position, number in enumerate(numbers, start=1):
        if number != f"HAR-{position:02d}":
            return found + [f"invariant {position} is {number}, expected HAR-{position:02d}"]
    return found


def code_references(harness: Path) -> set[str]:
    """Every HAR-nn named anywhere in the harness's Python (a docstring or a comment counts)."""
    found: set[str] = set()
    for path in sorted(harness.rglob("*.py")):
        found |= set(REFERENCE.findall(path.read_text()))
    return found


def reference_problems(document: str, harness: Path) -> list[str]:
    """Invariants the code never names, and names in the code the document does not have."""
    documented = set(HEADING.findall(document))
    referenced = code_references(harness)
    found = [f"{n} is in docs/HARNESS.md and nowhere in neonrain/harness/" for n in sorted(documented - referenced)]
    return found + [f"neonrain/harness/ names {n}, which docs/HARNESS.md does not have" for n in sorted(referenced - documented)]
