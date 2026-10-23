"""docs/GLOSSARY.md's enforced aliases appear in no other document (test/test_glossary.py)."""
import re
from pathlib import Path

CODE_SPAN = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)


def enforced_aliases(glossary: str) -> list[str]:
    """The backticked words of the table's third column ("Not"): "| a | b | x, `nn` |" gives ["nn"]."""
    aliases = []
    for line in glossary.splitlines():
        cells = line.split("|")
        if len(cells) >= 5:
            aliases += re.findall(r"`([^`]+)`", cells[3])
    return aliases


def uses(text: str, alias: str) -> int:
    """How often `alias` is used as a word, outside code spans (a quoted alias is a mention, not a use).

    Case is ignored unless the alias is in capitals: `NN` matches "NN" but not "HAR-nn".
    """
    prose = CODE_SPAN.sub(" ", text)
    if not alias.isupper():
        prose, alias = prose.lower(), alias.lower()
    return len(re.findall(rf"\b{re.escape(alias)}\b", prose))


def documents(root: Path) -> list[Path]:
    """The documents the glossary governs: every .md at the root and anywhere under docs/, but the glossary."""
    found = sorted(root.glob("*.md")) + sorted((root / "docs").rglob("*.md"))
    return [path for path in found if path.name != "GLOSSARY.md"]


def problems(root: Path) -> list[str]:
    """Each document that uses an enforced alias, with the alias and the count."""
    aliases = enforced_aliases((root / "docs" / "GLOSSARY.md").read_text())
    found = []
    for path in documents(root):
        text = path.read_text()
        found += [f"{path.name} uses {alias!r} {uses(text, alias)} times" for alias in aliases if uses(text, alias)]
    return found
