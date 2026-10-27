"""The feature table's build script (TODO 2.5): the yearly files, their index, the bytes repeating, the refusals.

Everything is built in a temporary folder from invented prices (R-006): 25 tickers on the sessions 150 to 330 of 1998 and 1999 (the universe starts 63 sessions in, so both years have rows).
"""
import random
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


@pytest.fixture
def clone(tmp_path: Path) -> tuple[Path, str]:
    """A data clone holding invented `wiki/prices` and the manifest text that carries its index hash."""
    folder = tmp_path / "data" / "wiki" / "prices"
    wiki.write_years(export().lazy(), folder)
    digest = artifacts.sha256_of(folder / "index.tsv")
    return tmp_path / "data", f"| wiki-prices | s | l | f | r | sha256 {digest} (of index.tsv) |\n"


def test_the_files_and_the_index(clone: tuple[Path, str], tmp_path: Path) -> None:
    out = tmp_path / "out"
    digest = feature_table.build(clone[0], clone[1], out)
    assert sorted(p.name for p in out.iterdir()) == ["1998.parquet", "1999.parquet", "index.tsv"]
    entries = verified.parse_index((out / "index.tsv").read_text())
    assert list(entries) == ["1998", "1999"]
    for year, (name, sha) in entries.items():
        assert name == f"{year}.parquet" and artifacts.sha256_of(out / name) == sha
    assert digest == artifacts.sha256_of(out / "index.tsv")


def test_the_same_input_gives_the_same_bytes(clone: tuple[Path, str], tmp_path: Path) -> None:
    first = feature_table.build(clone[0], clone[1], tmp_path / "a")
    second = feature_table.build(clone[0], clone[1], tmp_path / "b")
    assert first == second
    for name in ("1998.parquet", "1999.parquet", "index.tsv"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_the_files_hold_the_table_in_order(clone: tuple[Path, str], tmp_path: Path) -> None:
    feature_table.build(clone[0], clone[1], tmp_path / "out")
    for year in (1998, 1999):
        frame = pl.read_parquet(tmp_path / "out" / f"{year}.parquet")
        assert frame.columns == table.columns()
        assert (frame["date"].dt.year() == year).all()
        assert frame.equals(frame.sort("ticker", "date"))
    assert pl.read_parquet(tmp_path / "out" / "1999.parquet").height > 0


def test_the_parquet_settings_are_the_documented_ones(clone: tuple[Path, str], tmp_path: Path) -> None:
    import pyarrow.parquet as pq

    feature_table.build(clone[0], clone[1], tmp_path / "out")
    meta = pq.ParquetFile(tmp_path / "out" / "1999.parquet").metadata
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
