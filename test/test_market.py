"""What the harness is given (docs/HARNESS.md): the frame layouts and HAR-12's stamp refusal, on hand-made frames."""
from datetime import date, datetime, time

import polars as pl
import pytest

from neonrain.harness import market, synthetic
from neonrain.harness.market import LayoutRefused, Market, StampRefused

D1, D2, D3 = date(2000, 1, 3), date(2000, 1, 4), date(2000, 1, 5)
CAL = [D1, D2, D3]


def frame(rows: dict[str, list], schema: dict | None = None) -> pl.DataFrame:
    """A frame from columns; ticker and date typed as the layout says."""
    return pl.DataFrame(rows, schema={"ticker": pl.String, "date": pl.Date, **(schema or {})})


def features(stamps: list[date], value: str = "edge") -> pl.DataFrame:
    """Three cells of ticker A on D1 to D3, one feature with the given stamps."""
    return frame({"ticker": ["A"] * 3, "date": CAL, value: [1.0, 2.0, 3.0], value + "_stamp": stamps},
                 {value: pl.Float64, value + "_stamp": pl.Date})


def honest() -> Market:
    """A tiny valid market: A and B on three dates, one feature stamped with its own date."""
    keys = frame({"ticker": ["A", "A", "A", "B", "B", "B"], "date": CAL * 2})
    prices = keys.with_columns(pl.Series("close", [1.0] * 6))
    both = keys.with_columns(pl.Series("edge", [0.5] * 6), pl.col("date").alias("edge_stamp"))
    return Market(prices, keys, both, CAL)


def refusal(error: type[Exception], message: str) -> "pytest.RaisesExc[Exception]":
    """pytest.raises that holds the whole message, not a fragment."""
    return pytest.raises(error, match=f"^{message}$")


def test_the_synthetic_market_and_an_honest_one_are_accepted() -> None:
    market.check_market(honest())
    market.check_market(synthetic.generate(synthetic.MarketConfig(tickers=5, days=30, delist_below=0.9, seed=3)))


def test_the_synthetic_market_is_the_type_of_this_module() -> None:
    assert isinstance(synthetic.generate(synthetic.MarketConfig(tickers=2, days=3)), Market)


def test_a_stamp_on_the_cells_own_date_or_earlier_is_accepted() -> None:
    market.check_stamps(features([D1, D1, D2]))
    market.check_stamps(features(CAL))


def test_a_stamp_after_its_date_is_refused_naming_the_feature_and_the_cell() -> None:
    message = r"feature 'edge' refused at cell \(A, 2000-01-04\): stamp 2000-01-05 is after the cell's date"
    with refusal(StampRefused, message):
        market.check_stamps(features([D1, D3, D3]).with_columns(pl.col("edge_stamp").shift(0)))


def test_several_late_cells_are_counted_and_the_first_by_ticker_then_date_is_named() -> None:
    late = date(2000, 1, 6)
    a_late_on_d3 = features([D1, D2, late])
    b_late_on_d1_and_d2 = features([D2, D3, D3]).with_columns(pl.lit("B").alias("ticker"))
    message = r"feature 'edge' refused at cell \(A, 2000-01-05\): stamp 2000-01-06 is after the cell's date \(and 2 more cells\)"
    with refusal(StampRefused, message):
        market.check_stamps(pl.concat([b_late_on_d1_and_d2, a_late_on_d3]).sort("date", descending=True))


def test_within_one_ticker_the_earliest_late_cell_is_named() -> None:
    late = features([D1, date(2000, 1, 7), date(2000, 1, 6)])
    message = r"feature 'edge' refused at cell \(A, 2000-01-04\): stamp 2000-01-07 is after the cell's date \(and 1 more cells\)"
    with refusal(StampRefused, message):
        market.check_stamps(late.sort("date", descending=True))


def test_the_first_feature_by_name_is_the_one_named() -> None:
    wide = features(CAL).join(features([D3, D3, D3], "alpha").drop("ticker").rename({"alpha": "alpha"}), on="date")
    wide = wide.select("ticker", "date", "edge", "edge_stamp", "alpha", "alpha_stamp")
    message = r"feature 'alpha' refused at cell \(A, 2000-01-03\): stamp 2000-01-05 is after the cell's date \(and 1 more cells\)"
    with refusal(StampRefused, message):
        market.check_stamps(wide)


