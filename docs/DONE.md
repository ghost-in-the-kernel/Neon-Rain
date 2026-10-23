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

### 0.3 Reachability — done 2026-10-22 (J-004, NR-F-01)

`scripts/probe/reachability.py` run from the workspace. Every market-data and news host refused by
the proxy; PyPI and GitHub (git, read-only REST) open; GitHub Releases, Git LFS uploads and REST
writes refused for this session type; a plain 1 MB git blob pushes. Produced NR-F-01 and R-016;
superseded R-010.
Check: `docs/FINDINGS.md` NR-F-01 lists every candidate as reachable or refused. ✓

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
