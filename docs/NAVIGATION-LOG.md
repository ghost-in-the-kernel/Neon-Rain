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

Last review: 95b090d (2026-10-27, tithe pass 2, J-069: two debriefs and phase 2's routing, entries wiped)

## Entries

### 2026-10-27 3.1 a (Claude Sonnet)
- **Task:** 3.1 (a), the runner and the zero baseline
- **Opened:** CLAUDE.md, TODO.md (3.1), docs/ROADMAP.md (§6), docs/HARNESS.md, neonrain/harness/goldens.py, neonrain/harness/{split,trials,portfolio,metrics}.py, docs/modules.json, theGhost.md (R-026), scripts/checks/results.py
- **Complaints:** the "A baseline" row points at `neonrain/baselines/` and `harness/goldens/` and nothing else, so the three things this task needed were found by reading: that `baselines` may not import `targets` (docs/modules.json only), that trials.tsv has no period column (found in scripts/checks/results.py's comment that one hash names one period), and that HARNESS.md does not say how folds fall within a period. The moving-clock rule (MOD-05) for the run date also took a search.
- **Suggestions:** a line in the "A baseline" row naming docs/modules.json (`baselines` imports) and scripts/checks/results.py (how a period shows in trials.tsv); HARNESS.md a sentence on periods.
