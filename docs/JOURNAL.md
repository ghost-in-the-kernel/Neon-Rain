# Journal: every event in the work, as a record a researcher can count

One entry per event: a contradiction found, a decision taken, a failure caught or missed, a change
of direction, a measurement. Not a restatement of the commit log and not a status list and not the
design: the journal records *what happened while the work was done*. Fixed fields, the same as
Katana's and Suite Builder's, so entries can be counted across projects. Newest last. Written by
whoever was there, in the same commit as the event when possible; an agent writes its own entries.

Fields: **Who**, **Intent**, **Found**, **Options**, **Resolved**, **Touched**, **Caught by** (for a
failure), **Cost**, **Class** (`contradiction`, `ambiguity`, `failure-caught`, `failure-missed`,
`decision`, `measurement`, `direction`, `trial`, `deferred`).

---

### J-001 Founding
- **Who:** Ghost, Claude Fable.
- **Intent:** Found the project with the shape of Katana: decisions, roadmap, routing table, glossary,
  metrics, journal.
- **Found:** Ghost's starting design (every ticker as an input neuron; a Haiku agent scoring stories
  1–10 by ticker; horizons of 3 days, 1 week, 1 month, 3 months; cloud only, no CI, no local runs)
  and his method ("build a rigorous harness first, then the dumbest baseline, then add features one
  at a time").
- **Options:** Absolute price prediction vs cross-sectional direction and rank (took the latter,
  R-004). All-tickers-as-inputs vs pooled per-name training (took pooled, R-009). Live scorer vs a
  once-scored ledger (took the ledger, R-008). Java (Ghost's language) vs Python (proposed Python,
  R-001, for Ghost's word).
- **Resolved:** Fourteen decisions drafted; three left `proposed` for Ghost (R-001 toolchain, R-010
  artifact store, R-011 license).
- **Touched:** every founding document.
- **Class:** decision

### J-002 The ticker-holdout axis
- **Who:** Ghost, Claude Fable.
- **Intent:** Ghost, mid-founding: test on one stock, then another, and use the variance of accuracy
  to tell whether the model fit the data or learned an algorithm.
- **Found:** The variance idea is the only direct test of name-memorization and was missing from
  the plan. The single-stock part cannot stand (too few samples to train on; a held-out name's
  dates still share the market factor with trained names, so time leaks through it).
- **Options:** Replace the time split with a ticker split (refused: time is the primary leak);
  ignore (refused: the dispersion test is real); add as a second axis with dispersion reported
  beside every mean (taken).
- **Resolved:** R-014; the harness's grid is time × group; P-07 extended to require dispersion.
- **Touched:** R-014, R-005 (`See also`), ROADMAP §5, §6 phase 1.3 and 1.6, GLOSSARY (`group`,
  `dispersion`).
- **Class:** decision

### J-003 Python, and the audit it costs
- **Who:** Ghost, Claude Fable.
- **Intent:** Settle R-001.
- **Found:** Ghost chose Python and named its cost: he cannot audit it by hand as he can Java, so
  he will lean on testing.
- **Options:** Java after all (refused by Ghost); Python with ordinary tests (not enough: a test
  that cannot fail is not a check); Python with mutation-tested tests, readable-code rules, blind
  mirrors and hand-checkable ten-row examples (taken).
- **Resolved:** R-001 in force; R-015 added.
- **Touched:** R-001, R-015, CLAUDE.md (precommit now reports the mutation score), TODO 0.5.
- **Class:** decision

### J-004 Reachability
- **Who:** Claude Fable.
- **Intent:** ROADMAP 0.3: measure which hosts the workspace can reach before any fetch script is written.
- **Found:** Every price, news and dataset host refused by the proxy; PyPI and GitHub reachable;
  GitHub Releases, LFS uploads and REST writes refused for the session type; a plain git blob pushes.
  The `pip install` of a package was blocked by the session's own policy classifier on the first
  attempt; `pip download` worked, so PyPI itself is open.
- **Options:** Fetch from the workspace (impossible); Ghost supplies data through a data repository
  or the desktop bridge (taken as the proposal); a scheduled task elsewhere with network (parked for
  the news feed).
- **Resolved:** NR-F-01 written; R-016 proposed; R-010 superseded by it. A scratch branch
  `probe-plain` is left on GitHub because the proxy refuses branch deletion; Ghost deletes it.
- **Touched:** NR-F-01, R-010, R-016, `scripts/probe/reachability.py`.
- **Caught by:** the probe, by design of 0.3 (F-07).
- **Cost:** about twenty minutes.
- **Class:** measurement
