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

Last review: d0e7285 (2026-10-23, tithe pass 1, J-033: five debriefs, entries wiped)

## Entries
### 2026-10-23 R-024 (c), the full check's cost (Claude Sonnet)
- **Task:** R-024 (c): take the cost out of the mutation run
- **Opened:** CLAUDE.md, scripts/precommit.sh, pyproject.toml, theGhost.md (R-024 by grep), docs/MUTATION.md, test/conftest.py, mutmut 3.8's own source in .venv (__main__.py, runners/harness.py, workers/isolation.py, mutation/trampoline.py)
- **Complaints:** no routing row for the full check or mutmut itself: I found R-024 and mutmut's behaviour by grep, and the only note on why `rm -rf mutants` stays is the task text. Nothing says where mutmut's config reasons live beyond comments in pyproject.toml. `mutants/mutmut-stats.json` keeps per-test timings, and the per-mutant durations in the .meta files are all 0.0 here, which cost me a detour.
- **Suggestions:** a row "The full check's cost" pointing at precommit.sh, `[tool.mutmut]` and R-024, saying that mutmut already selects tests per function from its stats (so look at test order and cost, not selection).

### 2026-10-23 TODO 0.4, the artifact store (Claude Sonnet)
- **Task:** TODO 0.4: `scripts/fetch/artifacts.py`, put and get by SHA-256 through a private git repository
- **Opened:** CLAUDE.md, TODO.md (0.4), theGhost.md (R-016 by grep), docs/ROADMAP.md (0.4 by grep), docs/NAVIGATION-LOG.md, test/test_manifest.py, data/MANIFEST.md, scripts/probe/reachability.py (for style), pyproject.toml, scripts/checks/readability.py, test/conftest.py, docs/HANDOFF.md
- **Complaints:** the routing row "A dataset: fetch, manifest, universe" names `scripts/fetch/` and `data/MANIFEST.md (phase 2)` but the folder did not exist, so I had no sibling script to copy the style from and used `scripts/probe/`. Nothing said where a script's own docs go; I put the artifact store's layout in `data/MANIFEST.md` because the row points there. I learned only by a failing test that `scripts/` has no `__init__.py` yet tests import it as a namespace, and that readability.py forbids `*args` (a thin git helper needed a tuple parameter). `[tool.mutmut] also_copy` must list a new scripts folder or the copied tests cannot import it; no document says so.
- **Suggestions:** a line in the "dataset" row that artifacts.py is the artifact store and its layout is in `data/MANIFEST.md`; a note by `also_copy` in pyproject.toml (or the readability rules) that a new top-level scripts folder needs adding there.

### 2026-10-24 TODO 2.1 (a), the trading calendar (Claude Sonnet)
- **Task:** TODO 2.1 (a): the NYSE trading calendar by rule in `neonrain/universe/`
- **Opened:** CLAUDE.md, TODO.md (2.1 by grep), docs/modules.json, docs/HARNESS.md (first section), neonrain/harness/market.py (calendar lines by grep), docs/JOURNAL.md (J-033 by grep), neonrain/targets.py and test/test_targets.py (for style), scripts/checks/readability.py, docs/GLOSSARY.md, docs/MUTATION.md, pyproject.toml (ruff)
- **Complaints:** I looked first in the routing table for a row on the calendar: the "dataset: fetch, manifest, universe" row was the nearest, but points at scripts/fetch and not at `neonrain/universe/`, which does not exist yet. The ruff rules (type hints on every test function, ANN) were learned only from precommit refusing; the fast loop (`pytest`) does not run ruff, so a green fast loop still failed at the first step of precommit. Nothing says how to cope with mutmut survivors of arithmetic constants: I learned by `mutmut show` and a brute-force script what "equivalent" needs to show. `mutmut results` lists the whole project's "not checked" mutants, so I filtered by grep.
- **Suggestions:** a line in the Commands section: "run `.venv/bin/ruff check neonrain test` with the fast loop"; in docs/MUTATION.md, one sentence on how to prove an equivalent arithmetic mutant (a brute force over the stated domain, quoted in the row); `mutmut run "<module>.*"` runs one module's mutants.
