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
