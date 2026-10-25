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

Last review: e722195 (2026-10-24, a tithe, J-045: five debriefs, entries wiped)

## Entries
### 2026-10-25 R-026 (c) survivorship bias probe (Claude Sonnet)
- **Task:** R-026 (c): measure the survivor-only flattery on the synthetic market, write it as NR-F-09
- **Opened:** CLAUDE.md, theGhost.md (R-026), docs/FINDINGS.md, neonrain/harness/synthetic.py, test/test_harness_adversarial.py, neonrain/harness/goldens.py, dispersion.py, portfolio.py, pyproject.toml, scripts/precommit.sh
- **Complaints:** The CLAUDE.md table has no row for a measuring script that runs the harness (only for fetch/probe scripts that read data), so I found by search that goldens.cell_numbers is the one place a cell's metrics are assembled and is not reusable for a single cost level; the Fast-loop time of the first design (about 4 minutes a seed) was only discovered by running it. Nothing says where a shared "survivors-only market" helper belongs when a test file holds the construction (I copied it and cited it).
- **Suggestions:** A row "A measurement through the frozen harness" pointing at goldens.py (cell_numbers, metric_values) and scripts/probe/survivorship.py as the example, with the budget note that one seed of 4 horizons by 4 scorers by 2 markets is 30 to 90 seconds on one core. A neonrain-side helper for the cell grid would end the copy, but that is a change under harness/ and waits on Ghost.

### 2026-10-25 R-028 (1) the tithe guard (Claude Sonnet)
- **Task:** R-028 (1): scripts/commit.sh, adapted from Ghost-Core, refusing any commit but `tithe:` while a tithe is due
- **Opened:** CLAUDE.md, theGhost.md (R-028, R-012), docs/rules/tithe.md, /home/user/ghost-core/scripts/commit.sh, scripts/precommit.sh, pyproject.toml, scripts/checks/supply_chain.py, test/conftest.py, docs/NAVIGATION-LOG.md
- **Complaints:** R-012 says "every eighth commit" without saying whether the count starts at the tithe or after it, so the threshold (seven, then the tithe) is my reading. No routing row for a script under scripts/ that is not a document check, so I had to read pyproject.toml to learn mutmut's `also_copy` needs any file a test reaches. Readability's ban on `*args` was found only by running the fast loop.
- **Suggestions:** A row "A script that makes or guards a commit" pointing at scripts/commit.sh. A line in the CLAUDE.md Commands or MUTATION notes that a new script a test calls must be added to `also_copy`.

### 2026-10-25 R-028 (2) the decisions index and the next-id script (Claude Sonnet)
- **Task:** R-028 (2): docs/decisions.md generated from theGhost.md and checked; scripts/next_id.py fetching main first
- **Opened:** CLAUDE.md, theGhost.md (R-028), scripts/checks/ghost.py, scripts/commit_guard.py, pyproject.toml, docs/AGENT.md (AGT-05), /home/user/ghost-core/scripts/decisions_index.py, next_id.py, docs/decisions.md, test/conftest.py
- **Complaints:** No routing row says where pure logic of a script goes; I chose scripts/checks/ (mutation-tested) with a thin CLI in scripts/, and learned only from commit_guard.py's docstring that scripts/ is the other option. The `*args` ban in readability.py was again found only by the fast loop (the commit-guard debrief said the same).
- **Suggestions:** A row "A script that is not a document check" saying: logic in scripts/checks/ (mutated), the CLI thin, and the CLI added to `also_copy`. A line in readability's docstring is not enough; CLAUDE.md's Commands could name the `*args` ban.

