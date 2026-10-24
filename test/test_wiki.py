"""The WIKI fetch script (TODO 2.1 b): the join, its refusal, the sample's dates, the yearly files and their index.

Every file here is built in a temporary folder from a few invented rows (R-006); the real export is never read.
"""
import hashlib
import zipfile
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from scripts.fetch import wiki

HEADER = ",".join(wiki.COLUMNS)
ROW = "{t},{d},1.5,2.5,1.0,2.0,100.0,0.0,1.0,1.5,2.5,1.0,2.0,100.0"


def csv_text(rows: list[tuple[str, str]]) -> str:
    """A CSV in the export's layout from (ticker, date) pairs."""
    return HEADER + "\n" + "".join(ROW.format(t=t, d=d) + "\n" for t, d in rows)


def make_zip(path: Path, name: str, text: str) -> None:
    """A zip holding one file."""
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr(name, text)


def split_parts(archive: Path, folder: Path, pieces: int) -> list[Path]:
    """The archive cut into `pieces` parts named like the export's, in order."""
    data = archive.read_bytes()
    size = -(-len(data) // pieces)
    folder.mkdir(parents=True, exist_ok=True)
    parts = []
    for number in range(pieces):
        part = folder / f"WIKI_PRICES.zip.part-{chr(97 + number) * 2}"
        part.write_bytes(data[number * size:(number + 1) * size])
        parts.append(part)
    return parts


def manifest_for(digest: str) -> str:
    """A manifest with the raw row, as data/MANIFEST.md writes it."""
    return f"| Dataset | Hash |\n| --- | --- |\n| other | sha256 {'0' * 64} |\n| wiki-prices-raw | sha256 {digest} |\n"


def test_the_manifest_hash_is_read_from_its_row() -> None:
    assert wiki.manifest_hash(manifest_for("ab" * 32), "wiki-prices-raw") == "ab" * 32
    assert wiki.manifest_hash(manifest_for("ab" * 32), "other") == "0" * 64


def test_a_row_that_is_absent_or_has_no_hash_is_refused() -> None:
    with pytest.raises(wiki.WikiError, match="no row nope"):
        wiki.manifest_hash(manifest_for("ab" * 32), "nope")
    with pytest.raises(wiki.WikiError, match="no 'sha256"):
        wiki.manifest_hash("| wiki-prices-raw | pending |\n", "wiki-prices-raw")
    with pytest.raises(wiki.WikiError, match="no 'sha256"):
        wiki.manifest_hash("| wiki-prices-raw | sha256 abc |\n", "wiki-prices-raw")
    with pytest.raises(wiki.WikiError, match="no 'sha256"):
        wiki.manifest_hash("| wiki-prices-raw | md5 " + "a" * 64 + " |\n", "wiki-prices-raw")


def test_the_parts_join_into_the_original_bytes(tmp_path: Path) -> None:
    archive = tmp_path / "a.zip"
    make_zip(archive, "x.csv", csv_text([("A", "2000-01-03")]))
    parts = split_parts(archive, tmp_path / "parts", 3)
    joined = tmp_path / "joined.zip"
    wiki.join_parts(parts, joined, hashlib.sha256(archive.read_bytes()).hexdigest())
    assert joined.read_bytes() == archive.read_bytes()


def test_parts_that_do_not_hash_to_the_manifest_are_refused_and_nothing_is_written(tmp_path: Path) -> None:
    archive = tmp_path / "a.zip"
    make_zip(archive, "x.csv", csv_text([("A", "2000-01-03")]))
    parts = split_parts(archive, tmp_path / "parts", 2)
    joined = tmp_path / "joined.zip"
    with pytest.raises(wiki.WikiError, match="refusing the join"):
        wiki.join_parts(parts, joined, "0" * 64)
    assert not joined.exists()


def test_no_parts_is_refused(tmp_path: Path) -> None:
    with pytest.raises(wiki.WikiError, match="no parts"):
        wiki.join_parts([], tmp_path / "j.zip", "0" * 64)


def test_the_csv_in_the_zip_is_extracted(tmp_path: Path) -> None:
    make_zip(tmp_path / "a.zip", "data.csv", "hello")
    assert wiki.unzip_csv(tmp_path / "a.zip", tmp_path / "out").read_text() == "hello"


def test_a_zip_with_other_than_one_file_is_refused(tmp_path: Path) -> None:
    with zipfile.ZipFile(tmp_path / "a.zip", "w") as bundle:
        bundle.writestr("one.csv", "1")
        bundle.writestr("two.csv", "2")
    with pytest.raises(wiki.WikiError, match="2 files"):
        wiki.unzip_csv(tmp_path / "a.zip", tmp_path / "out")
    with zipfile.ZipFile(tmp_path / "b.zip", "w"):
        pass
    with pytest.raises(wiki.WikiError, match="0 files"):
        wiki.unzip_csv(tmp_path / "b.zip", tmp_path / "out")


def test_the_sample_keeps_exactly_the_plans_dates_and_the_columns_as_they_are(tmp_path: Path) -> None:
    rows = [("A", "1998-01-01"), ("A", "1998-01-02"), ("A", "2017-12-29"), ("A", "2018-01-02"), ("B", "1962-01-02")]
    (tmp_path / "x.csv").write_text(csv_text(rows))
    got = wiki.sample(tmp_path / "x.csv").collect()
    assert got["date"].to_list() == [date(1998, 1, 2), date(2017, 12, 29)]
    assert got.columns == list(wiki.COLUMNS)
    assert got.schema == pl.Schema(wiki.COLUMNS)
    assert (wiki.FIRST_DATE, wiki.LAST_DATE) == (date(1998, 1, 2), date(2017, 12, 29))


def test_a_header_that_is_not_the_export_is_refused(tmp_path: Path) -> None:
    (tmp_path / "x.csv").write_text("ticker,date,close\nA,2000-01-03,1.0\n")
    with pytest.raises(wiki.WikiError, match="expected"):
        wiki.sample(tmp_path / "x.csv")


def test_one_parquet_per_year_sorted_with_an_index_of_their_hashes(tmp_path: Path) -> None:
    rows = [("B", "2000-01-03"), ("A", "2000-01-04"), ("A", "2000-01-03"), ("A", "2001-06-01")]
    (tmp_path / "x.csv").write_text(csv_text(rows))
    folder = tmp_path / "prices"
    hashes = wiki.write_years(wiki.sample(tmp_path / "x.csv"), folder)
    assert sorted(hashes) == [2000, 2001]
    first = pl.read_parquet(folder / "2000.parquet")
    assert first.select("ticker", "date").rows() == [("A", date(2000, 1, 3)), ("A", date(2000, 1, 4)), ("B", date(2000, 1, 3))]
    assert pl.read_parquet(folder / "2001.parquet").height == 1
    assert hashes[2000] == hashlib.sha256((folder / "2000.parquet").read_bytes()).hexdigest()
    lines = (folder / "index.tsv").read_text().splitlines()
    assert lines == [f"2000\t2000.parquet\t{hashes[2000]}", f"2001\t2001.parquet\t{hashes[2001]}"]


def test_the_index_lists_years_ascending() -> None:
    assert wiki.index_text({2001: "b", 2000: "a"}) == "2000\t2000.parquet\ta\n2001\t2001.parquet\tb\n"


def test_a_year_file_over_the_limit_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wiki, "MAX_BYTES", 10)
    frame = pl.DataFrame({"ticker": ["A"], "date": [date(2000, 1, 3)]})
    with pytest.raises(wiki.WikiError, match="over 100 MB"):
        wiki.write_year(frame, tmp_path / "2000.parquet")


