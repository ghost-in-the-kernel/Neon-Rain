"""Cross-sectional normalization (TODO 2.4) on invented frames: tickers T00 to T24, values whose ranks are done by hand.

No real price is in this file (R-006). A cross-section needs at least MIN_NAMES (20) valued names, so the frames hold
20 to 25 tickers; a feature value v at rank r among n names reads (r - 1) / (n - 1) - 0.5.
"""
from datetime import date, timedelta

import polars as pl
import pytest

from neonrain import targets
from neonrain.features import common, normalize, returns
from neonrain.harness import market

FIRST = date(2001, 1, 1)
DAYS = [FIRST + timedelta(days=i) for i in range(40)]
TICKERS = [f"T{i:02d}" for i in range(25)]


def features(rows: list[tuple[str, int, float | None]], stamps: dict[tuple[str, int], int] | None = None) -> pl.DataFrame:
    """A feature frame with one feature `f`, from (ticker, day index, value); the stamp is the cell's own day unless given."""
    stamps = stamps or {}
    return pl.DataFrame(
        {
            "ticker": [r[0] for r in rows],
            "date": [DAYS[r[1]] for r in rows],
            "f": [r[2] for r in rows],
            "f_stamp": [DAYS[stamps.get((r[0], r[1]), r[1])] if r[2] is not None else None for r in rows],
        },
        schema={"ticker": pl.String, "date": pl.Date, "f": pl.Float64, "f_stamp": pl.Date},
    )


def universe(rows: list[tuple[str, int]]) -> pl.DataFrame:
    """A universe frame from (ticker, day index)."""
    return pl.DataFrame({"ticker": [r[0] for r in rows], "date": [DAYS[r[1]] for r in rows]}, schema=market.KEYS)


def day(values: list[float | None], i: int = 0) -> list[tuple[str, int, float | None]]:
    """The rows of one date: ticker T00 takes values[0], T01 values[1] and so on."""
    return [(TICKERS[j], i, v) for j, v in enumerate(values)]


def everyone(rows: list[tuple[str, int, float | None]]) -> pl.DataFrame:
    """A universe holding every cell of the rows."""
    return universe([(r[0], r[1]) for r in rows])


def out(frame: pl.DataFrame, ticker: str, i: int, column: str = "f") -> float | date | None:
    """One cell of a normalized frame, by ticker and day index."""
    return frame.filter((pl.col("ticker") == ticker) & (pl.col("date") == DAYS[i]))[column].item()


def test_constants_are_the_harnesss() -> None:
    assert normalize.MIN_NAMES == targets.MIN_TICKERS == 20
    assert normalize.CENTRE == 0.5
    assert normalize.KEYS == tuple(market.KEYS)
    assert common.STAMP_SUFFIX == market.STAMP_SUFFIX


def test_a_value_is_its_centred_rank() -> None:
    values = [float(v) for v in (7, 3, 21, 1, 15, 9, 2, 20, 4, 5, 6, 8, 10, 11, 12, 13, 14, 16, 17, 18, 19)]
    rows = day(values)
    result = normalize.normalize(features(rows), everyone(rows))
    # 21 names, ranks 1..21 equal the values: rank r reads (r - 1) / 20 - 0.5
    assert out(result, "T03", 0) == -0.5  # value 1, the lowest
    assert out(result, "T02", 0) == 0.5  # value 21, the highest
    assert out(result, "T00", 0) == pytest.approx(6 / 20 - 0.5)  # value 7
    assert out(result, "T10", 0) == pytest.approx(5 / 20 - 0.5)  # value 6
    assert out(result, "T12", 0) == pytest.approx(9 / 20 - 0.5)  # value 10
    assert out(result, "T15", 0) == pytest.approx(12 / 20 - 0.5)  # value 13
    assert out(result, "T20", 0) == pytest.approx(18 / 20 - 0.5)  # value 19


def test_the_middle_name_of_an_odd_cross_section_is_zero_and_the_mean_is_zero() -> None:
    rows = day([float(v) * v for v in range(21)])
    result = normalize.normalize(features(rows), everyone(rows))
    assert out(result, "T10", 0) == 0.0
    assert result["f"].sum() == pytest.approx(0.0, abs=1e-12)


