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

### 3.1 Zero, momentum, reversal

Plan: ROADMAP 3.1. One item, three tasks in order, a fresh agent each: (a) the zero baseline and the
runner, (b) momentum (12-1), (c) short-term reversal (1 month). The zero baseline scores 0.5 for
every cell (predicting the median is predicting excess 0, HAR-02); the harness reports what that
gives (accuracy as it is; IC undefined with every date in `dropped_flat`; the portfolio as HAR-07 gives a
constant: the tie-break's book, its after-cost Sharpe the turnover floor, NR-F-10), and that is
the result. The feature table has no 12-month return: momentum and reversal are signals from the
verified prices (`neonrain/universe/prices.py`), each with a glossary term before its file (P-08).
Check: (a) zero, a score of 0.5 for every cell (the median's excess is 0), through the frozen
harness on the feature table at all four horizons, each period apart (R-026): a line in
`harness/trials.tsv` per (horizon, metric) with both axes' dispersion (HAR-08) and the three cost
levels (HAR-06), by a runner in `neonrain/baselines/` that calls the harness and reimplements none
of it, every golden byte-identical (HAR-14); for zero the IC is undefined with every date in
`dropped_flat`, and the portfolio as HAR-07 gives a constant: the tie-break's book, its after-cost
Sharpe the turnover floor (NR-F-10); (b) 12-1 momentum and (c) 1-month reversal, each a
glossary term and a stamped signal from the verified prices (HAR-12), through the same runner,
the same lines. Three tasks, (a) first; no number reaches `docs/RESULTS.md` before 3.3.

Task (a) is built (`neonrain/baselines/`, `scripts/baseline_run.py`; the zero baseline's lines are in
`harness/trials.tsv`). Fable's five rulings are in decision R-032: (1) folds are HAR-03's on the whole
calendar and a period selects test dates, a straddling fold being a cell in both; (2) the period is in the config
hash's `split` since trials.tsv has no period column; (3) `baselines` may not import `targets` (modules.json), so
the caller hands in the labels; (4) a constant score still gets a portfolio (ties order by ticker), so zero's Sharpe
is defined, not undefined as this item expected (reported as the harness computes it, NR-F-10); (5) the DSR's V is
taken from the Sharpe_10bps lines in the file (HAR-07, HAR-09), and a rerun of the same config marks no line: the
DSR is excepted from HAR-01's conflict rule. Task (b) is built (`neonrain/baselines/momentum.py`, glossary term
**momentum**, `scripts/baseline_run.py momentum`). Task (c) is built (`neonrain/baselines/reversal.py`, glossary term
**reversal**, `scripts/baseline_run.py reversal`; the prior 21-session return negated, stamped *t*, ranked with
`momentum.rank_scores`); all three tasks are done and the item awaits review.

### 3.2 LightGBM

Plan: ROADMAP 3.2. The hyperparameters are a decision in `theGhost.md` (take its id from
`scripts/next_id.py decision`) and sit in the config hash's `model.hyperparameters` (HAR-01).
LightGBM 4.7.0 is in `requirements.lock`: no dependency changes.
Check: the tree trains on the feature table's sixteen features, one model per grid cell, with a
hyperparameter set recorded once as a decision in `theGhost.md` and carried in the config hash
(HAR-01), no search; its lines in `harness/trials.tsv` as 3.1's, both periods apart; the lock
unchanged (LightGBM 4.7.0 is in it) and every golden byte-identical.

### 3.3 Baseline goldens and the first results table

Plan: ROADMAP 3.3. The fast loop has no data (AGT-01), so a baseline golden is held by its hash in
`index.json`, not recomputed; `scripts/goldens.py` keeps recomputing the synthetic ones.
Check: `harness/goldens/baseline_<name>.json` for each of the four, listed in `index.json` with
its hash and `changed_by` 3.3, held byte-identical by the fast loop with no data (AGT-01) and
rewritten only by its run under a decision (HAR-14); `docs/RESULTS.md`'s baseline table has a row
per (run, horizon, period, metric) and `test/test_results.py` is green with rows present (HAR-13:
a trials line, both dispersions, the three costs, the dropped counts in the golden, NR-F-03 and
NR-F-04 cited); the expectation in ROADMAP 3.3 is set against what came, and a miss is a finding (P-03).

### 3.4 Tithe pass 3

Plan: `docs/rules/tithe.md`.
Check: AGENT.md re-measured; every debrief given a verdict, the log wiped and "Last review"
moved; open questions in the journal (R-023); Opus's phase-boundary report to Ghost (R-030 (d)).

## Phase 4: the network

## Phase 5: news

## Phase 6: the news-augmented model and the ablations

## Phase 7: the forward test
