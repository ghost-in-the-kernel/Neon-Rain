"""The price loader (TODO 2.2) and the verified read under it, on invented files: tickers A, B, C and round numbers.

No real price is in this file (R-006). Each test builds yearly parquet files, an index and a manifest row in a
temporary folder. The check against the real data is `scripts/probe/wiki_prices.py` (counts only, a run to report on): the fast
loop reads no data.
"""
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from neonrain.harness import market
from neonrain.universe import membership, prices, verified

MONDAY, TUESDAY, WEDNESDAY = date(2001, 1, 1), date(2001, 1, 2), date(2001, 1, 3)
NEXT_YEAR = date(2002, 1, 2)


def export(rows: list[tuple[str, date, float]]) -> pl.DataFrame:
    """Export-layout rows from (ticker, date, close): raw close = close, adjusted = half, volume 100 (adjusted 200)."""
    return pl.DataFrame(
        {
            "ticker": [r[0] for r in rows], "date": [r[1] for r in rows],
            "open": [r[2] + 1 for r in rows], "high": [r[2] + 2 for r in rows], "low": [r[2] - 1 for r in rows],
            "close": [r[2] for r in rows], "volume": [100.0] * len(rows), "ex-dividend": [0.0] * len(rows),
            "split_ratio": [1.0] * len(rows),
            "adj_open": [r[2] / 2 + 1 for r in rows], "adj_high": [r[2] / 2 + 2 for r in rows],
            "adj_low": [r[2] / 2 - 1 for r in rows], "adj_close": [r[2] / 2 for r in rows],
            "adj_volume": [200.0] * len(rows),
        },
        schema=prices.EXPORT,
    )


def make(folder: Path, years: dict[int, pl.DataFrame]) -> str:
    """Write the yearly files and the index into `folder`; the manifest text holding the index's hash."""
    lines = []
    for year, frame in years.items():
        path = folder / f"{year}.parquet"
        frame.write_parquet(path)
        lines.append(f"{year}\t{year}.parquet\t{verified.sha256_bytes(path.read_bytes())}\n")
    (folder / "index.tsv").write_text("".join(lines))
    return manifest_for(folder)


def manifest_for(folder: Path) -> str:
    """A manifest with the row `wiki-prices` carrying the hash of the folder's index."""
    digest = verified.sha256_bytes((folder / "index.tsv").read_bytes())
    return f"| a | b |\n| wiki-prices | licence | sha256 {digest} (of `index.tsv`) |\n"


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    """An empty data folder."""
    return tmp_path


def test_the_mapping_takes_adjusted_columns_and_keeps_raw_close_and_volume(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 10.0)])})
    loaded = prices.load(folder, text, [MONDAY])
    assert loaded.prices.columns == list(prices.FRAME)
    row = loaded.prices.row(0, named=True)
    assert (row["open"], row["high"], row["low"], row["close"], row["volume"]) == (6.0, 7.0, 4.0, 5.0, 200.0)
    assert (row["raw_close"], row["raw_volume"], row["ex_dividend"], row["split_ratio"]) == (10.0, 100.0, 0.0, 1.0)


def test_the_frame_has_the_harness_layout_and_rows_sorted_by_ticker_then_date(folder: Path) -> None:
    rows = [("B", TUESDAY, 2.0), ("A", TUESDAY, 2.0), ("B", MONDAY, 2.0), ("A", MONDAY, 2.0)]
    text = make(folder, {2001: export(rows)})
    loaded = prices.load(folder, text, [MONDAY, TUESDAY])
    market.check_prices(loaded.prices)
    market.check_on_calendar("price", loaded.prices, [MONDAY, TUESDAY])
    assert loaded.prices.select("ticker", "date").rows() == [("A", MONDAY), ("A", TUESDAY), ("B", MONDAY), ("B", TUESDAY)]


