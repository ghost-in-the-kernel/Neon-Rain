# Done: the items completed, numbers kept from TODO.md

An item moves here from `TODO.md` when its check passes, keeping its roadmap number. The journal
(`docs/JOURNAL.md`) says what happened while it was done; this file says only that it is done.

## Phase 0: founding

### 0.1 Repository and documents — done 2026-10-22 (J-001)

`README.md`, `CLAUDE.md`, `theGhost.md` (R-001 to R-016), `docs/ROADMAP.md`, `GLOSSARY.md`,
`AGENT.md`, `JOURNAL.md`, `FINDINGS.md`, `HARNESS.md`, `LEDGER.md`, `GHOST-IN-THE-KERNEL.md`,
`SUPPLY-CHAIN.md`, `RESULTS.md`, `MUTATION.md`, `DONE.md`, `TODO.md`, `HANDOFF.md`,
`docs/modules.json`, `.gitignore`, `data/MANIFEST.md`, `harness/trials.tsv`, `requirements.in`.
Check: `git log` shows Ghost as author; the files exist.

### 0.2 Ghost's founding decisions — done 2026-10-23 (J-036, J-037)

R-001 (Python), R-016 (data and artifacts through two private GitHub repositories) and R-011
(protective) in force; R-010 superseded. Ghost made the repository private and created
`ghost-in-the-kernel/neon-rain-data` and `neon-rain-artifacts`, both private and empty.
Check: `test/test_ghost.py` passes and no decision is `proposed`. ✓

### 0.3 Reachability — done 2026-10-22 (J-004, NR-F-01)

`scripts/probe/reachability.py` run from the workspace. Every market-data and news host refused by
the proxy; PyPI and GitHub (git, read-only REST) open; GitHub Releases, Git LFS uploads and REST
writes refused for this session type; a plain 1 MB git blob pushes. Produced NR-F-01 and R-016;
superseded R-010.
Check: `docs/FINDINGS.md` NR-F-01 lists every candidate as reachable or refused. ✓

### 0.4 Artifact store and data repository — done 2026-10-23 (J-038)

`scripts/fetch/artifacts.py`: `put FILE` stores a file in the private `neon-rain-artifacts` under
its SHA-256 (`<hash[:2]>/<hash>` on `main`, committed as Ghost, pushed), `get HASH DEST` copies it
out and refuses bytes that do not hash to the name; the clone is a cache outside this repository
(`data/MANIFEST.md`). 15 tests against a local bare repository. Built by a fresh Claude Sonnet
agent under J-027. Check: a 1 MB file round-trips by content hash through the real artifacts
repository (9001d514…, one commit; a second put of the same bytes, none). ✓

### 0.5 The doc tests and `precommit.sh` — done 2026-10-22 (J-010, J-011)

`requirements.lock` (R-017, R-018); `pyproject.toml` (ruff for R-015b's type hints and bare excepts,
pytest, mutmut); `scripts/checks/` and a test for each of theGhost.md, the glossary, TODO.md, the
module rules, the manifest, the supply chain, HARNESS.md, RESULTS.md, AGENT.md's metrics, R-015(b)'s
readability and the survivor rule; `scripts/metrics.py`, `scripts/survivors.py`, `scripts/precommit.sh`.
Check: every doc test passes (137, and `test_harness_doc`'s code-reference test a strict xfail until
`neonrain/harness/` exists); `test_ghost` failed on a conflicting in-force pair planted in the real
file and passed once one side was superseded; `precommit.sh` refused 139 unexplained survivors, then
passed with 1,096 of 1,099 killed and 3 explained in `docs/MUTATION.md`; the readability lint is
configured. ✓

#### What 0.5's checks hold, and the change that turns each red (moved from HANDOFF.md, J-020)

