# Decisions, one line each

Written by `python3 -I scripts/decisions_index.py` from `theGhost.md`; do not edit here. Search `### R-012` in theGhost.md for the entry.

| Id | Decision | Status | subject |
| --- | --- | --- | --- |
| R-001 | Python 3.12, PyTorch, and the scientific stack | in force | toolchain |
| R-002 | The harness before the model, and the harness is frozen before the first model trains | in force | method |
| R-003 | Cloud only, no CI, no local runs, for the foreseeable future | in force | environment |
| R-004 | Four horizons, cross-sectional, direction and rank, never price | in force | target |
| R-005 | Walk-forward only, purged and embargoed, every trial counted | in force | method |
| R-006 | Data is regenerated, never committed; its provenance is | in force | data |
| R-007 | Baselines first, and the tree model is a baseline the network must beat | in force | method |
| R-008 | News is scored once by a pinned Haiku, into an append-only ledger, point-in-time | in force | news |
| R-009 | One network until the tabular trunk is proven; its shape is a decision, not a search | in force | model |
| R-010 | Artifacts (weights, ledger snapshots, feature caches) live in an artifact store, not git | superseded by R-016 | environment |
| R-011 | Licensing and publication | in force | license |
| R-012 | The navigation tithe: one commit in eight, one pass per phase | in force | environment |
| R-013 | Nothing here is investment advice, and nothing trades real money without a separate decision | in force | scope |
| R-014 | Held-out ticker groups are the second evaluation axis; dispersion is reported with the mean | in force | method |
| R-015 | Tests are the audit: mutation-tested, readable Python, and the mirror written blind | in force | method |
| R-016 | Data and artifacts live in two private GitHub repositories as plain git blobs | in force | environment |
| R-017 | The lock is compiled by `uv pip compile`; `pip` installs it | in force | toolchain |
| R-018 | A dependency enters the lock in the phase that first imports it, and no version younger than seven days | in force | toolchain |
| R-019 | The largest source file and docs per source line are recorded at tithe passes, not on every commit | in force | agent environment |
| R-020 | A trial's task and pass condition stay out of the repository until it has run | superseded by R-023 | agent environment |
| R-021 | Costs are charged on every trade that could be charged, never netted | in force | method |
| R-022 | A Claude Sonnet agent makes one attempt at a hard code fix, then escalates to Claude Opus | in force | agent environment |
| R-023 | A tithe pass scores the phase's debriefs; the fresh-agent trial is retired | in force | agent environment |
| R-024 | The metric targets re-based after phase 1: source lines, docs per source, the full check | in force | agent environment |
| R-025 | The network lives in this repository and can be lifted out, one way | in force | model |
| R-026 | WIKI's sample ends 2017-11-07; its survivor-only years are reported apart and the bias measured | in force | data |
| R-027 | baselines and training may import universe; CLAUDE.md may grow to 1,400 words | in force | agent environment |
| R-028 | Four of Ghost-Core's tools adopted; Ghost-Core is read only | in force | agent environment |
| R-029 | CLAUDE.md's reading goes into conditional files; always-on rules stay inline | in force | agent environment |
| R-030 | Autonomous development by the roadmap: an escalation ladder, and human items moved back | in force | agent environment |
| R-031 | The fast loop's target re-based to 40 s | in force | agent environment |
