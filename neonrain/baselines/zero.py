"""The zero baseline (R-007 a, TODO 3.1 a): predict the median, which is predicting an excess return of 0.

HAR-02 makes a label the excess over the day's universe median, so the median's own prediction is excess 0, and as a
direction score that is exactly 0.5 for every cell. HAR-07 then reports what it reports (a score of 0.5 predicts 0, so
accuracy is the share of down labels; every date's scores are equal, so the IC drops every date as flat). The score is
not replaced by a random one: the harness's answer to a constant is the result. Pure.
"""
import polars as pl

SCORE = 0.5
NAME = "zero"


def scores(universe: pl.DataFrame) -> pl.DataFrame:
    """A score of 0.5 for every universe cell, stamped with the cell's own date (nothing else was read): columns
    ticker, date, score (Float64), stamp (Date)."""
    return universe.select("ticker", "date", pl.lit(SCORE).alias("score"), pl.col("date").alias("stamp"))
