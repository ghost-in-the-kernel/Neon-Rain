"""No document uses an enforced alias; and a planted one is caught (TODO 0.5)."""
from pathlib import Path

from checks import glossary

TABLE = "| Term | Means | Not |\n| --- | --- | --- |\n| **horizon** | a window | period, `timeframe` |\n"


def plant(tmp_path: Path, roadmap: str) -> Path:
    """A root with the one-row glossary above and a ROADMAP.md of the given text."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "GLOSSARY.md").write_text(TABLE)
    (tmp_path / "docs" / "ROADMAP.md").write_text(roadmap)
    return tmp_path


def test_the_real_documents_hold(root: Path) -> None:
    assert glossary.problems(root) == []


def test_only_backticked_aliases_are_enforced() -> None:
    assert glossary.enforced_aliases(TABLE) == ["timeframe"]


def test_the_real_glossary_enforces_something(root: Path) -> None:
    assert glossary.enforced_aliases((root / "docs" / "GLOSSARY.md").read_text()) != []


def test_a_planted_alias_is_caught(tmp_path: Path) -> None:
    root = plant(tmp_path, "Each Timeframe is tested.\n")
    assert glossary.problems(root) == ["ROADMAP.md uses 'timeframe' 1 times"]


def test_an_unenforced_alias_passes(tmp_path: Path) -> None:
    assert glossary.problems(plant(tmp_path, "Each period is tested.\n")) == []


def test_a_quoted_alias_is_a_mention_not_a_use(tmp_path: Path) -> None:
    text = "Never write `timeframe`.\n```\ntimeframe = 3\n```\n"
    assert glossary.problems(plant(tmp_path, text)) == []


def test_an_alias_in_capitals_matches_only_in_capitals() -> None:
    assert glossary.uses("an NN and HAR-nn", "NN") == 1


def test_a_word_containing_the_alias_is_not_it(tmp_path: Path) -> None:
    assert glossary.problems(plant(tmp_path, "timeframes and subtimeframe\n")) == []