def test_ties_take_the_average_rank() -> None:
    # 20 names: four at 0 (ranks 1 to 4, average 2.5), the others 1 to 16 (ranks 5 to 20)
    rows = day([0.0] * 4 + [float(v) for v in range(1, 17)])
    result = normalize.normalize(features(rows), everyone(rows))
    for ticker in ("T00", "T01", "T02", "T03"):
        assert out(result, ticker, 0) == pytest.approx(1.5 / 19 - 0.5)
    assert out(result, "T04", 0) == pytest.approx(4 / 19 - 0.5)
    assert out(result, "T19", 0) == 0.5
    assert result["f"].sum() == pytest.approx(0.0, abs=1e-12)


def test_the_day_s_level_and_scale_do_not_move_a_rank() -> None:
    base = [float(v) for v in range(25)]
    rows = day(base, 0) + [(t, 1, 100.0 + 3.0 * v) for t, v in zip(TICKERS, base)] + [(t, 2, 1.0 + v**3) for t, v in zip(TICKERS, base)]
    result = normalize.normalize(features(rows), everyone(rows))
    for ticker in TICKERS:
        assert out(result, ticker, 0) == pytest.approx(out(result, ticker, 1))
        assert out(result, ticker, 0) == pytest.approx(out(result, ticker, 2))


def test_each_date_is_its_own_cross_section() -> None:
    rows = day([float(v) for v in range(25)], 0) + day([float(24 - v) for v in range(25)], 1)
    result = normalize.normalize(features(rows), everyone(rows))
    assert out(result, "T00", 0) == -0.5 and out(result, "T00", 1) == 0.5
    assert out(result, "T24", 0) == 0.5 and out(result, "T24", 1) == -0.5


def test_a_null_stays_null_and_is_left_out_of_the_cross_section() -> None:
    values: list[float | None] = [None] + [float(v) for v in range(1, 21)]
    rows = day(values)
    result = normalize.normalize(features(rows), everyone(rows))
    assert out(result, "T00", 0) is None and out(result, "T00", 0, "f_stamp") is None
    # n is 20, not 21: the lowest valued name is -0.5, the highest +0.5
    assert out(result, "T01", 0) == -0.5
    assert out(result, "T20", 0) == 0.5
    assert out(result, "T01", 0, "f_stamp") == DAYS[0]


def test_a_value_that_is_not_finite_is_a_null() -> None:
    values: list[float | None] = [float("nan"), float("inf"), float("-inf")] + [float(v) for v in range(1, 21)]
    rows = day(values)
    result = normalize.normalize(features(rows), everyone(rows))
    for ticker in ("T00", "T01", "T02"):
        assert out(result, ticker, 0) is None and out(result, ticker, 0, "f_stamp") is None
    assert out(result, "T03", 0) == -0.5 and out(result, "T22", 0) == 0.5  # n is 20


def test_fewer_than_the_fewest_names_gives_null_and_exactly_the_fewest_gives_values() -> None:
    thin = day([float(v) for v in range(19)] + [None])
    result = normalize.normalize(features(thin), everyone(thin))
    assert result["f"].null_count() == 20 and result["f_stamp"].null_count() == 20
    enough = day([float(v) for v in range(20)])
    result = normalize.normalize(features(enough), everyone(enough))
    assert result["f"].null_count() == 0 and out(result, "T00", 0) == -0.5


def test_the_fewest_is_counted_by_date() -> None:
    rows = day([float(v) for v in range(20)], 0) + day([float(v) for v in range(19)], 1)
    result = normalize.normalize(features(rows), everyone(rows))
    assert out(result, "T00", 0) == -0.5
    assert out(result, "T00", 1) is None and out(result, "T18", 1) is None


def test_a_name_outside_the_universe_takes_no_part_and_gets_no_row() -> None:
    inside = day([float(v) for v in range(20)])
    wild = [("OUT", 0, 1e9)]
    frame = features(inside + wild)
    result = normalize.normalize(frame, everyone(inside))
    assert result.height == 20 and "OUT" not in result["ticker"].to_list()
    assert result.equals(normalize.normalize(features(inside), everyone(inside)))  # the outsider moved no rank