| Test | Holds | Must turn red when |
| --- | --- | --- |
| `test_ghost.py` | `theGhost.md`: ids `R-nnn` unique and sequential from 001; every entry has Decision, Why, Held by, Source, Status, See also, subject; status is one of the five words; a `superseded by R-nnn` names an entry that exists and that names it back; no two `in force` entries share a `subject:` while carrying `conflicts-with:` | an id is duplicated; a supersession is one-sided; two in-force entries conflict on a subject |
| `test_glossary.py` | every backticked alias in `docs/GLOSSARY.md` appears in no other document under `docs/` or the root | a document uses an enforced alias (try writing `timeframe` into ROADMAP.md, outside backticks: a backticked word is a mention) |
| `test_todo.py` | `TODO.md` headings in numeric order; the first open item has a `Check:` line; no item appears in both `TODO.md` and `docs/DONE.md` | an item is out of order, or is in both files |
| `test_modules.py` | every `import` under `neonrain/` is allowed by `docs/modules.json`; MOD-01 (only `scorer` imports `anthropic`), MOD-02 (`harness` imports neither `models` nor `baselines`), MOD-03 (no broker client anywhere), MOD-04, MOD-05 | a planted `import anthropic` in `neonrain/features/` |
| `test_manifest.py` | every row of `data/MANIFEST.md` has a source, a license, a supplier and a hash; an empty table passes | a row with a blank license |
| `test_supply_chain.py` | no file under `.github/workflows/`; no `.claude/settings.json` hooks; no git hooks; every import in `neonrain/` resolves to something in `requirements.lock` or the standard library; none of the named worm artefacts exist | a planted empty workflow file |
| `test_harness_doc.py` | every `HAR-nn` in `docs/HARNESS.md` is referenced by a docstring or comment in `neonrain/harness/`, and the reverse; numbers unique and sequential | an invariant exists in the document and nowhere in the code (it will fail until phase 1, so **write it last and let it fail for now** — note that in the journal rather than weakening it) |
| `test_results.py` | every row of `docs/RESULTS.md` has a line in `harness/trials.tsv` with a matching `config_hash`, a dispersion on both axes, and findings cited by number; empty tables pass | a row with no trials line |
| `test_metrics.py` | `docs/AGENT.md`'s table against what `scripts/metrics.py` measures; a metric within target may move freely, past it may not get worse | a measured value worse than the recorded one |

### 0.6 Tithe pass 0 — done 2026-10-22 (J-012)

The fresh-agent trial, in a fresh cloud session on `main` at 77ff4e2. Reads `docs/modules.json` in its
second tool call (its eighth file); changes nothing; proposes `neonrain/harness/cost.py` under
HAR-06, which is right. Contaminated: it read the trial's own description in HANDOFF.md (R-020,
proposed). What it showed is fixed or waiting at 1.4 (J-012). AGENT.md re-measured.
Check: the trial opens `CLAUDE.md` first (loaded by the tool, so not evidence), `docs/modules.json`
within three reads (by tool call yes, by file no), and changes nothing (yes). ✓ with J-012's caveats.

## Phase 1: the harness

### 1.1 Synthetic market — done 2026-10-22 (J-013)

`neonrain/harness/synthetic.py` to HAR-10, whose model was made exact first; `test/test_synthetic.py`.
Check: the generator is seeded and deterministic (the same config gives byte-identical frames, another
seed another market); the planted edge is recovered by a least-squares line at ρ = 0.1 and 0.3
within 0.015 (five standard errors) and nothing at ρ = 0. One return is rebuilt from HAR-10's text
alone, and with ρ = 1 every return equals σ_x times the previous edge (R-015d). 146 of 146 mutants
killed. ✓

### 1.2 Targets — done 2026-10-22 (J-014)

`neonrain/targets.py` to R-004 and HAR-02, which was made exact first (ties, the calendar's end,
`min_tickers`); NR-F-02 written before any result. `test/test_targets.py`.
Check: the hand-built ten-day, three-ticker series gives the hand-computed forward returns, excess
returns, directions, ranks and the three dropped counts at horizons 3, 5 and 9. On the synthetic
market every label is well formed at the four horizons, and the planted edge's rank correlation
thins as HAR-10 predicts (about ρ/√h at 3 and 21 days). 278 of 278 mutants killed. ✓

