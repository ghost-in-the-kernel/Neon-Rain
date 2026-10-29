"""The feature table's build script (TODO 2.5): the yearly files, their index, the bytes repeating, the refusals.

Everything is built in a temporary folder from invented prices (R-006): 25 tickers on the sessions 150 to 330 of 1998 and 1999 (the universe starts 63 sessions in, so both years have rows).
"""
import random
import subprocess
from pathlib import Path

import polars as pl
import pytest

from neonrain.features import table
from neonrain.universe import calendar, prices, verified
from scripts.fetch import artifacts, feature_table, wiki

SESSIONS = calendar.sessions(1998, 1999)[150:330]


def export() -> pl.DataFrame:
    """The WIKI export's layout for invented rows: a seeded walk and volume for 25 tickers."""
    rng = random.Random(7)
    rows = []
    for i in range(25):
        close = 40.0 + i
        for day in SESSIONS:
            close *= 1 + rng.uniform(-0.02, 0.02)
            rows.append((f"T{i:02d}", day, close, rng.uniform(1e3, 1e5)))
    frame = pl.DataFrame(rows, schema={"ticker": pl.String, "date": pl.Date, "close": pl.Float64, "volume": pl.Float64}, orient="row")
    columns = {name: pl.col("close") if "close" in name or name in ("open", "high", "low") else pl.col("volume") for name in prices.EXPORT}
    return frame.select(
        "ticker", "date",
        *[(columns[name] if name not in ("ex-dividend", "split_ratio") else pl.lit(1.0)).cast(pl.Float64).alias(name)
          for name in prices.EXPORT if name not in ("ticker", "date")],
    )


def invented_clone(root: Path) -> tuple[Path, str]:
    """A data clone under `root` holding invented `wiki/prices` and the manifest text that carries its index hash."""
    folder = root / "data" / "wiki" / "prices"
    wiki.write_years(export().lazy(), folder)
    digest = artifacts.sha256_of(folder / "index.tsv")
    return root / "data", f"| wiki-prices | s | l | f | r | sha256 {digest} (of index.tsv) |\n"


@pytest.fixture
def clone(tmp_path: Path) -> tuple[Path, str]:
    """A data clone holding invented `wiki/prices` and the manifest text that carries its index hash."""
    return invented_clone(tmp_path)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """The table built once from the invented prices: its output folder and its index's hash. The tests read it, never
    write it; the build repeating itself is `test_the_same_input_gives_the_same_bytes`'s claim, which builds again."""
    root = tmp_path_factory.mktemp("built")
    data, manifest = invented_clone(root)
    return root / "out", feature_table.build(data, manifest, root / "out")


def test_the_files_and_the_index(built: tuple[Path, str]) -> None:
    out, digest = built
    assert sorted(p.name for p in out.iterdir()) == ["1998.parquet", "1999.parquet", "index.tsv"]
    entries = verified.parse_index((out / "index.tsv").read_text())
    assert list(entries) == ["1998", "1999"]
    for year, (name, sha) in entries.items():
        assert name == f"{year}.parquet" and artifacts.sha256_of(out / name) == sha
    assert digest == artifacts.sha256_of(out / "index.tsv")