def test_a_universe_cell_without_a_feature_row_keeps_a_null_row_and_is_not_counted() -> None:
    inside = day([float(v) for v in range(20)])
    cells = universe([(r[0], r[1]) for r in inside] + [("T24", 0), ("T23", 1)])
    result = normalize.normalize(features(inside), cells)
    assert result.height == 22
    assert out(result, "T24", 0) is None and out(result, "T24", 0, "f_stamp") is None
    assert out(result, "T23", 1) is None  # a date with no feature rows at all
    assert out(result, "T00", 0) == -0.5 and out(result, "T19", 0) == 0.5  # n is 20, the missing cell not counted


def test_a_name_ranks_only_on_the_dates_it_is_in_the_universe() -> None:
    rows = day([float(v) for v in range(21)], 0) + day([float(v) for v in range(21)], 1)
    cells = universe([r for r in [(r[0], r[1]) for r in rows] if not (r[0] == "T00" and r[1] == 1)])
    result = normalize.normalize(features(rows), cells)
    assert out(result, "T00", 0) == -0.5
    assert result.filter((pl.col("ticker") == "T00") & (pl.col("date") == DAYS[1])).height == 0
    assert out(result, "T01", 1) == -0.5  # T00 is outside the universe on day 1, so T01 is the lowest of 20


def test_the_stamp_is_the_latest_stamp_of_the_cross_section() -> None:
    rows = day([float(v) for v in range(22)], 5)
    stamps = {("T04", 5): 3, ("T07", 5): 5, ("T09", 5): 2}
    result = normalize.normalize(features(rows, stamps), everyone(rows))
    assert result["f_stamp"].unique().to_list() == [DAYS[5]]
    early = {(t, 5): 2 for t in TICKERS}
    early[("T11", 5)] = 4
    result = normalize.normalize(features(rows, early), everyone(rows))
    assert result["f_stamp"].unique().to_list() == [DAYS[4]]  # the latest of 2 and 4, on every valued cell
    assert result.schema["f_stamp"] == pl.Date


def test_a_stamp_from_a_cell_without_a_value_is_not_an_input() -> None:
    rows = day([None] + [float(v) for v in range(21)], 5)
    frame = features(rows).with_columns(f_stamp=pl.when(pl.col("f").is_null()).then(DAYS[30]).otherwise(pl.col("f_stamp")))
    result = normalize.normalize(frame, everyone(rows))
    assert result["f_stamp"].drop_nulls().unique().to_list() == [DAYS[5]]


def test_the_layout_is_the_families_and_passes_the_harness() -> None:
    rows = day([float(v) for v in range(25)], 1) + day([float(v) for v in range(25)], 0)
    frame = features(rows).with_columns(g=pl.col("f") * -1.0, g_stamp=pl.col("f_stamp"))
    result = normalize.normalize(frame, everyone(rows))
    assert result.columns == ["ticker", "date", "f", "f_stamp", "g", "g_stamp"]
    assert result.schema["f"] == pl.Float64 and result.schema["g"] == pl.Float64
    assert result["ticker"].to_list() == sorted(result["ticker"].to_list())
    assert result.select("ticker", "date").equals(result.select("ticker", "date").sort("ticker", "date"))
    assert market.stamp_columns(result) == {"f": "f_stamp", "g": "g_stamp"}
    market.check_stamps(result)
    assert out(result, "T00", 0, "g") == 0.5 and out(result, "T00", 0) == -0.5  # g reverses f
    assert result["f"].min() >= -0.5 and result["f"].max() <= 0.5


def test_an_integer_feature_is_ranked_as_a_float() -> None:
    rows = day([float(v) for v in range(20)])
    frame = features(rows).with_columns(pl.col("f").cast(pl.Int64))
    result = normalize.normalize(frame, everyone(rows))
    assert result.schema["f"] == pl.Float64 and out(result, "T19", 0) == 0.5


def test_a_feature_is_normalized_on_its_own_names() -> None:
    f = day([float(v) for v in range(25)])
    frame = features(f).with_columns(
        g=pl.Series([None] * 6 + [float(v) for v in range(19)], dtype=pl.Float64), g_stamp=pl.col("f_stamp")
    )
    result = normalize.normalize(frame, everyone(f))
    assert out(result, "T00", 0) == -0.5 and out(result, "T24", 0) == 0.5  # f has 25 names
    assert out(result, "T06", 0, "g") is None  # g has 19: below the fewest, all null
    full = features(f).with_columns(g=pl.Series([None] * 5 + [float(v) for v in range(20)], dtype=pl.Float64), g_stamp=pl.col("f_stamp"))
    result = normalize.normalize(full, everyone(f))
    assert out(result, "T05", 0, "g") == -0.5 and out(result, "T00", 0, "g") is None  # g has 20, its own n


