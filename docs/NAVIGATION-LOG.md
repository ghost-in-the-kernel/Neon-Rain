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

### 2026-10-29 3.1 (c) reversal (Claude Sonnet)
- **Task:** 3.1 (c), the 1-month reversal baseline through the runner, its glossary term, its real run
- **Opened:** CLAUDE.md, TODO.md (3.1), docs/ROADMAP.md (§6), docs/journal/J-071-080.md (J-074), neonrain/baselines/{momentum,runner}.py, test/test_momentum.py, scripts/baseline_run.py, docs/HARNESS.md (HAR-02, HAR-12), neonrain/harness/market.py, docs/GLOSSARY.md, test/test_glossary.py, docs/modules.json, docs/rules/done.md, docs/NAVIGATION-LOG.md
- **Complaints:** the "A baseline" row named the folder `neonrain/baselines/`, which the routing metric counts as its files: adding `reversal.py` made the row six and the fast loop fail (test_metrics) with no pointer from the failure to the row; found by reading scripts/checks/metrics.py. The scratchpad is shared across sessions, so a stale `precommit.done` from an earlier session made my wait loop return at once.
- **Suggestions:** the "A baseline" row now names two files, not the folder. A note in docs/rules/done.md that adding a file to a folder a routing row names can push the row over five. Wait on a done file of a fresh name, or one that starts with the exit status.

### 2026-10-29 3.2 (a) the tree's fit path (Claude Sonnet)
- **Task:** 3.2 (a), the runner's per-cell fit, `tree.py`, a proposed hyperparameter set, one timed real fit
- **Opened:** CLAUDE.md, TODO.md (3.2), docs/ROADMAP.md (3.2), neonrain/baselines/{runner,record,momentum,zero}.py, scripts/baseline_run.py, neonrain/harness/{split,trials,synthetic}.py, neonrain/targets.py, docs/HARNESS.md (HAR-01, 05, 07, 12), docs/journal/J-071-080.md, theGhost.md (R-032), scripts/fetch/{artifacts,feature_table}.py, data/MANIFEST.md, docs/modules.json, docs/GLOSSARY.md, test/test_momentum.py, test/test_baselines.py
- **Complaints:** how to fetch the feature table is in three places (artifacts.py's docstring, MANIFEST's artifact-store section, feature_table.py), and none gives the loop that fetches every year from the index; I wrote one. The feature table's column set (sixteen features, each with a stamp) is stated only as "34 columns" in MANIFEST; the names are in the `feature_columns` of each `neonrain/features/` family. No routing row says what a model baseline (as against a signal) opens: the "A baseline" row names momentum.py, a signal, and runner.py.
- **Suggestions:** a line in the "A baseline" row or in 3.2's TODO text: a model baseline's fit is `runner.Fit`, the example is `tree.py`. A fetch-the-feature-table one-liner in MANIFEST. The run's peak memory (about 7 GB, 4.3 GB of it `prices.load`) belongs in docs/AGENT.md's environment section.

### 2026-10-29 3.2 (b) the tree entry of baseline_run.py (Claude Sonnet)
- **Task:** 3.2 (b), the wiring only: `scripts/baseline_run.py tree`, the progress log, tests
- **Opened:** CLAUDE.md, TODO.md (3.2), neonrain/baselines/{runner,tree}.py, scripts/baseline_run.py, scripts/fetch/{artifacts,feature_table}.py, neonrain/universe/{verified,prices,membership}.py, neonrain/features/table.py, neonrain/harness/market.py, docs/journal/J-071-080.md (J-077), docs/modules.json, scripts/checks/modules.py, pyproject.toml, test/test_tree.py, test/test_baselines.py, test/test_feature_table.py, docs/rules/done.md
- **Complaints:** nothing says which universe the feature table was built on: `feature_table.build` uses the adjusted prices where the baselines use `prices.for_membership` (raw), so the stored table has 141,655 cells the baselines' universe lacks; found only by joining the two. MOD-05 ("nothing but scripts/fetch reads the clock") is checked under neonrain/ only, so whether a log line's timestamp in scripts/baseline_run.py is allowed is a reading, not a rule. Which scripts are mutated (scripts/checks only; scripts/fetch and baseline_run.py are copied for the tests, not mutated) is in pyproject.toml's comments, not in the routing row for a script.
- **Suggestions:** in MANIFEST's `feature-table` row, one line on the universe it was built with; in the "A script that is not a document check" row, that scripts/fetch and scripts/baseline_run.py are tested but not mutated.

