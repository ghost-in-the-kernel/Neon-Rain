# TODO: the open items, in order

The roadmap as a chain: items are done in this order, never out of it, and an item that cannot be
done as written stops the chain and goes to Ghost. Each item's plan is its step in docs/ROADMAP.md
§6, by the same number; its check is the roadmap's, copied here. A done item moves to `docs/DONE.md`
with its number kept. `test/test_todo.py` (phase 0.5) holds this file: headings in numeric order,
and the first open item has a check.

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

### 2.1 Universe

(a) The trading calendar: the exact NYSE calendar, derived in `neonrain/universe/` by rule
(weekends, each holiday's rule and the years it held, the special closures listed with their
reason), no dependency (Ghost, J-033). (b) Membership, from WIKI. Plan:
`scripts/fetch/wiki.py` joins the raw parts in the data repository's clone, refuses them unless
they hash to the manifest's line, and writes the sample as yearly parquet (`wiki/prices/<year>.parquet`,
each under 100 MB) back to the data repository, one manifest line with the hash of their index (the
reviewer pushes). `neonrain/universe/membership.py`, a pure function of the price frame: each
ticker's first and last date in the sample; a last date before 2017-11-07 is a ticker that left;
the universe on each date is the 1,000 names with the largest trailing 63-session median dollar
volume, known at that date (no look-ahead). Findings: the share of tickers that leave against
the few percent a year the market loses; tickers reused by another company; how WIKI marks a
delisting, if at all.
Check: (a) the calendar gives the NYSE's sessions for hand-checked years and closures (Good Friday,
Juneteenth from 2022, 2001-09-11 to 09-14, 2012-10-29 and 30, the national days of mourning);
(b) every ticker has dates in and out, and the gap is a finding. (a) is done (J-039); (b) is next.

### 2.5 The feature table

Check: cached to the artifact store by content hash (`scripts/fetch/artifacts.py`); a fetch rebuilds
it byte for byte.

### 2.6 Tithe pass 2

Plan: `docs/rules/tithe.md`. Check: AGENT.md re-measured; every debrief given a verdict, the log
wiped and "Last review" moved; open questions in the journal (R-023).

## Phase 3: baselines

## Phase 4: the network

## Phase 5: news

## Phase 6: the news-augmented model and the ablations

## Phase 7: the forward test
