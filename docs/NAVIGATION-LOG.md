# Navigation log: what agents found hard to find

Each new task goes to a fresh Claude Sonnet agent (no context carried from an earlier task), and the
agent reviewing it (Claude Opus) pushes it. At the end of its task the agent debriefs here: one entry,
its complaints and suggestions about finding its way (routing rows, documents, names, rules that were
unclear), not about the task's code. Ghost's rule, 2026-10-23 (J-027).

**The review, at every tithe pass and every ten commits or so** (`docs/rules/tithe.md` step 4) (`scripts/precommit.sh` prints how many since the last):
read the entries for what agents converge on. With nothing actionable, wipe the entries and go on.
With something actionable, wipe the entries too, and review each item for validity first; act on the
valid ones (a routing row, a document, a name), and take any open question to a Claude Fable
instance. Record the review in the journal, then set the line below to the review's commit.

Last review: e85890e (2026-10-26, a tithe, J-057: ten debriefs, entries wiped)

## Entries

### 2026-10-26 Licence facts and decisions move to neon-rain-data's theGhost.md (Claude Sonnet)
- **Task:** a decision record for the data's licences in `neon-rain-data` (prefix D), R-016 (d) turned into a pointer, the manifest's licence cells shortened, J-059
- **Opened:** CLAUDE.md, neon-rain-data's CLAUDE.md and README.md, theGhost.md (header, R-016), docs/decisions.md, data/MANIFEST.md, docs/journal/J-041-050.md and J-051-060.md (J-040, J-042, J-048, J-058), docs/NAVIGATION-LOG.md, test/test_ghost.py, Ghost-Core docs/LINEAGE.md
- **Complaints:** No routing row for a data licence or for `neon-rain-data`'s own files; the first row ("a decision") sent me to theGhost.md, and the licence facts only turned up by grepping R-016 and J-040 to J-058. Finding a journal entry means grepping across the 10-entry files; the INDEX gives the file but not a line. Which prefixes are taken lives only in Ghost-Core's LINEAGE.md (read only), and Neon Rain's own non-R prefixes (J, NR-F, HAR, AGT, MOD, P) are scattered.
- **Suggestions:** A CLAUDE.md row "A dataset's licence" pointing at neon-rain-data's theGhost.md (D-001, D-002) and the manifest's License column; Ghost to decide, as CLAUDE.md is near its word limit.

### 2026-10-26 Volatility, the second price-derived family (Claude Sonnet)
- **Task:** TODO 2.3's second family, `neonrain/features/volatility.py`, its test, glossary term, entry points, a counts-only probe
- **Opened:** CLAUDE.md, TODO.md (2.3), `neonrain/features/returns.py`, `test/test_returns.py`, docs/journal/J-051-060.md (J-056), `scripts/probe/wiki_returns.py`, docs/GLOSSARY.md, docs/modules.json, docs/NAVIGATION-LOG.md
- **Complaints:** The feature row worked well; returns.py as the model made this quick. Not stated anywhere: whether one family may import another's helpers (I did, `from neonrain.features.returns import ...`; the module rules allow it, MOD-04 is about the ledger only), and where the shared helpers (`positioned`, `usable`, `OffCalendar`, `STAMP_SUFFIX`) should live once a third family needs them. No row for "a probe script" (the scripts row sends to scripts/checks, which does not fit a probe).
- **Suggestions:** A sentence in the feature row or `docs/modules.json` `features` naming whether a family may import `returns`; consider a `features/_common.py` at the third family.

### 2026-10-26 Volume ratios, the third price-derived family (Claude Sonnet)
- **Task:** TODO 2.3's third family, `neonrain/features/volume.py`, its test, glossary term, entry points, the helpers moved to `neonrain/features/common.py`, a counts-only probe
- **Opened:** CLAUDE.md, `neonrain/features/returns.py` and `volatility.py`, `test/test_volatility.py`, docs/journal/J-051-060.md (J-056, J-060), `neonrain/universe/prices.py`, docs/FINDINGS.md (NR-F-06), docs/GLOSSARY.md, docs/modules.json, docs/MUTATION.md, TODO.md, `scripts/probe/wiki_volatility.py`, docs/NAVIGATION-LOG.md
- **Complaints:** The feature row and the two models made this quick. Hard to find: which volume column the price frame offers and what it is adjusted for (only `prices.py`'s docstring says; nothing says whether WIKI's adjusted volume follows splits alone). The glossary already uses "baseline" for R-007's comparators, so the natural name for the prior window was taken; I used "prior mean". A probe run needs `PYTHONPATH=.` (the docstring's `python scripts/probe/...` fails with ModuleNotFoundError); the existing probes say the same.
- **Suggestions:** Put `PYTHONPATH=.` (or the venv's path) in the probe docstrings, or in the "Commands" line; a routing row or a sentence in the feature row naming `neonrain/features/common.py` as the shared helpers, once Ghost accepts the move.

### 2026-10-26 CLAUDE.md's reading moved into conditional files (R-029) (Claude Sonnet)
- **Task:** "Before calling work done" to `docs/rules/done.md`, the supply-chain rules split between `docs/rules/dependencies.md` and an inline "Always" section, a measurement row, the volume debrief's two routing fixes, R-029
- **Opened:** CLAUDE.md, `docs/rules/escalation.md`, `docs/SUPPLY-CHAIN.md`, `test/test_supply_chain.py`, `scripts/checks/metrics.py`, `scripts/checks/pointers.py`, `scripts/checks/modules.py`, docs/AGENT.md, docs/journal/J-051-060.md (J-057), docs/journal/J-061-070.md (J-061), theGhost.md (R-027, R-028), docs/NAVIGATION-LOG.md
- **Complaints:** The task brief named four places for AGT-03's limit, but the limit was not raised, so I could not tell whether they agree. J-057's "rules found only by running a loop" are not listed anywhere; I read three checks to word them. The metric's name-counting rule is only in `scripts/checks/metrics.py`.
- **Suggestions:** Nothing for the routing; `done.md` now holds the loop-only rules where an agent meets them.
