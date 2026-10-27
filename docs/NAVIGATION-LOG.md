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

Last review: 0b2227f (2026-10-26, a tithe, J-065: six debriefs, entries wiped)

## Entries

### 2026-10-27 J-065's four answers (Claude Sonnet)
- **Task:** F-09 in ROADMAP, the licence in the dataset row, line numbers in the journal INDEX, the open-question rule in done.md
- **Opened:** CLAUDE.md, docs/journal/J-061-070.md, docs/ROADMAP.md, docs/rules/done.md, scripts/checks/journal.py, test/test_journal.py, scripts/checks/metrics.py
- **Complaints:** none; J-065's Found and J-066 together said exactly what to do. docs/JOURNAL.md also describes the index's columns, which no row of the task named.
- **Suggestions:** have the journal-index row in CLAUDE.md or JOURNAL.md say where the column list is written (scripts/checks/journal.py HEADER and docs/JOURNAL.md), so a column change finds both.

### 2026-10-27 TODO 2.5, the feature table (Claude Sonnet)
- **Task:** the table as pure functions, a build script writing yearly parquet with an index, the hash recorded in the manifest
- **Opened:** CLAUDE.md, TODO.md, docs/ROADMAP.md, docs/DONE.md, docs/journal/INDEX.md, docs/journal/J-051-060.md, docs/journal/J-061-070.md, neonrain/universe/prices.py, neonrain/universe/membership.py, neonrain/universe/verified.py, neonrain/features/normalize.py, neonrain/features/common.py, scripts/fetch/artifacts.py, scripts/fetch/wiki.py, data/MANIFEST.md, docs/modules.json, docs/GLOSSARY.md, docs/rules/done.md
- **Complaints:** the task's check ("cached to the artifact store by content hash; a fetch rebuilds it") does not say whether the manifest records one hash or one for each file; I chose the index's hash as one dataset row (the wiki-prices form) and wrote why in MANIFEST.md. DONE.md was named in the task but is under docs/, and the first read of it failed at the repository root. The ruff rules ask for return annotations on test functions, which the older tests have and no document says.
- **Suggestions:** a line in the artifact-store section of MANIFEST.md saying how a multi-file artifact is recorded (this entry's choice), so the next one (a ledger snapshot, weights) follows it.