def test_the_same_input_gives_the_same_bytes(built: tuple[Path, str], clone: tuple[Path, str], tmp_path: Path) -> None:
    first = built[1]
    second = feature_table.build(clone[0], clone[1], tmp_path / "b")
    assert first == second
    for name in ("1998.parquet", "1999.parquet", "index.tsv"):
        assert (built[0] / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_the_files_hold_the_table_in_order(built: tuple[Path, str]) -> None:
    out = built[0]
    for year in (1998, 1999):
        frame = pl.read_parquet(out / f"{year}.parquet")
        assert frame.columns == table.columns()
        assert (frame["date"].dt.year() == year).all()
        assert frame.equals(frame.sort("ticker", "date"))
    assert pl.read_parquet(out / "1999.parquet").height > 0


def test_the_parquet_settings_are_the_documented_ones(built: tuple[Path, str]) -> None:
    import pyarrow.parquet as pq

    meta = pq.ParquetFile(built[0] / "1999.parquet").metadata
    column = meta.row_group(0).column(2)
    assert column.compression == "ZSTD" and column.is_stats_set
    assert feature_table.PARQUET == {
        "compression": "zstd", "compression_level": 3, "statistics": True, "row_group_size": 100_000, "data_page_size": 1 << 20,
    }
    assert "polars" in meta.created_by.lower()


def test_row_groups_are_cut_at_the_fixed_size(tmp_path: Path) -> None:
    frame = pl.DataFrame({"ticker": ["A"] * 250_000, "date": [calendar.sessions(1998, 1998)[0]] * 250_000})
    feature_table.write_year(frame, tmp_path / "y.parquet")
    import pyarrow.parquet as pq

    assert [pq.ParquetFile(tmp_path / "y.parquet").metadata.row_group(i).num_rows for i in range(3)] == [100_000, 100_000, 50_000]


def test_rows_are_sorted_whatever_the_order_given(tmp_path: Path) -> None:
    day = SESSIONS[0]
    frame = pl.DataFrame({"ticker": ["B", "A"], "date": [day, day]})
    feature_table.write_year(frame, tmp_path / "y.parquet")
    assert pl.read_parquet(tmp_path / "y.parquet")["ticker"].to_list() == ["A", "B"]


def test_a_file_of_100_mb_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(feature_table, "MAX_BYTES", 1)
    with pytest.raises(feature_table.TableError, match="over 100 MB"):
        feature_table.write_year(pl.DataFrame({"ticker": ["A"], "date": [SESSIONS[0]]}), tmp_path / "y.parquet")


def test_the_limit_is_the_stores(tmp_path: Path) -> None:
    assert feature_table.MAX_BYTES == 100 * 1000 * 1000 == artifacts.MAX_BYTES


def test_prices_that_do_not_match_the_manifest_are_refused_before_any_write(clone: tuple[Path, str], tmp_path: Path) -> None:
    wrong = f"| wiki-prices | s | l | f | r | sha256 {'0' * 64} |\n"
    with pytest.raises(verified.Unverified):
        feature_table.build(clone[0], wrong, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_the_command_line(clone: tuple[Path, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert feature_table.main([]) == 2
    assert feature_table.main(["only-one"]) == 2
    assert feature_table.main([str(tmp_path / "no-such-clone"), str(tmp_path / "out")]) == 1
    assert "refused" in capsys.readouterr().err


FEATURES = ["macd", "macd_hist", "mar_21", "mar_5", "mar_63", "ret_21", "ret_3", "ret_5", "ret_63", "rsi_14", "vol_21",
            "vol_5", "vol_63", "volr_21", "volr_5", "volr_63"]


def test_the_feature_names_are_the_sixteen_without_keys_or_stamps() -> None:
    assert feature_table.feature_names() == FEATURES
    assert set(FEATURES) | {f"{name}_stamp" for name in FEATURES} | {"ticker", "date"} == set(table.columns())


@pytest.fixture(scope="module")
def stored(built: tuple[Path, str], tmp_path_factory: pytest.TempPathFactory) -> tuple[str, Path, str, pl.DataFrame]:
    """The table built from the invented prices, its files and index put in a local bare repository standing in for the
    artifact store: the manifest text of its row, a clone path, the remote, and the table (sorted). The tests only read
    the store, but for one artifact the refusing test adds (an index for another table), which no other test names."""
    tmp_path = tmp_path_factory.mktemp("stored")
    remote = tmp_path / "store.git"
    subprocess.run(["git", "init", "--quiet", "--bare", "--initial-branch=main", str(remote)], check=True)
    out, index = built
    for path in sorted(out.iterdir()):
        artifacts.put(path, tmp_path / "put-clone", str(remote))
    manifest = f"| {feature_table.DATASET} | s | l | f | r | sha256 {index} (of index.tsv) |\n"
    whole = pl.concat([pl.read_parquet(out / "1998.parquet"), pl.read_parquet(out / "1999.parquet")]).sort("ticker", "date")
    return manifest, tmp_path / "get-clone", str(remote), whole


def test_load_gives_the_table_from_the_store_sorted_by_ticker_and_date_and_keeps_no_copy(
        stored: tuple[str, Path, str, pl.DataFrame], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, clone, remote, whole = stored
    scratch = tmp_path / "tmp"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))
    monkeypatch.setattr("tempfile.tempdir", None)
    loaded = feature_table.load(manifest, clone, remote)
    assert loaded.equals(whole) and loaded.columns == table.columns() and loaded.height > 1000
    assert loaded["date"].dt.year().n_unique() == 2  # both years' files, joined in the table's (ticker, date) order
    assert list(scratch.iterdir()) == []  # the fetched files were in a temporary folder, gone now


def test_load_refuses_an_index_the_manifest_does_not_name_and_a_year_the_store_lacks(
        stored: tuple[str, Path, str, pl.DataFrame], tmp_path: Path) -> None:
    manifest, clone, remote, _ = stored
    wrong = f"| {feature_table.DATASET} | s | l | f | r | sha256 {'0' * 64} |\n"
    with pytest.raises(artifacts.ArtifactError, match="no artifact"):
        feature_table.load(wrong, clone, remote)  # nothing in the store has that hash: no unchecked copy is read instead
    with pytest.raises(verified.Unverified, match="no row"):
        feature_table.load("| other | s | l | f | r | sha256 " + "0" * 64 + " |\n", clone, remote)
    other = tmp_path / "other"
    other.mkdir()
    (other / "index.tsv").write_text(f"1998\t1998.parquet\t{'1' * 64}\n")
    artifacts.put(other / "index.tsv", tmp_path / "put-clone", remote)
    made = f"| {feature_table.DATASET} | s | l | f | r | sha256 {artifacts.sha256_of(other / 'index.tsv')} |\n"
    with pytest.raises(artifacts.ArtifactError, match="no artifact 1111"):
        feature_table.load(made, clone, remote)  # the index names a year the store lacks
    assert feature_table.load(manifest, clone, remote).height > 0