def build_clone(tmp_path: Path, digest_ok: bool) -> tuple[Path, Path]:
    """A data clone holding the raw parts of a tiny export, and a manifest naming their hash (or a wrong one)."""
    archive = tmp_path / "a.zip"
    make_zip(archive, "WIKI.csv", csv_text([("A", "2000-01-03"), ("A", "2018-01-02")]))
    clone = tmp_path / "clone"
    split_parts(archive, clone / "raw" / "wiki", 2)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest() if digest_ok else "0" * 64
    manifest = tmp_path / "MANIFEST.md"
    manifest.write_text(manifest_for(digest))
    return clone, manifest


def test_the_whole_run_writes_the_years_and_returns_the_indexs_hash(tmp_path: Path) -> None:
    clone, manifest = build_clone(tmp_path, True)
    digest = wiki.build(clone, manifest, tmp_path / "scratch")
    index = clone / "wiki" / "prices" / "index.tsv"
    assert digest == hashlib.sha256(index.read_bytes()).hexdigest()
    assert [p.name for p in sorted((clone / "wiki" / "prices").glob("*.parquet"))] == ["2000.parquet"]


def test_a_run_on_the_wrong_hash_writes_no_year(tmp_path: Path) -> None:
    clone, manifest = build_clone(tmp_path, False)
    with pytest.raises(wiki.WikiError):
        wiki.build(clone, manifest, tmp_path / "scratch")
    assert not (clone / "wiki").exists()
    assert not (tmp_path / "scratch" / "WIKI_PRICES.zip").exists()


def test_the_command_line_refuses_misuse_and_wrong_hashes_and_clears_its_scratch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert wiki.main([]) == 2
    assert wiki.main(["a", "b", "stay"]) == 2
    clone, _ = build_clone(tmp_path, True)
    scratch = tmp_path / "scratch"
    assert wiki.main([str(clone), str(scratch)]) == 1  # the real MANIFEST.md names the real export's hash, not this one
    assert "refused" in capsys.readouterr().err
    assert not scratch.exists()
    assert wiki.main([str(clone), str(scratch), "keep"]) == 1
    assert scratch.exists()
