"""Every dataset in data/MANIFEST.md has every column filled (test/test_manifest.py, R-006)."""
from scripts.checks import tables


def problems(manifest: str) -> list[str]:
    """Each row with a blank cell, named by its dataset and the column; an empty table holds."""
    table = [line for line in manifest.splitlines() if line.startswith("|")]
    if not table:
        return ["no table"]
    header = tables.cells(table[0])
    found = []
    for line in table[2:]:
        cells = tables.cells(line)
        dataset = cells[0] or "?"
        found += [f"{dataset} has no {name}" for name, cell in zip(header, cells) if not cell]
        if len(cells) != len(header):
            found.append(f"{dataset} has {len(cells)} cells, the header {len(header)}")
    return found
