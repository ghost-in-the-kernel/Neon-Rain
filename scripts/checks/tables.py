"""The markdown-table helpers the checks share: finding a table's lines and splitting a line into cells."""
import re

TABLE = re.compile(r"(?:^\|.*(?:\n|$))+", re.MULTILINE)


def cells(line: str) -> list[str]:
    """A table line's cells, trimmed: "| a | b |" gives ["a", "b"]."""
    return [cell.strip() for cell in line.strip().split("|")[1:-1]]
