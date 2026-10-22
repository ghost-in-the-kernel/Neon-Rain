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
