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
