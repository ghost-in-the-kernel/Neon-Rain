"""Every dataset in data/MANIFEST.md has every column filled (test/test_manifest.py, R-006)."""


def rows(manifest: str) -> list[list[str]]:
    """The table's data rows as cells, header and rule left out: "| a | b |" gives ["a", "b"]."""
    table = [line for line in manifest.splitlines() if line.startswith("|")]
    return [[cell.strip() for cell in line.strip("|").split("|")] for line in table[2:]]


def problems(manifest: str) -> list[str]:
    """Each row with a blank cell, named by its dataset and the column; an empty table holds."""
    table = [line for line in manifest.splitlines() if line.startswith("|")]
    if not table:
        return ["no table"]
    header = [cell.strip() for cell in table[0].strip("|").split("|")]
    found = []
    for cells in rows(manifest):
        found += [f"{cells[0] or '?'} has no {name}" for name, cell in zip(header, cells, strict=False) if not cell]
        if len(cells) != len(header):
            found.append(f"{cells[0] or '?'} has {len(cells)} cells, the header {len(header)}")
    return found
