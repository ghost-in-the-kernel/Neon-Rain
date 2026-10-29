"""The 1-month short-term reversal baseline (R-007 c, TODO 3.1 c): a ticker's score is the rank of its negated month.

**Reversal** (docs/GLOSSARY.md) at a universe cell (ticker, *t*) is minus the total return of the adjusted close over
the last `SPAN` (21) sessions: -(close at *t* / close at *t*-21 - 1). Last month's losers are predicted to rise, so
a lower return scores higher. Sessions are those of the calendar, never calendar days. Unlike momentum nothing is
skipped: the window ends at *t* itself. Like the returns family (TODO 2.3) it never fills: the value needs a usable
close (present, finite, above zero) on every one of the 22 sessions from *t*-21 to *t*, so a window that crosses a gap
has none, and neither has a ticker's first 21 sessions. A ticker is never merged, split or dropped (NR-F-05).

`SPAN` is the definition of the name "reversal" (the one-month form), never a knob: a different window is a
different baseline name, or a run with hyperparameters in its config hash (HAR-01). One configuration, run once, is a
trial, not a search (HAR-09).

**The score** is what the harness reads (HAR-07: a score above 0.5 predicts an excess return above 0): the rank
fraction of the negated return among the universe cells that have a value that day, `(rank - 1) / (n - 1)` with ties at
their average rank, so the median ticker scores 0.5, the biggest loser 1 and the biggest winner 0, and a higher score
is a predicted higher excess return. A day with one such cell scores it 0.5. A cell with no value has no score row (a
score frame holds no null, `runner.scored_market`), and no row means no label is scored there.

**The stamp** (HAR-12) is the date of the latest close used: *t* itself, which HAR-12 allows ("the close of *t* itself
is known at *t*"). The label's forward return starts from that same close (HAR-02: P(t+h) / P(t) - 1), but the signal
reads nothing after *t*, so nothing of the label's own window is in the score.

The window is counted by `momentum.window_returns`, the same rule at another span, and ranked by
`momentum.rank_scores`. The prices are the verified frame's adjusted `close`; the caller passes the whole frame, not
one cut at the universe's first date. Pure (HAR-11).
"""
from datetime import date

import polars as pl

from neonrain.baselines import momentum

NAME = "reversal"
SPAN = 21  # sessions back to the start of the window: one month


def scores(prices: pl.DataFrame, universe: pl.DataFrame, calendar: list[date]) -> pl.DataFrame:
    """The score frame of the 1-month reversal baseline: columns ticker, date, score (Float64), stamp (Date), one row
    for each universe cell that has a value, in the universe's own row order."""
    return momentum.rank_scores(prices, universe, calendar, SPAN, 0, descending=True)