def test_a_news_stamp_before_the_cut_is_accepted_and_at_or_after_it_refused() -> None:
    cut = time(16, 30)
    before, at = datetime(2000, 1, 3, 16, 29, 59), datetime(2000, 1, 4, 16, 30)
    news = frame({"ticker": ["A"] * 3, "date": CAL, "tone": [1.0, 2.0, 3.0],
                  "tone_stamp": [before, at, datetime(2000, 1, 4)]}, {"tone": pl.Float64, "tone_stamp": pl.Datetime})
    message = r"feature 'tone' refused at cell \(A, 2000-01-04\): stamp 2000-01-04 16:30:00.000000 is at or after the news cut"
    with refusal(StampRefused, message):
        market.check_stamps(news, cut)
    market.check_stamps(news.head(1), cut)
    market.check_stamps(news.tail(1), cut)


def test_a_news_stamp_needs_a_cutoff_and_one_without_a_zone() -> None:
    news = frame({"ticker": ["A"], "date": [D1], "tone": [1.0], "tone_stamp": [datetime(2000, 1, 1)]},
                 {"tone": pl.Float64, "tone_stamp": pl.Datetime})
    with refusal(LayoutRefused, "a news feature \\(a Datetime stamp\\) needs the run's news cutoff time, and none was given"):
        market.check_stamps(news)
    with refusal(LayoutRefused, "the news cutoff time must have no time zone: stamps and cuts are UTC"):
        market.check_stamps(news, time(16, tzinfo=datetime.now().astimezone().tzinfo))


def test_the_cut_counts_hours_minutes_seconds_and_microseconds() -> None:
    news = frame({"ticker": ["A"], "date": [D1], "tone": [1.0], "tone_stamp": [datetime(2000, 1, 3, 1, 2, 3, 4)]},
                 {"tone": pl.Float64, "tone_stamp": pl.Datetime})
    market.check_stamps(news, time(1, 2, 3, 5))
    with pytest.raises(StampRefused):
        market.check_stamps(news, time(1, 2, 3, 4))
    with pytest.raises(StampRefused):
        market.check_stamps(news, time(1, 2, 3, 3))


def test_a_value_with_no_stamp_is_refused_and_an_empty_cell_may_have_none() -> None:
    ok = features([D1, D2, D3]).with_columns(pl.when(pl.col("date") == D2).then(None).otherwise(pl.col("edge")).alias("edge"),
                                             pl.when(pl.col("date") == D2).then(None).otherwise(pl.col("edge_stamp")).alias("edge_stamp"))
    market.check_stamps(ok)
    bad = ok.with_columns(pl.lit(1.0).alias("edge"))
    with refusal(StampRefused, r"feature 'edge' refused at cell \(A, 2000-01-04\): value has no stamp"):
        market.check_stamps(bad)


def test_a_stamp_of_another_type_is_refused() -> None:
    odd = features(CAL).with_columns(pl.lit("x").alias("edge_stamp"))
    with refusal(LayoutRefused, "stamp column 'edge_stamp' is String, expected Date or Datetime without a time zone"):
        market.check_stamps(odd)
    zoned = features(CAL).with_columns(pl.col("edge_stamp").cast(pl.Datetime).dt.replace_time_zone("UTC"))
    with pytest.raises(LayoutRefused):
        market.check_stamps(zoned, time(0))


def test_a_feature_and_its_stamp_must_come_as_a_pair() -> None:
    with refusal(LayoutRefused, "feature 'edge' has no edge_stamp column"):
        market.check_stamps(features(CAL).drop("edge_stamp"))
    with refusal(LayoutRefused, "stamp column 'edge_stamp' has no feature 'edge'"):
        market.check_stamps(features(CAL).drop("edge"))
    with refusal(LayoutRefused, "feature 'edge' is String, expected a number"):
        market.check_stamps(features(CAL).with_columns(pl.lit("x").alias("edge")))