def test_years_join_in_order_and_a_chosen_year_reads_only_that_file(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 2.0)]), 2002: export([("A", NEXT_YEAR, 2.0)])})
    both = prices.load(folder, text, [MONDAY, NEXT_YEAR])
    assert both.prices["date"].to_list() == [MONDAY, NEXT_YEAR]
    (folder / "2001.parquet").write_bytes(b"damaged")  # 2001 is not asked for, so its damage is not read
    assert prices.load(folder, text, [NEXT_YEAR], years=[2002]).prices["date"].to_list() == [NEXT_YEAR]
    with pytest.raises(verified.Unverified, match="2001.parquet hashes to"):
        prices.load(folder, text, [MONDAY, NEXT_YEAR])


def test_a_date_that_is_no_session_is_handed_back_not_dropped(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 2.0), ("A", TUESDAY, 2.0), ("B", TUESDAY, 2.0), ("A", WEDNESDAY, 2.0)])})
    loaded = prices.load(folder, text, [MONDAY, WEDNESDAY])
    assert loaded.prices.select("ticker", "date").rows() == [("A", MONDAY), ("A", WEDNESDAY)]
    assert loaded.off_calendar.columns == ["ticker", "date"]
    assert loaded.off_calendar.sort("ticker").rows() == [("A", TUESDAY), ("B", TUESDAY)]
    market.check_on_calendar("price", loaded.prices, [MONDAY, WEDNESDAY])


def test_a_session_with_no_rows_between_the_first_and_last_date_is_handed_back(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 2.0), ("A", WEDNESDAY, 2.0)])})
    sessions = [date(2000, 12, 29), MONDAY, TUESDAY, WEDNESDAY, date(2001, 1, 4)]
    assert prices.load(folder, text, sessions).empty_sessions == [TUESDAY]


def test_a_session_whose_only_rows_are_off_the_sample_is_not_an_empty_one(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 2.0), ("A", TUESDAY, 2.0)])})
    assert prices.load(folder, text, [MONDAY, TUESDAY]).empty_sessions == []


def test_no_years_asked_gives_an_empty_frame_with_the_layout(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 2.0)])})
    loaded = prices.load(folder, text, [MONDAY], years=[])
    assert (loaded.prices.height, loaded.off_calendar.height, loaded.empty_sessions) == (0, 0, [])
    assert loaded.prices.columns == list(prices.FRAME)
    assert loaded.prices.schema["close"] == pl.Float64


def test_no_sessions_leave_every_row_off_the_calendar(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 2.0)])})
    loaded = prices.load(folder, text, [])
    assert loaded.prices.height == 0
    assert loaded.off_calendar.rows() == [("A", MONDAY)]


def test_nothing_is_empty_when_there_are_no_rows(folder: Path) -> None:
    text = make(folder, {2001: export([])})
    loaded = prices.load(folder, text, [MONDAY])
    assert (loaded.prices.height, loaded.off_calendar.height, loaded.empty_sessions) == (0, 0, [])


def test_a_ticker_with_a_gap_stays_one_ticker_with_its_rows(folder: Path) -> None:
    gap = [("A", MONDAY, 2.0), ("A", NEXT_YEAR, 20.0)]
    text = make(folder, {2001: export(gap[:1]), 2002: export(gap[1:])})
    loaded = prices.load(folder, text, [MONDAY, NEXT_YEAR])
    assert loaded.prices["ticker"].to_list() == ["A", "A"]
    assert loaded.prices["close"].to_list() == [1.0, 10.0]


def test_for_membership_gives_raw_close_and_volume_under_the_names_membership_reads(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 10.0)])})
    seen = prices.for_membership(prices.load(folder, text, [MONDAY]).prices)
    assert seen.columns == ["ticker", "date", "close", "volume"]
    assert seen.row(0) == ("A", MONDAY, 10.0, 100.0)
    assert membership.spans(seen).row(0) == ("A", MONDAY, MONDAY)


def test_a_file_that_is_not_the_exports_layout_is_refused(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 2.0)]).drop("adj_volume")})
    with pytest.raises(verified.Unverified, match="2001.parquet has the columns"):
        prices.load(folder, text, [MONDAY])
    text = make(folder, {2001: export([("A", MONDAY, 2.0)]).with_columns(pl.col("volume").cast(pl.Int64))})
    with pytest.raises(verified.Unverified, match="has the columns"):
        prices.load(folder, text, [MONDAY])


