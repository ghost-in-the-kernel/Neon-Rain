"""The feature table as yearly parquet files and an index (TODO 2.5, R-006, R-016).

Loads WIKI's prices from the data repository's clone through `prices.load` (every file hash-checked against the index
and the manifest row `wiki-prices` before a byte is parsed), builds the universe (`prices.universe`, ranked on the raw close and volume as the baselines do) and the table
(`table.feature_table`), and writes `<year>.parquet` for each year the table has rows, each under 100 MB, and
`index.tsv` (`year<TAB>file<TAB>sha256`, the dataset layout of `verified`). The SHA-256 of that index is the hash the
manifest row `feature-table` carries; the files are stored in the artifact store by their own hashes
(`scripts/fetch/artifacts.py put`), the index with them.

    PYTHONPATH=. python scripts/fetch/feature_table.py DATA_CLONE OUT_DIR   # OUT_DIR is outside both repositories

**Byte for byte.** The same input gives the same bytes, because everything that could vary is fixed: rows sorted by
(ticker, date), columns in `table.columns()` order, dtypes as the table's, one file for each calendar year, and the
parquet settings of PARQUET (zstd at level 3, statistics on, row groups of 100,000 rows, data pages of 1 MiB, polars'
own writer). The writer does put its own version in the file's footer (`created_by`), so the bytes are a function of
the polars version too, pinned by `requirements.lock`; the manifest row records that version beside the hash.
Pure apart from reading and writing files; no clock, no network.
"""
import io
import sys
import tempfile
from pathlib import Path

import polars as pl

from neonrain.features import returns, table
from neonrain.universe import calendar, prices, verified
from scripts.fetch import artifacts, wiki

DATASET = "feature-table"

FIRST_YEAR = 1998
LAST_YEAR = 2017
# Decision: TODO 2.5: the parquet settings that make the bytes repeatable; changing one changes the table's hash.
PARQUET = {"compression": "zstd", "compression_level": 3, "statistics": True, "row_group_size": 100_000, "data_page_size": 1 << 20}
MAX_BYTES = artifacts.MAX_BYTES


class TableError(Exception):
    """A run that was refused; the message says why."""


def write_year(frame: pl.DataFrame, path: Path) -> str:
    """One year's rows sorted by (ticker, date) as parquet with PARQUET's settings; refuses 100 MB or more; its SHA-256."""
    frame.sort("ticker", "date").write_parquet(path, **PARQUET)
    if path.stat().st_size >= MAX_BYTES:
        raise TableError(f"{path.name} is {path.stat().st_size} bytes, over 100 MB (R-016 a)")
    return artifacts.sha256_of(path)


def write_years(frame: pl.DataFrame, folder: Path) -> dict[int, str]:
    """`<year>.parquet` for each year of `frame` and `index.tsv` in `folder`; each year's SHA-256 by year."""
    folder.mkdir(parents=True, exist_ok=True)
    years = frame.select(pl.col("date").dt.year().unique().sort()).to_series().to_list()
    hashes = {year: write_year(frame.filter(pl.col("date").dt.year() == year), folder / f"{year}.parquet") for year in years}
    (folder / "index.tsv").write_text(wiki.index_text(hashes))
    return hashes


def build(clone: Path, manifest: str, out: Path) -> str:
    """The table of the data clone's verified prices written to `out`; the index's SHA-256, for the manifest row."""
    sessions = calendar.sessions(FIRST_YEAR, LAST_YEAR)
    loaded = prices.load(clone / "wiki" / "prices", manifest, sessions)
    members = prices.universe(loaded.prices, sessions)
    write_years(table.feature_table(loaded.prices, sessions, members), out)
    return artifacts.sha256_of(out / "index.tsv")


def feature_names() -> list[str]:
    """The table's feature columns, sorted by name: `table.columns()` without the keys and the stamps (sixteen)."""
    return sorted(c for c in table.columns() if c not in table.KEYS and not c.endswith(returns.STAMP_SUFFIX))


def fetch(manifest: str, folder: Path, clone: Path, remote: str) -> None:
    """The index, by the hash on the manifest row `feature-table`, and each year's file, by its hash in that index,
    from the artifact store into `folder`. The store refuses bytes that do not hash to their name (`artifacts.get`)."""
    artifacts.get(verified.manifest_hash(manifest, DATASET), folder / "index.tsv", clone, remote)
    for name, digest in verified.parse_index((folder / "index.tsv").read_text()).values():
        artifacts.get(digest, folder / name, clone, remote)


def load(manifest: str, clone: Path, remote: str) -> pl.DataFrame:
    """The feature table from the artifact store, every year in order, after the index hashes to the manifest row and
    each file to its index line (`verified.read_verified`), sorted by (ticker, date) as the table is defined. Nothing is read from a local copy that was not checked."""
    with tempfile.TemporaryDirectory(prefix="neonrain-feature-table-") as folder:
        fetch(manifest, Path(folder), clone, remote)
        files = verified.read_verified(Path(folder), manifest, DATASET)
    return pl.concat([pl.read_parquet(io.BytesIO(files[year])) for year in sorted(files)]).sort(table.KEYS)


def main(argv: list[str]) -> int:
    """The command line: DATA_CLONE OUT_DIR; prints the index's hash; 0 on success, 1 on a refusal, 2 on misuse."""
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    manifest = (Path(__file__).resolve().parents[2] / "data" / "MANIFEST.md").read_text()
    try:
        print(build(Path(argv[0]), manifest, Path(argv[1])))
    except Exception as refusal:  # noqa: BLE001 - a verification refusal (verified.Unverified), a layout fault or TableError
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
