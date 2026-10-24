"""Quandl's WIKI prices, the sample as yearly parquet (TODO 2.1 b, R-006, J-041, J-042).

The raw export sits in the data repository's clone (`raw/wiki/WIKI_PRICES.zip.part-*`, five parts). This script
joins them, refuses them unless the joined bytes hash to the manifest's row `wiki-prices-raw`, reads the one CSV in
the zip, keeps the sample's dates, and writes one parquet file per year to `<clone>/wiki/prices/<year>.parquet`
(each under 100 MB, R-016 a) with the columns as the export has them, rows sorted by ticker then date. It also
writes `<clone>/wiki/prices/index.tsv`, one line per year (`year<TAB>file<TAB>sha256`); the SHA-256 of that index is
the hash the manifest row `wiki-prices` carries. Nothing is pushed: the reviewer pushes the data repository.

    python scripts/fetch/wiki.py DATA_CLONE SCRATCH_DIR [keep]   # SCRATCH_DIR is outside both repositories

The joined zip and the unzipped CSV (1.8 GB) go to SCRATCH_DIR and are deleted when the run ends, unless `keep`.
"""
import hashlib
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

import polars as pl

FIRST_DATE = date(1998, 1, 2)
LAST_DATE = date(2017, 11, 7)  # the last session before the feed's holes (R-026 a, NR-F-07)
MAX_BYTES = 100 * 1000 * 1000  # R-016 (a): plain git files under 100 MB each
RAW_DATASET = "wiki-prices-raw"
PARTS_GLOB = "WIKI_PRICES.zip.part-*"
COLUMNS: dict[str, pl.DataType] = {
    "ticker": pl.String(), "date": pl.Date(), "open": pl.Float64(), "high": pl.Float64(), "low": pl.Float64(),
    "close": pl.Float64(), "volume": pl.Float64(), "ex-dividend": pl.Float64(), "split_ratio": pl.Float64(),
    "adj_open": pl.Float64(), "adj_high": pl.Float64(), "adj_low": pl.Float64(), "adj_close": pl.Float64(),
    "adj_volume": pl.Float64(),
}


class WikiError(Exception):
    """A run that was refused; the message says why."""


def sha256_of(path: Path) -> str:
    """The SHA-256 of a file's bytes, hex, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_hash(manifest: str, dataset: str) -> str:
    """The SHA-256 on a manifest row, which ends `sha256 <64 hex>`; refuses a row that is absent or has none."""
    for line in manifest.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[0] == dataset:
            words = cells[-1].split()
            if len(words) == 2 and words[0] == "sha256" and len(words[1]) == 64:
                return words[1]
            raise WikiError(f"the manifest row {dataset} has no 'sha256 <hash>' in its last cell")
    raise WikiError(f"the manifest has no row {dataset}")


def join_parts(parts: list[Path], dest: Path, expected: str) -> None:
    """Concatenate the parts into `dest`, but only if they hash to `expected` (nothing is written otherwise)."""
    if not parts:
        raise WikiError("no parts to join")
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.read_bytes())
    if digest.hexdigest() != expected:
        raise WikiError(f"the parts hash to {digest.hexdigest()}, the manifest says {expected}: refusing the join")
    with dest.open("wb") as out:
        for part in parts:
            with part.open("rb") as handle:
                shutil.copyfileobj(handle, out)


def unzip_csv(archive: Path, folder: Path) -> Path:
    """Extract the one CSV in a zip into `folder`; refuses an archive with any other number of files."""
    with zipfile.ZipFile(archive) as bundle:
        names = [name for name in bundle.namelist() if not name.endswith("/")]
        if len(names) != 1:
            raise WikiError(f"the zip holds {len(names)} files, expected one CSV")
        bundle.extract(names[0], folder)
    return folder / names[0]


def sample(csv: Path) -> pl.LazyFrame:
    """The CSV, typed as COLUMNS says, kept to FIRST_DATE..LAST_DATE; refuses a header that is not those columns."""
    lazy = pl.scan_csv(csv, schema_overrides=COLUMNS, try_parse_dates=True)
    if lazy.collect_schema().names() != list(COLUMNS):
        raise WikiError(f"the CSV's columns are {lazy.collect_schema().names()}, expected {list(COLUMNS)}")
    return lazy.filter(pl.col("date").is_between(FIRST_DATE, LAST_DATE))


def write_year(frame: pl.DataFrame, path: Path) -> str:
    """One year's rows, sorted by ticker then date, as parquet; refuses a file over 100 MB; the file's SHA-256."""
    frame.sort("ticker", "date").write_parquet(path, compression="zstd", statistics=True)
    if path.stat().st_size >= MAX_BYTES:
        raise WikiError(f"{path.name} is {path.stat().st_size} bytes, over 100 MB (R-016 a)")
    return sha256_of(path)


def index_text(hashes: dict[int, str]) -> str:
    """The index: one line per year, `year<TAB>file<TAB>sha256`, ascending."""
    return "".join(f"{year}\t{year}.parquet\t{hashes[year]}\n" for year in sorted(hashes))


def write_years(lazy: pl.LazyFrame, folder: Path) -> dict[int, str]:
    """Yearly parquet files and `index.tsv` in `folder`; each year's SHA-256 by year. Rows outside a year never cross."""
    folder.mkdir(parents=True, exist_ok=True)
    years = lazy.select(pl.col("date").dt.year().unique().sort()).collect().to_series().to_list()
    hashes = {}
    for year in years:
        frame = lazy.filter(pl.col("date").dt.year() == year).collect()
        hashes[year] = write_year(frame, folder / f"{year}.parquet")
    (folder / "index.tsv").write_text(index_text(hashes))
    return hashes


def build(clone: Path, manifest: Path, scratch: Path) -> str:
    """The whole run; the index's SHA-256, for the manifest row. The scratch files stay for the caller to remove."""
    parts = sorted((clone / "raw" / "wiki").glob(PARTS_GLOB))
    scratch.mkdir(parents=True, exist_ok=True)
    join_parts(parts, scratch / "WIKI_PRICES.zip", manifest_hash(manifest.read_text(), RAW_DATASET))
    csv = unzip_csv(scratch / "WIKI_PRICES.zip", scratch / "csv")
    write_years(sample(csv), clone / "wiki" / "prices")
    return sha256_of(clone / "wiki" / "prices" / "index.tsv")


def main(argv: list[str]) -> int:
    """The command line: DATA_CLONE SCRATCH_DIR [keep]; prints the index's hash; 0 on success, 1 on a refusal, 2 on misuse.

    The scratch directory is deleted at the end unless the third word is `keep`.
    """
    if len(argv) not in (2, 3) or (len(argv) == 3 and argv[2] != "keep"):
        print(__doc__, file=sys.stderr)
        return 2
    scratch = Path(argv[1])
    try:
        print(build(Path(argv[0]), Path(__file__).resolve().parents[2] / "data" / "MANIFEST.md", scratch))
    except WikiError as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    finally:
        if len(argv) == 2:
            shutil.rmtree(scratch, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