### 2026-10-29 gate time metrics back within target (Claude Sonnet)
- **Task:** bring the fast loop (< 40 s) and the full check (< 10 min) back within target, no test weakened
- **Opened:** CLAUDE.md, docs/AGENT.md, docs/MUTATION.md, theGhost.md (R-024, R-031), pyproject.toml, test/conftest.py, scripts/precommit.sh, test/test_baselines.py, test/test_baseline_run.py, test/test_feature_table.py, test/test_commit_script.py, scripts/checks/supply_chain.py, the mutmut package (runners/harness.py)
- **Complaints:** nothing says where a mutation run's minutes go: mutmut's stats time only a test's call, so a fixture-heavy test looks free and runs first; I found it by logging every mutant's tests from a temporary hook in conftest. The lead's figures of 7 s for `test_readability` and `test_modules` are the stats run under coverage tracing (0.3 s and 0.2 s in the loop). The scratchpad is shared across sessions and full of earlier sessions' files.
- **Suggestions:** MUTATION.md now says how to see per-mutant tests (the probe above, one `pytest_runtest_logreport` hook writing the mutant name and the test) and that stats durations exclude setup. A routing hint in the "surviving mutant, slower check" row: `test/conftest.py` holds the order and the thread knobs.


### 2026-10-29 the feature table rebuilt on the raw universe (Claude Sonnet)
- **Task:** fix `feature_table.build`'s universe, a test that fails on the old line, rebuild, new hash in MANIFEST
- **Opened:** CLAUDE.md, docs/rules/done.md, J-078 and J-068, scripts/fetch/feature_table.py, neonrain/universe/{prices,membership}.py, scripts/baseline_run.py, data/MANIFEST.md, test/test_feature_table.py, test/test_prices.py, docs/modules.json
- **Complaints:** nothing says that membership is meant to be called only through `prices.for_membership`; `scripts/probe/wiki_normalize.py` had the same defect and only a grep for `membership.universe` found it. The scratch location for a rebuild (outside both repositories) is in the script's docstring only.
- **Suggestions:** MANIFEST's `feature-table` row could say the universe it was built on; `membership.universe`'s docstring could point at `prices.universe`.

### 2026-10-29 portfolio.daily partitioned by date (Claude Sonnet)
- **Task:** make `portfolio.daily` cheaper (one partition by date, not a filter per open date), no number changed
- **Opened:** CLAUDE.md, docs/rules/done.md, docs/HARNESS.md (HAR-14), test/test_the_freeze.py, neonrain/harness/portfolio.py, docs/journal/J-071-080.md (J-078), docs/MUTATION.md
- **Complaints:** what HAR-14 asks of a harness change that moves no golden (nothing beyond `scripts/goldens.py` saying "identical") is found only by reading both HAR-14 and the freeze test; the routing row "The portfolio and its costs" does not say which goldens or freeze tests cover a portfolio change. A mutation survivor on an argument that cannot matter (`maintain_order`) is better removed than explained; MUTATION.md does not say so.
- **Suggestions:** in the "The portfolio and its costs" row, a clause: a speed change is shown by `scripts/goldens.py` and the slow tests of `test/test_the_freeze.py`. In MUTATION.md, a line: an argument whose mutant survives because it cannot matter is dropped from the code.