def test_a_row_outside_its_files_year_is_refused(folder: Path) -> None:
    text = make(folder, {2001: export([("A", NEXT_YEAR, 2.0)])})
    with pytest.raises(verified.Unverified, match=r"holds a row dated 2002-01-02, outside 2001"):
        prices.load(folder, text, [NEXT_YEAR])


# verification

def test_an_index_that_does_not_match_the_manifest_refuses_every_file(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 2.0)])})
    (folder / "index.tsv").write_text((folder / "index.tsv").read_text() + "2002\t2002.parquet\t" + "0" * 64 + "\n")
    with pytest.raises(verified.Unverified, match="index.tsv hashes to .* the manifest says"):
        prices.load(folder, text, [MONDAY])


def test_a_changed_file_is_refused_and_nothing_is_returned_even_for_the_good_ones(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 2.0)]), 2002: export([("A", NEXT_YEAR, 2.0)])})
    (folder / "2002.parquet").write_bytes((folder / "2002.parquet").read_bytes() + b"x")
    with pytest.raises(verified.Unverified, match="2002.parquet hashes to .* the index says"):
        verified.read_verified(folder, text, "wiki-prices")


def test_a_missing_file_a_missing_index_and_an_unknown_year_are_refused(folder: Path) -> None:
    with pytest.raises(verified.Unverified, match="has no index.tsv"):
        verified.read_verified(folder, "| wiki-prices | x | sha256 " + "0" * 64 + " |", "wiki-prices")
    text = make(folder, {2001: export([("A", MONDAY, 2.0)])})
    with pytest.raises(verified.Unverified, match="the index has no key 1999"):
        verified.read_verified(folder, text, "wiki-prices", ["1999"])
    (folder / "2001.parquet").unlink()
    with pytest.raises(verified.Unverified, match=r"2001\.parquet is listed in the index and absent"):
        verified.read_verified(folder, text, "wiki-prices")


def test_read_verified_returns_the_bytes_that_were_hashed(folder: Path) -> None:
    text = make(folder, {2001: export([("A", MONDAY, 2.0)])})
    found = verified.read_verified(folder, text, "wiki-prices")
    assert list(found) == ["2001"]
    assert found["2001"] == (folder / "2001.parquet").read_bytes()
    assert verified.read_verified(folder, text, "wiki-prices", []) == {}


def test_the_manifest_row_must_exist_and_end_in_a_hash() -> None:
    digest = "ab" * 32
    assert verified.manifest_hash(f"| x | y |\n| d | z | sha256 {digest} (of the index) |\n", "d") == digest
    with pytest.raises(verified.Unverified, match="no row e"):
        verified.manifest_hash(f"| d | z | sha256 {digest} |", "e")
    assert verified.manifest_hash(f"| d | z | sha256 {digest}", "d") == digest  # the cell may be just the hash
    assert verified.manifest_hash(f"|XXd | z | sha256 {digest} |", "XXd") == digest  # only the pipes are trimmed
    for last in ("sha256", "sha256 abc", f"md5 {digest}", f"{digest}"):
        with pytest.raises(verified.Unverified, match="no 'sha256 <hash>'"):
            verified.manifest_hash(f"| d | z | {last} |", "d")


def test_the_index_is_parsed_and_a_bad_line_refused() -> None:
    digest = "cd" * 32
    assert verified.parse_index(f"1998\t1998.parquet\t{digest}\n1999\ta.parquet\t{digest}\n") == {
        "1998": ("1998.parquet", digest), "1999": ("a.parquet", digest)}
    assert verified.parse_index("") == {}
    for bad, why in (
        ("1998\t1998.parquet\n", "index line 1 is not"),
        (f"1998\tf\t{digest}\textra\n", "index line 1 is not"),
        ("1998\tf\tabc\n", "index line 1 is not"),
        (f"1998\tf\t{digest}\n1998\tg\t{digest}\n", "index line 2 repeats the key 1998"),
        (f"1998\t../x.parquet\t{digest}\n", "not a file in the folder"),
        (f"1998\t..\t{digest}\n", "not a file in the folder"),
        (f"1998\t\t{digest}\n", "not a file in the folder"),
    ):
        with pytest.raises(verified.Unverified, match=why):
            verified.parse_index(bad)