### 1.3 Splits — done 2026-10-22 (J-015)

`neonrain/harness/split.py` to R-005, R-014 and HAR-03 to HAR-05, made exact first (the first fold at
the longest horizon, whole test spans only, the group hash with a separator, no empty group);
`test/test_split.py`.
Check: no training label's horizon window overlaps any test date, at all four horizons and every
fold on a 1,300-day synthetic market, checked by brute force from the calendar independently of
`split.py`; every ticker is in exactly one group; the grid is reproducible from a seed (and another
seed gives another). Folds and purging by hand. 178 of 178 mutants killed. ✓

### 1.4 Cost model and metrics — done 2026-10-23 (J-016 to J-018)

In three parts: 1.4a the portfolio after costs (R-021), 1.4b HAR-07's metrics, 1.4c HAR-08's
dispersion, the mirror and the noise band. `neonrain/harness/portfolio.py`, `metrics.py`,
`dispersion.py`; `test/mirror_har07.py`, written blind by another agent from HAR-06 and HAR-07's
text alone, standard library only, agreeing with the code to 1e-12 on every metric, at all three
cost levels, through 30+ held delistings; three deliberate breaks of the code each turn it red.
Check: a zero-edge strategy reports a deflated Sharpe inside its noise band across 100 seeds: 3 of
100 at or above 0.95 before costs (band: at most 12), mean 0.471 (0.4 to 0.6); after 10 bps, 0 and
0.012. With an edge of ρ = 0.1 all 100 are above 0.95, so the band check fails as it must. ✓

### 1.5 The trials file — done 2026-10-23 (J-026)

`neonrain/harness/trials.py`: HAR-09's header (which `scripts/checks/results.py` now imports), the
append, and HAR-01's config hash; HAR-01 and HAR-09 made exact first. Built by a Claude Sonnet agent
under R-022, reviewed by Claude Opus. `test/test_trials.py` writes only to temporary files.
Check: every harness run appends to `harness/trials.tsv` through `append_trial` (a missing file
gets its header; another header, or a last line with no line break, is refused); `docs/RESULTS.md`'s
test refuses a number with no line (`test/test_results.py`, as before). The real `harness/trials.tsv`
is unchanged. ✓

### 1.6 Adversarial tests — done 2026-10-23 (J-030, J-031)

`test/test_harness_adversarial.py`, eleven tests, by two fresh Claude Sonnet agents under J-027,
reviewed by Claude Opus: the planted leak (refused by the stamp check; with a lying stamp, caught
by the leak check), survivorship (a universe without its delisted names inflates), a label reaching
the embargo (none on the purged grid, at every horizon), a short embargo refused, the name memorizer
(R-014's signature), HAR-12's label shuffle (every metric at chance; red when the shuffle never
reaches the metrics, or reaches only direction), and the mirror (`test/test_mirror.py`, 1.4c).
Check: every test red on its broken input, green on the honest one: seen by the agents on scratch
copies of the harness, and by the reviewer in the repository (purge removed, stamp refusal off,
`fits_names` never raised, DSR forced to 0.99, IC made absolute): each turned its test red. ✓

### 1.7 Freeze — done 2026-10-23 (J-032)

`harness/goldens/`: five goldens of HAR-14's synthetic market (labels, splits, cells, dispersion,
the config hash; 52 KB, floats to 12 significant digits) and `index.json` (each file's SHA-256, who
changed it, the harness version). `neonrain/harness/goldens.py`, `scripts/goldens.py` (check, or
`--write`, refused for a change without a decision in force). `trials.HARNESS_VERSION` is "1".
Built by a fresh Claude Sonnet agent under J-027, finished by Claude Opus.
Check: the goldens are written from the synthetic market; a harness change is caught (the default
cost moved by 0.5 bp: three goldens named with their first differing line, and `--write` refused
without a decision); `test_harness_doc`'s invariants are held by the code now that this item is
done. ✓

### 1.8 Tithe pass 1 — done 2026-10-23 (J-033)

