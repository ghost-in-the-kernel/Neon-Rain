"""Every dataset in data/MANIFEST.md has every column; a blank one is caught (TODO 0.5, R-006)."""
from pathlib import Path

from scripts.checks import manifest

HEADER = "| Dataset | Source | License | Fetch | Range | Hash |\n| --- | --- | --- | --- | --- | --- |\n"


def test_the_real_manifest_holds(root: Path) -> None:
    assert manifest.problems((root / "data" / "MANIFEST.md").read_text()) == []


def test_an_empty_table_holds() -> None:
    assert manifest.problems(HEADER) == []


def test_a_full_row_holds() -> None:
    assert manifest.problems(HEADER + "| prices | Stooq | CC0 | f.py | 2000-2026 | ab12 |\n") == []


def test_a_blank_license_is_caught() -> None:
    assert manifest.problems(HEADER + "| prices | Stooq |  | f.py | 2000-2026 | ab12 |\n") == ["prices has no License"]


def test_a_short_row_is_caught() -> None:
    assert manifest.problems(HEADER + "| prices | Stooq | CC0 |\n") == ["prices has 3 cells, the header 6"]


def test_a_file_with_no_table_is_caught() -> None:
    assert manifest.problems("# Data manifest\n") == ["no table"]