def test_other_dates_move_nothing() -> None:
    base = day([float((v * 7) % 25) for v in range(25)], 3)
    other = day([float(v) for v in range(25)], 2) + day([float(v) for v in range(25)], 4)
    changed = day([float((v * 11) % 25) for v in range(25)], 2) + day([1.0 * (v % 3) for v in range(25)], 4)
    cells = universe([(t, i) for t in TICKERS for i in (2, 3, 4)])
    one = normalize.normalize(features(base + other), cells)
    two = normalize.normalize(features(base + changed), cells)
    assert one.filter(pl.col("date") == DAYS[3]).equals(two.filter(pl.col("date") == DAYS[3]))
    assert not one.filter(pl.col("date") == DAYS[2]).equals(two.filter(pl.col("date") == DAYS[2]))


def test_a_later_price_moves_nothing_through_the_returns_family() -> None:
    sessions = DAYS[:30]
    closes = {t: [10.0 + (j * 7 + i * (j % 5 + 1)) % 17 for i in range(30)] for j, t in enumerate(TICKERS)}

    def prices(after: int, bump: float) -> pl.DataFrame:
        rows = [(t, DAYS[i], closes[t][i] * (bump ** (j % 4) if i > after else 1.0)) for j, t in enumerate(TICKERS) for i in range(30)]
        return pl.DataFrame(rows, schema=market.PRICE_COLUMNS, orient="row")

    cells = universe([(t, i) for t in TICKERS for i in range(30)])
    at = 15
    one = normalize.normalize(returns.returns(prices(at, 1.0), sessions), cells)
    two = normalize.normalize(returns.returns(prices(at, 3.0), sessions), cells)
    earlier = pl.col("date") <= DAYS[at]
    assert one.filter(earlier).height == 25 * 16 and one.filter(earlier)["ret_3"].null_count() < 25 * 16
    assert one.filter(earlier).equals(two.filter(earlier))
    assert not one.filter(~earlier).equals(two.filter(~earlier))


def test_a_frame_without_a_key_is_refused() -> None:
    rows = day([float(v) for v in range(20)])
    with pytest.raises(normalize.NotAFeatureFrame, match="no date column"):
        normalize.normalize(features(rows).drop("date"), everyone(rows))
    with pytest.raises(normalize.NotAFeatureFrame, match="no ticker column"):
        normalize.normalize(features(rows).drop("ticker"), everyone(rows))


def test_a_feature_without_its_stamp_or_a_stamp_without_its_feature_is_refused() -> None:
    rows = day([float(v) for v in range(20)])
    with pytest.raises(normalize.NotAFeatureFrame, match=r"feature 'f' has no f_stamp column"):
        normalize.normalize(features(rows).drop("f_stamp"), everyone(rows))
    with pytest.raises(normalize.NotAFeatureFrame, match=r"stamp column 'f_stamp' has no feature"):
        normalize.normalize(features(rows).drop("f"), everyone(rows))


def test_a_repeated_cell_is_refused_in_either_frame() -> None:
    rows = day([float(v) for v in range(20)])
    with pytest.raises(normalize.NotAFeatureFrame, match=r"^frame has more than one row for some \(ticker, date\)$"):
        normalize.normalize(features(rows + rows[:1]), everyone(rows))
    with pytest.raises(normalize.NotAFeatureFrame, match=r"^universe has more than one row for some \(ticker, date\)$"):
        normalize.normalize(features(rows), universe([(r[0], r[1]) for r in rows + rows[:1]]))


def test_feature_names_in_order() -> None:
    rows = day([float(v) for v in range(20)])
    frame = features(rows).with_columns(a=pl.col("f"), a_stamp=pl.col("f_stamp"))
    assert normalize.feature_names(frame) == ["f", "a"]
    assert normalize.feature_names(frame.select("ticker", "date")) == []
