"""docs/HARNESS.md's invariants are in sequence and held by the harness's code, both ways (TODO 0.5)."""
from pathlib import Path

import pytest

from scripts.checks import harness_doc

ROOT = Path(__file__).resolve().parent.parent
DOC = "## HAR-01 One\n\n## HAR-02 Two\n"


def test_the_real_numbering_holds(root: Path) -> None:
    assert harness_doc.numbering_problems((root / "docs" / "HARNESS.md").read_text()) == []


FROZEN = "### 1.7" in (ROOT / "docs" / "DONE.md").read_text()


def test_the_code_names_no_invariant_the_document_lacks(root: Path) -> None:
    assert harness_doc.unknown((root / "docs" / "HARNESS.md").read_text(), root / "neonrain" / "harness") == []


# Phase 1 builds the harness a step at a time (1.1 to 1.6), so an invariant not yet held by the code is expected
# until 1.7 freezes it; from then this runs for real. Not strict: phase 1 may cite every HAR before 1.7 is marked
# done, and the condition only ever turns off (J-012, which replaced 0.5's condition on the folder existing).
@pytest.mark.xfail(not FROZEN, reason="phase 1 is building neonrain/harness/; held from 1.7")
def test_every_invariant_is_held_by_the_code(root: Path) -> None:
    assert harness_doc.unheld((root / "docs" / "HARNESS.md").read_text(), root / "neonrain" / "harness") == []


def test_a_duplicate_and_a_gap_are_caught() -> None:
    assert harness_doc.numbering_problems(DOC + "## HAR-02 Again\n") == [
        "HAR-02 appears 2 times", "invariant 3 is HAR-02, expected HAR-03"
    ]
    assert harness_doc.numbering_problems("## HAR-01 a\n\n## HAR-03 c\n") == ["invariant 2 is HAR-03, expected HAR-02"]


def test_an_invariant_nowhere_in_the_code_is_caught(tmp_path: Path) -> None:
    (tmp_path / "split.py").write_text('"""Walk-forward folds (HAR-01)."""\n')
    assert harness_doc.reference_problems(DOC, tmp_path) == ["HAR-02 is in docs/HARNESS.md and nowhere in neonrain/harness/"]


def test_a_reference_to_no_invariant_is_caught(tmp_path: Path) -> None:
    (tmp_path / "split.py").write_text("# HAR-01, HAR-02\n# HAR-07\n")
    assert harness_doc.reference_problems(DOC, tmp_path) == ["neonrain/harness/ names HAR-07, which docs/HARNESS.md does not have"]


def test_both_ways_held_is_clean(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("# HAR-01\n")
    (tmp_path / "b.py").write_text('"""HAR-02"""\n')
    assert harness_doc.reference_problems(DOC, tmp_path) == []
