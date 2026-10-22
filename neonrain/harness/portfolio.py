"""The long–short decile portfolio of HAR-07, after the costs of HAR-06 and R-021.

Plain loops over sleeves and names, so each line can be read against the contract. Pure: frames in, a frame out.
"""
import math
from datetime import date
from typing import NamedTuple

import numpy as np
import polars as pl

DEFAULT_COST_BPS = 10.0
COST_LEVELS_BPS: tuple[float, ...] = (0.0, 10.0, 25.0)
SERIES: dict[str, type[pl.DataType]] = {"date": pl.Date, "gross": pl.Float64, "cost": pl.Float64, "net": pl.Float64}


class Sleeve(NamedTuple):
    """One sleeve's (or leg's) effect on every calendar position, before its 1/h share: return and cost."""

    returns: np.ndarray
    costs: np.ndarray


def wide_closes(prices: pl.DataFrame, calendar: list[date], tickers: list[str]) -> np.ndarray:
    """Closes as an array [calendar position, ticker], NaN where there is no price."""
    index = {d: i for i, d in enumerate(calendar)}
    column = {t: j for j, t in enumerate(tickers)}
    closes = np.full((len(calendar), len(tickers)), np.nan)
    for ticker, day, close in prices.select("ticker", "date", "close").iter_rows():
        if ticker in column and day in index:
            closes[index[day], column[ticker]] = close
    return closes


def legs(scores: list[tuple[str, float]], column: dict[str, int]) -> tuple[list[int], list[int]]:
    """The short and long legs: ascending by (score, ticker), the first n and the last n, n = ⌊N/10⌋.

    For 20 tickers scored 0..19 the short leg is the two lowest and the long leg the two highest.
    """
    ordered = sorted(scores, key=lambda pair: (pair[1], pair[0]))
    n = len(ordered) // 10
    if n == 0:
        return [], []
    return [column[t] for t, _ in ordered[:n]], [column[t] for t, _ in ordered[-n:]]


# Decision: R-021 (opening, closing and a delisting each pay; both legs count; no netting)
def leg_days(closes: np.ndarray, opened: int, names: list[int], horizon: int, cost: float) -> Sleeve:
    """One leg held from the close of `opened` for `horizon` days: its mean daily return and its closing costs.

    Each name weighs 1/n; a name with no price on a day is closed at its last price and pays there (HAR-07).
    """
    last = closes.shape[0] - 1
    returns = np.zeros(closes.shape[0])
    costs = np.zeros(closes.shape[0])
    for name in names:
        closed = min(opened + horizon, last)
        for day in range(opened, closed):
            if math.isnan(closes[day + 1, name]):
                closed = day
                break
            returns[day + 1] += (closes[day + 1, name] / closes[day, name] - 1.0) / len(names)
        costs[closed] += cost / len(names)
    return Sleeve(returns, costs)


def sleeve(closes: np.ndarray, opened: int, short: list[int], long: list[int], horizon: int, cost: float) -> Sleeve:
    """A sleeve: the long leg's return minus the short leg's; it pays 2·cost to open (both legs) and each close."""
    up = leg_days(closes, opened, long, horizon, cost)
    down = leg_days(closes, opened, short, horizon, cost)
    costs = up.costs + down.costs
    costs[opened] += 2.0 * cost
    return Sleeve(up.returns - down.returns, costs)


def daily(scores: pl.DataFrame, prices: pl.DataFrame, calendar: list[date], horizon: int,
          cost_bps: float = DEFAULT_COST_BPS) -> pl.DataFrame:
    """The portfolio's daily series: date, gross, cost, net (= gross − cost), from the first test date to the last
    day a sleeve touches. `scores` has ticker, date, score: one row per tested ticker per test date.

    Dates are taken in calendar order, so the sums are added in the same order every run (HAR-11).
    """
    if scores.height == 0:
        return pl.DataFrame(schema=SERIES)
    tickers = sorted(set(scores["ticker"].to_list()))
    column = {t: j for j, t in enumerate(tickers)}
    closes = wide_closes(prices, calendar, tickers)
    index = {d: i for i, d in enumerate(calendar)}
    gross, paid = np.zeros(len(calendar)), np.zeros(len(calendar))
    opens = sorted(index[d] for d in set(scores["date"].to_list()))
    for opened in opens:
        group = scores.filter(pl.col("date") == calendar[opened]).select("ticker", "score").iter_rows()
        priced = [(t, s) for t, s in group if not math.isnan(closes[opened, column[t]])]
        short, long = legs(priced, column)
        if not long:
            continue
        held = sleeve(closes, opened, short, long, horizon, cost_bps / 10000.0)
        gross += held.returns / horizon
        paid += held.costs / horizon
    return series(gross, paid, calendar, opens[0], min(opens[-1] + horizon, len(calendar) - 1))


def series(gross: np.ndarray, paid: np.ndarray, calendar: list[date], start: int, end: int) -> pl.DataFrame:
    """The positions start..end (inclusive) with each day's gross return, cost and net; days with no sleeve are
    cash (0)."""
    rows = [(calendar[p], gross[p], paid[p], gross[p] - paid[p]) for p in range(start, end + 1)]
    return pl.DataFrame(rows, schema=SERIES, orient="row")
