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

### 2026-10-28 3.1 (a) rulings (Claude Sonnet)
- **Task:** apply Fable's five rulings on 3.1 (a) (HARNESS.md, trials.py's DSR exception, record.py's order), then one repeat run
- **Opened:** CLAUDE.md, docs/rules/done.md, neonrain/baselines/{record,runner}.py, neonrain/harness/trials.py, docs/HARNESS.md (HAR-01, 03, 07, 09, 14), test/test_the_freeze.py, test/test_baselines.py, test/test_trials.py, docs/FINDINGS.md, TODO.md, docs/ROADMAP.md
- **Complaints:** the routing table has no row for "a ruled change to the frozen harness": HAR-14 says a decision, but which tests catch a change (goldens.py, test_the_freeze.py) was found by reading. The ROADMAP check text and TODO's check text are copies kept by hand, and nothing says so.
- **Suggestions:** in the "The goldens" row, a clause: a harness change that moves no golden is shown by `scripts/goldens.py` ("identical").

### 2026-10-28 3.1 (b) momentum (Claude Sonnet)
- **Task:** 3.1 (b), the 12-1 momentum baseline through the runner, its glossary term, its real run
- **Opened:** CLAUDE.md, TODO.md (3.1), neonrain/baselines/{zero,runner,record}.py, scripts/baseline_run.py, neonrain/universe/prices.py, neonrain/features/{returns,common}.py, neonrain/harness/{market,metrics,goldens}.py, docs/GLOSSARY.md, docs/modules.json, test/test_baselines.py, test/test_glossary.py, theGhost.md (R-032)
- **Complaints:** which range a score may take (rank fraction 0 to 1, 0.5 = predicts excess 0) is in no document; it was found by reading `metrics.predictions` and `goldens.edge_scores`. Whether a baseline's prices may be the cut frame (the script cuts it at the universe's first date) or the whole one is nowhere said; a lookback signal needs the whole.
- **Suggestions:** a sentence in the "A baseline" row or HARNESS.md: a score is read as P(up) with 0.5 the median, and a signal that looks back must be given the uncut prices.
