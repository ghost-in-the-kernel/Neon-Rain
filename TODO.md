# TODO: the open items, in order

The roadmap as a chain: items are done in this order, never out of it, and an item that cannot be
done as written stops the chain and goes to Ghost. Each item's plan is its step in docs/ROADMAP.md
§6, by the same number; its check is the roadmap's, copied here. A done item moves to `docs/DONE.md`
with its number kept. `test/test_todo.py` (phase 0.5) holds this file: headings in numeric order,
and the first open item has a check: a line that begins `Check:` (mid-line it does not count; 2.6
was red for it, J-068).

## Phase 0: founding

## Phase 1: the harness

Nothing under `neonrain/models/` or `neonrain/baselines/` begins until 1.6 passes (R-002).

## Phase 2: real data

The source is Quandl's WIKI prices (Ghost, 2026-10-24, J-041): about 3,000 US companies, daily
OHLCV, dividends, splits and adjusted columns, public domain, frozen since 2018-04-11. The raw export
is staged in `neon-rain-data` (`raw/wiki/`, five parts, its hash on `data/MANIFEST.md`; J-042). The
sample is 1998-01-02 to 2017-11-07: the calendar's first year to the last session before the feed's
holes (R-026, NR-F-07; the plan's first date was 2017-12-29). Every result on it is reported for two
periods apart, before 2014-04-01 (survivor-only) and from it (R-026, NR-F-03). 

## Phase 3: baselines

Nothing under `neonrain/baselines/` existed before this phase; 1.6 passed, so it may begin (R-002).
WIKI's licence is accepted for private research and a portfolio piece (D-002, in `neon-rain-data`):
its results may be reported, none licensed or sold. Every result is for two periods apart (R-026).

## Phase 4: the network

## Phase 5: news

## Phase 6: the news-augmented model and the ablations

## Phase 7: the forward test
