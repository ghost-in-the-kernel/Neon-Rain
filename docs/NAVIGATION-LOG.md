# Navigation log: what agents found hard to find

Each new task goes to a fresh Claude Sonnet agent (no context carried from an earlier task), and the
agent reviewing it (Claude Opus) pushes it. At the end of its task the agent debriefs here: one entry,
its complaints and suggestions about finding its way (routing rows, documents, names, rules that were
unclear), not about the task's code. Ghost's rule, 2026-10-23 (J-027).

**The review, every ten commits or so** (`scripts/precommit.sh` prints how many since the last):
read the entries for what agents converge on. With nothing actionable, wipe the entries and go on.
With something actionable, wipe the entries too, and review each item for validity first; act on the
valid ones (a routing row, a document, a name), and take any open question to a Claude Fable
instance. Record the review in the journal, then set the line below to the review's commit.

Last review: 10fd67e (2026-10-23, the log begins)

## Entries


### 2026-10-23, neonrain/harness/market.py: the Market type, the frame layouts, HAR-12's stamp refusal
- **Task:** Create `neonrain/harness/market.py` (Market type moved out of `synthetic.py`, frame layouts, a callable HAR-12 stamp refusal); make `docs/HARNESS.md` precise where it was not.
- **Opened:** CLAUDE.md, docs/modules.json, docs/HARNESS.md, neonrain/harness/synthetic.py, docs/NAVIGATION-LOG.md, docs/HANDOFF.md, TODO.md (1.6), scripts/checks/harness_doc.py, test/test_harness_doc.py, scripts/checks/modules.py, scripts/precommit.sh, scripts/checks/readability.py, docs/ROADMAP.md (1.6), docs/LEDGER.md (NL-04), theGhost.md (R-008), docs/GLOSSARY.md, docs/rules/escalation.md, test/test_synthetic.py, test/test_mirror.py, test/test_trials.py (for style), scripts/checks/navigation.py. Not opened: docs/MUTATION.md beyond a grep, docs/JOURNAL.md.
- **Complaints:** CLAUDE.md has no row for "what the harness is given" or for adding a file to the harness; the nearest row (the synthetic market) points at synthetic.py, which is the file being emptied. The news cut (HAR-12) names a "publish-time cut" but no document gives the cutoff's time of day (NL-04 says `publish_time < t's cutoff`); I had to leave it a caller's parameter. `docs/MUTATION.md` is a table whose rule for explaining a mutant is only discoverable from `scripts/checks/mutation.py`; a mutant of `x[0]` on a sorted pair of duplicate keys is equivalent and not obvious. The precommit run showed a survivor in `scripts/checks/modules.py` that I had not touched, with no hint whether it was already known (it was not in MUTATION.md; a direct test now kills it).
- **Suggestions:** Add a routing row "What the harness is given: frame layouts, the stamp check | `neonrain/harness/market.py`, `docs/HARNESS.md` (first section, HAR-12) | HAR-12 | `test/test_market.py`". Put the news cutoff time of day in LEDGER.md NL-04 or HARNESS.md when Ghost decides it. Say in `docs/rules/` or the precommit header that survivors outside one's own files are the next agent's to kill too.
