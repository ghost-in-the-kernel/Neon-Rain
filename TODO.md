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

Prices and universe membership come only from `neon-rain-data` (R-016), supplied by Ghost from a
source whose license allows commercial use (R-016 d). Nothing in this phase is built from data
until that is there; the calendar is not data.

### 2.1 Universe

(a) The trading calendar: the exact NYSE calendar, derived in `neonrain/universe/` by rule
(weekends, each holiday's rule and the years it held, the special closures listed with their
reason), no dependency (Ghost, J-033). (b) Membership with dates in and out, delistings where the
source gives them, from Ghost's dataset; `docs/FINDINGS.md` records the survivorship gap.
Check: (a) the calendar gives the NYSE's sessions for hand-checked years and closures (Good Friday,
Juneteenth from 2022, 2001-09-11 to 09-14, 2012-10-29 and 30, the national days of mourning);
(b) every ticker has dates in and out, and the gap is a finding. (a) is done (J-039); (b) waits on
Ghost's dataset.

### 2.2 Daily prices

Check: OHLCV for ten or more years, fetched by script from `neon-rain-data` and manifested (R-006);
every price date is a session of 2.1's calendar.

### 2.3 Price-derived features

Check: each family has a glossary term and a pure function from prices with a unit test against a
hand-computed window.

### 2.4 Cross-sectional normalization

Check: no feature carries the market level: per day, each is a rank or z-score within the universe.

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