def test_the_layout_of_each_frame_is_held() -> None:
    good = honest()
    with refusal(LayoutRefused, "price frame has no close column"):
        market.check_market(good._replace(prices=good.prices.drop("close")))
    with refusal(LayoutRefused, "price frame's close column is Int64, expected Float64"):
        market.check_market(good._replace(prices=good.prices.with_columns(pl.col("close").cast(pl.Int64))))
    with refusal(LayoutRefused, r"universe frame has columns \['ticker', 'date', 'x'\], expected \['ticker', 'date'\]"):
        market.check_market(good._replace(universe=good.universe.with_columns(pl.lit(1).alias("x"))))
    with refusal(LayoutRefused, "feature frame has no date column"):
        market.check_market(good._replace(features=good.features.drop("date")))
    with refusal(LayoutRefused, "price frame's ticker column is Int64, expected String"):
        market.check_market(good._replace(prices=good.prices.with_columns(pl.col("ticker").cast(pl.Int64, strict=False))))
    with refusal(LayoutRefused, "universe frame's date column is String, expected Date"):
        market.check_market(good._replace(universe=good.universe.with_columns(pl.col("date").cast(pl.String))))


def test_a_null_or_repeated_key_is_refused() -> None:
    good = honest()
    with refusal(LayoutRefused, "price frame has a null ticker or date"):
        market.check_market(good._replace(prices=good.prices.with_columns(pl.lit(None, dtype=pl.Date).alias("date"))))
    with refusal(LayoutRefused, "universe frame has a null ticker or date"):
        market.check_market(good._replace(universe=good.universe.with_columns(pl.lit(None, dtype=pl.String).alias("ticker"))))
    twice = pl.concat([good.universe, good.universe.head(1)])
    with refusal(LayoutRefused, r"universe frame has more than one row for \(A, 2000-01-03\)"):
        market.check_market(good._replace(universe=twice))
    two_repeats = pl.concat([good.universe, good.universe.filter(pl.col("ticker") == "B").tail(2), good.universe.head(2)])
    with refusal(LayoutRefused, r"universe frame has more than one row for \(A, 2000-01-03\)"):
        market.check_market(good._replace(universe=two_repeats.sort("date", descending=True)))


def test_the_first_row_off_the_calendar_is_named_by_ticker_then_date() -> None:
    off = frame({"ticker": ["B", "A", "A"], "date": [date(2000, 1, 3), date(2000, 1, 7), date(2000, 1, 6)]})
    with refusal(LayoutRefused, r"price frame has a row \(A, 2000-01-06\) off the calendar"):
        market.check_on_calendar("price", off, [date(2000, 1, 4)])


def test_check_market_gives_the_news_cutoff_to_the_stamp_check() -> None:
    good = honest()
    news = good.features.with_columns(pl.col("edge_stamp").cast(pl.Datetime))
    market.check_market(good._replace(features=news), time(0, 0, 1))
    with pytest.raises(StampRefused):
        market.check_market(good._replace(features=news), time(0))
    with refusal(LayoutRefused, "a news feature \\(a Datetime stamp\\) needs the run's news cutoff time, and none was given"):
        market.check_market(good._replace(features=news))


def test_the_calendar_is_ascending_and_holds_every_date() -> None:
    good = honest()
    with refusal(LayoutRefused, "calendar is empty"):
        market.check_market(good._replace(calendar=[]))
    with refusal(LayoutRefused, "calendar is not strictly ascending: 2000-01-04 follows 2000-01-04"):
        market.check_market(good._replace(calendar=[D1, D2, D2, D3]))
    with refusal(LayoutRefused, "calendar is not strictly ascending: 2000-01-03 follows 2000-01-04"):
        market.check_market(good._replace(calendar=[D2, D1, D3]))
    market.check_market(good._replace(calendar=[D1, D2, D3, date(2000, 1, 6)]))
    labels = {"prices": "price", "universe": "universe", "features": "feature"}
    for name, label in labels.items():
        trimmed = {other: getattr(good, other).filter(pl.col("date") <= D2) for other in labels if other != name}
        message = f"{label} frame has a row \\(A, 2000-01-05\\) off the calendar"
        with refusal(LayoutRefused, message):
            market.check_market(good._replace(**trimmed, calendar=[D1, D2]))


def test_a_leaking_market_is_refused_as_a_whole() -> None:
    good = honest()
    leaking = good.features.with_columns(pl.col("edge_stamp").dt.offset_by("1d"))
    with pytest.raises(StampRefused, match=r"^feature 'edge' refused at cell \(A, 2000-01-03\)"):
        market.check_market(good._replace(features=leaking, calendar=[D1, D2, D3, date(2000, 1, 6)]))