### 2026-10-25 R-028 (3) the escalation register (Claude Sonnet)
- **Task:** R-028 (3): docs/ESCALATIONS.md by kind, a check (scripts/checks/escalations.py) and its test, three of a kind to Ghost
- **Opened:** CLAUDE.md, theGhost.md (R-028), docs/rules/escalation.md, docs/rules/conflict.md, docs/JOURNAL.md (J-019, J-023, J-032), docs/HANDOFF.md, scripts/checks/tables.py, scripts/checks/decisions.py, test/test_decisions.py, pyproject.toml, /home/user/ghost-core/docs/ESCALATIONS.md, registers.py and its test
- **Complaints:** No routing row for a new document check, so I copied the shape of decisions.py and navigation.py by search; the decision to cite for a new rule is unclear when theGhost.md may not be touched (I cited R-028 (3) for the three-count, as no R-number exists for it). The first precommit run refused at an unexplained survivor in untouched `scripts/checks/modules.py` (`x_file_problems__mutmut_31`), which a second run did not show: flaky, not mine, nothing records it.
- **Suggestions:** A row "A document check (a register, a table)" pointing at scripts/checks/tables.py, a model check and its test. Ghost may want a decision of its own for the register's three-count (R-022 or R-028 would then cite it). Look into that flaky survivor.

### 2026-10-25 R-028 (4) the journal split into numbered files (Claude Sonnet)
- **Task:** R-028 (4): docs/JOURNAL.md's entries into docs/journal/J-nnn-mmm.md, ten ids to a file, a generated INDEX.md, every journal check reading the files
- **Opened:** CLAUDE.md, docs/decisions.md (R-028), docs/rules/tithe.md, docs/JOURNAL.md, scripts/checks/journal.py, test/test_journal.py, scripts/checks/next_id.py, test/test_next_id.py, scripts/checks/escalations.py, scripts/checks/metrics.py, scripts/decisions_index.py, scripts/checks/decisions.py, pyproject.toml, /home/user/ghost-core/scripts/journal_index.py
- **Complaints:** The task's "every check that reads the journal" list was found by grep (`JOURNAL`, `journal`); no document says which checks read which record, and escalations.py's "J-number check" turned out to read no journal at all (a regex on the cell), so nothing there changed. Mutmut's survivors on new code (an equivalent-looking `int(i[2:])` against `[3:]`, which differ only from J-100) were found only by the full precommit, eight minutes in.
- **Suggestions:** A line in the "Writing down what happened" row's contract or docs/JOURNAL.md saying which checks read the entries (journal.py, next_id.py). For new code with an id slice or a `default=`, try `.venv/bin/mutmut run <module>` before the full precommit.

### 2026-10-25 TODO 2.2 daily prices (Claude Sonnet)
- **Task:** TODO 2.2: the price frame from WIKI's yearly parquet, verified before any read; NR-F-08 and NR-F-05 recorded
- **Opened:** CLAUDE.md, TODO.md (2.2, phase 2), docs/modules.json, scripts/fetch/wiki.py, neonrain/universe/membership.py, periods.py, calendar.py, neonrain/harness/market.py, docs/HARNESS.md (first section), docs/FINDINGS.md, test/test_wiki.py, test/test_membership.py, data/MANIFEST.md, pyproject.toml
- **Complaints:** No routing row for "a loader of a dataset" or "a hash check any loader shares"; I placed both in `universe` (the only leaf the plan names for the price frame, and `features` may import it) by reading modules.json's purposes. `membership` reads `close` and `volume` as raw while the harness's `close` is adjusted, a clash only visible by reading both; I added `for_membership` rather than edit membership. `manifest_hash` now exists in both `scripts/fetch/wiki.py` and `neonrain/universe/verified.py` because a script cannot be imported by `neonrain/` and I did not touch the fetch script. Nothing says whether a new real-data check belongs in `test/` or `scripts/probe/`; I tried a skipping test first, found it cost 7 s of the fast loop (which reads no data), and kept only the probe. The precommit ran past the 10-minute tool limit, so it had to go to the background.
- **Suggestions:** A CLAUDE.md row "A loader of a dataset in the data repository" pointing at `neonrain/universe/verified.py` and `prices.py`. One home for the manifest-row parser (wiki.py could import it once `scripts/` may import `neonrain`). A line in the Commands section that `scripts/precommit.sh` takes longer than a foreground tool call allows.
