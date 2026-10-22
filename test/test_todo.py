"""TODO.md is a chain in order with a check on its first item, sharing nothing with DONE.md (TODO 0.5)."""
from pathlib import Path

from checks import todo

CHAIN = "## Phase 0\n\n### 0.2 a\n\nCheck: x\n\n### 0.5 b\n\nCheck: y\n\n## Phase 1\n\n### 1.1 c\n"


def test_the_real_chain_holds(root: Path) -> None:
    assert todo.problems((root / "TODO.md").read_text(), (root / "docs" / "DONE.md").read_text()) == []


def test_a_clean_chain_holds() -> None:
    assert todo.problems(CHAIN, "### 0.1 done\n") == []


def test_items_out_of_order_are_caught() -> None:
    swapped = CHAIN.replace("### 0.2 a", "### 0.6 a")
    assert todo.problems(swapped, "") == ["items out of order: ['0.6', '0.5', '1.1']"]


def test_an_item_under_the_wrong_phase_is_caught() -> None:
    misplaced = CHAIN.replace("### 1.1 c", "### 0.9 c")
    assert todo.problems(misplaced, "") == ["item 0.9 is not under Phase 0"]


def test_phases_out_of_order_are_caught() -> None:
    assert todo.order_problems("## Phase 1\n\n## Phase 0\n") == ["phases out of order: [1, 0]"]


def test_a_first_item_without_a_check_is_caught() -> None:
    unchecked = CHAIN.replace("Check: x\n", "")
    assert todo.problems(unchecked, "") == ["the first open item, 0.2, has no Check: line"]


def test_a_later_item_without_a_check_is_allowed() -> None:
    assert todo.problems(CHAIN.replace("Check: y\n", ""), "") == []


def test_an_item_in_both_files_is_caught() -> None:
    assert todo.problems(CHAIN, "### 0.5 b\n") == ["0.5 is in both TODO.md and DONE.md"]


def test_an_empty_chain_holds() -> None:
    assert todo.problems("## Phase 0\n", "") == []