A fresh Claude Sonnet agent re-measured `docs/AGENT.md` (no armed metric regressed; the full check
9.53 min of its 10), fixed what it could not find (a tithe row, AGENT.md's re-measuring, MUTATION.md's scope, HANDOFF's stale phase-1 lines) and
gave each of the phase's debriefs a verdict. The separate fresh-agent trial ran once more and
drifted into phase-2 work on a follow-up; Ghost retired it (R-023). `docs/rules/tithe.md` is the
one procedure, reviewed by Claude Fable. Check: AGENT.md re-measured; every debrief given a
verdict, the log wiped and "Last review" moved; open questions in the journal. ✓

### 2.1 Universe — done 2026-10-24 (J-039, J-043; closed in TODO J-066)

(a) The NYSE calendar by rule (`neonrain/universe/calendar.py`, J-039). (b) WIKI as yearly parquet in
`neon-rain-data` and the point-in-time universe of 1,000 names by trailing median dollar volume
(`neonrain/universe/membership.py`, J-043); the survivorship gap is NR-F-03 (no ticker leaves before
2014-04-01), with NR-F-04 to NR-F-08 beside it. The item stayed open in TODO by oversight until J-066.
Check: (a) hand-checked sessions and closures ✓; (b) every ticker has dates in and out, the gap a finding ✓.

### 2.2 Daily prices — done 2026-10-25 (J-053)

`neonrain/universe/verified.py` checks `index.tsv` against the manifest and every year against its
index line before any byte is returned; `neonrain/universe/prices.py` loads the harness's price frame
from WIKI's adjusted columns (a total-return close; raw close and volume kept for dollar volume).
On the 2017-11-07 sample: 20 years verified, 11,965,009 rows on 4,996 sessions, 3,194 tickers; 165
rows on 120 dates off the calendar, refused by `check_market`, kept aside in `Loaded.off_calendar`
(NR-F-08); no session without rows; NR-F-05's tickers kept whole. Built by a fresh Claude Sonnet
agent under J-027. Check: ten or more years of OHLCV from neon-rain-data by script, manifested; every
price date a session or a finding. ✓ (No result is reported: WIKI's licence is unverified.)

### 2.3 Price-derived features — done 2026-10-26 (J-056, J-060, J-061, J-063)

Four families in `neonrain/features/`, sharing `common.py`, one fresh Claude Sonnet agent each under
J-027: returns (`ret_3`, `ret_5`, `ret_21`, `ret_63`), volatility (`vol_5`, `vol_21`, `vol_63`), volume
ratios (`volr_5`, `volr_21`, `volr_63`), and the indicators (`rsi_14`, `macd`, `macd_hist`, `mar_5`,
`mar_21`, `mar_63`; the textbook settings, every one a finite window of whole sessions ending at t).
Each feature stamped t (HAR-12), null across any gap, never infinite; reused tickers kept whole
(NR-F-05). Check: each family has a glossary term and a pure function from prices with a unit test
against a hand-computed window. ✓

### 2.4 Cross-sectional normalization — done 2026-10-26 (J-064)

`neonrain/features/normalize.py`: each feature as a centred rank within the day's universe,
`(rank - 1) / (n - 1) - 0.5`, ties averaged, nulls left out, null below 20 names (HAR-02's minimum).
The two questions J-056 left open, answered: a family's frame keeps the price frame's cells; the
normalized frame has exactly the universe's cells, and a name outside the universe on a date has no
row and no part in that date's ranks. Applying it to every family and caching the table is 2.5's.
Built by a fresh Claude Sonnet agent under J-027. Check: per day, each feature a rank within the
universe; no feature carries the market level (a day's mean is 0). ✓

### 2.5 The feature table — done 2026-10-27 (J-068)

`neonrain/features/table.py` joins the four families, each normalized within the universe (2.4): one row
per universe cell, 34 columns in a fixed order (keys, then 16 features each with its stamp). Built from
the verified prices by `scripts/fetch/feature_table.py` into 20 yearly parquet files and an index
(158 MB in all), the same bytes on every build with polars 2.0.0 (the version is written into each file's
footer, so it is recorded beside the hash). Its row in `data/MANIFEST.md`: index sha256 f3c9e950…d325.
Built by a fresh Claude Sonnet agent under R-030. Check: cached to the artifact store by content hash;
a fetch rebuilds it byte for byte: the reviewer rebuilt it (same hash), stored all 21 files in
`neon-rain-artifacts`, fetched them into a fresh clone, and every file compared identical. ✓

### 2.6 Tithe pass 2 — done 2026-10-27 (J-069)

The navigation log reviewed (two debriefs) and phase 2's routing measured across J-039 to J-068; four
document fixes (TODO's header on the line-start `Check:`, `done.md`'s rule on test annotations, the
journal index's columns named where they are written, the manifest's rule for a multi-file artifact).
Fast loop 22.9 s, full check 4.8 min, on a quiet machine. By a fresh Claude Sonnet agent under
`docs/rules/tithe.md`. Check: AGENT.md re-measured; every debrief given a verdict, the log wiped and
"Last review" moved; open questions in the journal. ✓ Phase 2 is done.

## Phase 3: baselines

### 3.1 Zero, momentum, reversal — done 2026-10-29 (J-071 to J-076)

The runner (`neonrain/baselines/runner.py`, `record.py`) calls the frozen harness and reimplements none of it;
zero (0.5 for every cell), 12-1 momentum and 1-month reversal, each a glossary term and a stamped signal from the
verified prices, run on WIKI with 56 lines each in `harness/trials.tsv`, both periods apart (R-026). Fable's
rulings in R-032 (results by period, the DSR outside the conflict rule, V defined) and NR-F-10 (zero's
alphabetical book). Built by fresh Claude Sonnet agents under R-030. Check: a line per (period, horizon, metric)
with both dispersions and the three costs; zero's IC undefined with every date in `dropped_flat` and its portfolio
the tie-break's book (NR-F-10); every golden byte-identical. ✓

### 3.2 LightGBM — done 2026-10-30 (J-077 to J-082)

The runner's per-cell fit (one model per horizon, fold and held-out group, HAR-05) and `neonrain/baselines/tree.py`
with one fixed set chosen blind (R-034); the feature table rebuilt on the raw-ranked universe the baselines use
(J-079); the run made resumable by horizon (J-081) and run on WIKI in four pieces (J-082). Check: sixteen
features, one model per grid cell, the set recorded once and carried in the config hash, no search; 56 lines as
3.1's, both periods apart; the lock unchanged; every golden byte-identical. ✓

### 3.3 Baseline goldens and the first results table — done 2026-10-30 (J-083)

`harness/goldens/baseline_{zero,momentum,reversal,tree}.json`, each a baseline's latest real-data run per period
read from `harness/trials.tsv`, held by hash (R-036); `docs/RESULTS.md`'s baseline table (216 rows) written from the
goldens and held to them; NR-F-11, the expectation of ROADMAP 3.3 set against what came. Built by a fresh Claude
Sonnet agent under R-030. Check: the four goldens listed in `index.json` with `changed_by` 3.3 and held
byte-identical with no data; the table's rows each carry a trials line, both dispersions, the three costs and
NR-F-03 or NR-F-04; `test/test_results.py` green with rows present; the expectation set against the results, its
miss a finding. ✓ Open for phase 4: its results table needs the Model column (`scripts/checks/results.py` pairs a
model's two periods by it).

### 3.4 Tithe pass 3 — done 2026-10-30 (J-084)

Twelve debriefs given verdicts and phase 3's routing measured; document fixes only (two routing rows, the
glossary's universe, the feature table's manifest line, MUTATION.md, done.md's trap (h)). Fast loop 31.96 s, full
check 8.25 min. By a fresh Claude Sonnet agent under `docs/rules/tithe.md`. Check: AGENT.md re-measured; every
debrief given a verdict, the log wiped and "Last review" moved; open questions in the journal; Opus's
phase-boundary report to Ghost. ✓ Phase 3 is done.
