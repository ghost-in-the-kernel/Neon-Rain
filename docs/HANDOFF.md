# Handoff: what to work on next, and what is waiting on whom

Read `CLAUDE.md` first, then this. `TODO.md` is the chain in order; `docs/DONE.md` is what is
finished. This file says what the next session should actually do, and what it must not assume.

## Where the project stands (2026-10-22)

Phase 0 is most of the way done: every founding document exists, `theGhost.md` holds R-001 to R-016,
and step 0.3 has been measured. **There is no Python in the repository yet** — not one module, not
one test. The first code written is phase 0.5's doc tests, then phase 1's harness. No model, no
data, no result.

Four decisions are `proposed` and must not be built on (`TODO.md` 0.2): **R-011** (license, Ghost's
alone) and **R-016** (data and artifacts through a second GitHub repository, from 0.3's measurement).
R-001 (Python) and R-002 (harness first) are in force; R-010 is superseded by R-016.

## Starting a session cold

```sh
git clone https://github.com/ghost-in-the-kernel/Neon-Rain /home/claude/neon-rain
cd /home/claude/neon-rain
git config user.name Ghost
git config user.email 118085043+ghost-in-the-kernel@users.noreply.github.com
```

Commits are authored as **Ghost** — he uses the commit count as a velocity tracker, so a session's
work lands as several real commits, each a deliverable that stands alone, not one batch at the end.
An agent keeps its own `Co-Authored-By` line.

Four things about this environment, each measured, not assumed (NR-F-01):

1. **There is no CI and no local machine** (R-003). `scripts/precommit.sh` run in the session is the
   only gate. If a `.github/workflows/` file ever appears, that is an intrusion: change nothing and
   report it.
2. **Only PyPI and GitHub are reachable.** Every price, news and dataset host is refused by the
   proxy, as are GitHub Releases, Git LFS uploads and REST writes. Do not write a fetch script that
   reaches a market-data host; it cannot work, and a retry with a different client is wasted time.
3. **`pip install` may be refused by the session's own policy classifier** even for PyPI, which is
   open (J-004). If it is, say so and ask Ghost to approve it rather than working around it.
4. **A scratch branch `probe-plain`** with a 1 MB random blob is still on GitHub; the proxy refuses
   branch deletion, so Ghost deletes it. Do not try again.

---

## For Opus: step 0.5, the doc tests and `precommit.sh` — start here

The documents exist and nothing holds them. Write `test/` and `scripts/precommit.sh` so that the
founding documents cannot rot silently. No data, no model, no network: the fast loop must run under
30 seconds (AGT-02) on a clean clone with only `requirements.lock` installed.

Compile the lock first: `pip-compile --generate-hashes requirements.in -o requirements.lock` (or the
equivalent), then `pip install --require-hashes -r requirements.lock`. The ten direct dependencies
and their reasons are in `requirements.in`; adding an eleventh is a decision, not an import.

Each test below names what it holds and **the mutation that must turn it red**. A test whose red
condition you have not seen is not a check (GHOST-IN-THE-KERNEL.md); write the test, break the
document deliberately, watch it fail, fix the document, commit.

| Test | Holds | Must turn red when |
| --- | --- | --- |
| `test_ghost.py` | `theGhost.md`: ids `R-nnn` unique and sequential from 001; every entry has Decision, Why, Held by, Source, Status, See also, subject; status is one of the five words; a `superseded by R-nnn` names an entry that exists and that names it back; no two `in force` entries share a `subject:` while carrying `conflicts-with:` | an id is duplicated; a supersession is one-sided; two in-force entries conflict on a subject |
| `test_glossary.py` | every backticked alias in `docs/GLOSSARY.md` appears in no other document under `docs/` or the root | a document uses an enforced alias (try writing "timeframe" into ROADMAP.md) |
| `test_todo.py` | `TODO.md` headings in numeric order; the first open item has a `Check:` line; no item appears in both `TODO.md` and `docs/DONE.md` | an item is out of order, or is in both files |
| `test_modules.py` | every `import` under `neonrain/` is allowed by `docs/modules.json`; MOD-01 (only `scorer` imports `anthropic`), MOD-02 (`harness` imports neither `models` nor `baselines`), MOD-03 (no broker client anywhere), MOD-04, MOD-05 | a planted `import anthropic` in `neonrain/features/` |
| `test_manifest.py` | every row of `data/MANIFEST.md` has a source, a license, a supplier and a hash; an empty table passes | a row with a blank license |
| `test_supply_chain.py` | no file under `.github/workflows/`; no `.claude/settings.json` hooks; no git hooks; every import in `neonrain/` resolves to something in `requirements.lock` or the standard library; none of the named worm artefacts exist | a planted empty workflow file |
| `test_harness_doc.py` | every `HAR-nn` in `docs/HARNESS.md` is referenced by a docstring or comment in `neonrain/harness/`, and the reverse; numbers unique and sequential | an invariant exists in the document and nowhere in the code (it will fail until phase 1, so **write it last and let it fail for now** — note that in the journal rather than weakening it) |
| `test_results.py` | every row of `docs/RESULTS.md` has a line in `harness/trials.tsv` with a matching `config_hash`, a dispersion on both axes, and findings cited by number; empty tables pass | a row with no trials line |
| `test_metrics.py` | `docs/AGENT.md`'s table against what `scripts/metrics.py` measures; a metric within target may move freely, past it may not get worse | a measured value worse than the recorded one |

`scripts/metrics.py` measures: mandatory context words (`CLAUDE.md`), fast-loop seconds, largest
source file, files a routing row opens, decisions without `See also`, results without a trials line
or a dispersion, datasets without a manifest line, docs lines per source line. It prints the table
and exits non-zero past a target.

`scripts/precommit.sh` runs, in order, and prints one summary line to quote in the commit: the fast
loop; `ruff` with the R-015(b) rules configured in `pyproject.toml` (type hints required,
comprehensions at most three clauses, no `*args`/`**kwargs` in our own signatures, functions under
40 lines, no bare `except`); `mutmut` over `neonrain/` with a survivor refused unless
`docs/MUTATION.md` has a line for it; `scripts/metrics.py`.

**Check for 0.5:** every doc test passes; `test_ghost.py` fails on a deliberately conflicting pair,
then passes when one is superseded; `precommit.sh` refuses an unexplained mutant; the readability
lint is configured.

Then **0.6, tithe pass 0**: the fresh-agent trial. A copy of the repository, an agent told only
*"Propose where the cost model goes and what it would contain; say which files you would change,
then stop."* Pass: it opens `CLAUDE.md` first, `docs/modules.json` within three reads, and changes
nothing. Record the result in the journal whichever way it goes, and fix what it showed.

## For Opus: phase 1, the harness — the shape of the work

`docs/HARNESS.md` is the specification; build to it, and when it is not precise enough to implement,
**make the document precise rather than deciding in code**. The order is `TODO.md`'s and is not
negotiable: nothing under `neonrain/models/` or `neonrain/baselines/` exists until 1.6 passes
(R-002).

1.1 synthetic market (HAR-10) → 1.2 targets (HAR-02) → 1.3 splits (HAR-03 to HAR-05) → 1.4 costs and
metrics (HAR-06, HAR-07) → 1.5 the trials file (HAR-09) → 1.6 the adversarial tests → 1.7 freeze.

Three things about phase 1 that are easy to get wrong:

- **The provenance stamp (HAR-12) is the primary leak defence**, not the statistical tests. Build it
  into the feature contract from the first line of `neonrain/features/`, so a leaking feature is
  refused by construction rather than noticed by a suspicious metric.
- **The mirror test (R-015c) must be written blind.** Spawn a subagent, give it `docs/HARNESS.md`
  §HAR-07 and nothing else — not the code, not your implementation's shape — and have it write an
  independent, deliberately naive implementation of the metrics. Then compare on the synthetic
  market. If you write both sides, you have written a mirror that agrees with itself on every shared
  mistake, and phase 1's most important check is worthless.
- **The goldens are written at 1.7, not before.** A golden recorded while the harness is still
  changing records a bug as the expected answer.

## For Ghost: waiting on you

1. **R-011, the license.** Protective as Katana's (private, all rights reserved, nothing leaves),
   research-open on the harness only (the methodology is citable and checkable; the model and ledger
   stay private), or fully private with no intent to publish. The harness is the part with
   standalone value and the part that could support the NSF study; the model loses any edge on
   publication. Phase 1 can proceed without this; nothing leaves the repository until it is settled.
2. **R-016, the two data repositories.** `neon-rain-data` and `neon-rain-artifacts`, both private,
   created by you (this session type cannot create repositories). Then phase 2 can start.
3. **Delete the `probe-plain` branch** on GitHub.
4. **Approve `pip install` if the classifier blocks it**, or say how you would rather it be done.
5. **Phase 5's news feed is blocked on you** (NR-F-01): a dataset with publish timestamps, obtained
   where there is network access and pushed to `neon-rain-data`. FNSPID on Hugging Face is the
   leading candidate — 15M+ timestamped items with tickers — and its license is yours to check
   before it enters. Phases 1 to 4 do not wait on this.
6. **The calibration set, phase 5.3**: 200 news stories hand-labelled by you (bullish / bearish /
   neutral, and which ticker), which is what the scorer's own accuracy is measured against. You are
   the first reviewer here as you are on Katana.

## Waiting on a run

Nothing yet. The first measurements that change the plan are: 1.6's zero-edge noise band (does the
harness report chance when there is no edge?), 3.1's baseline edge at each horizon, and 3.2's tree.

## Trials: questions to be settled by running something, not by arguing

Each gets a journal entry of class `trial` naming the trial, its result and the decision it produced.

- **T-01 (phase 1.6)** Does the zero-edge strategy's deflated Sharpe sit inside its noise band
  across 100 seeds? If not, the harness is optimistic and nothing built on it means anything.
- **T-02 (phase 3)** Do the published cross-sectional baselines (12-1 momentum, short-term reversal)
  show any edge at all on this universe after 10 bps? A flat result here is informative: it means
  the data or the universe cannot show what the literature found, and that must be understood
  before a network is trained on it.
- **T-03 (phase 4)** Does the network beat the tree at any horizon out of sample? R-009 blocks
  breadth until it does.
- **T-04 (phase 5.3)** Does the pinned Haiku scorer agree with Ghost's hand labels better than
  FinBERT does? If not, the cheaper non-LLM scorer is the feature and R-008's design loses its
  reason.
- **T-05 (phase 6.2)** Does news help the 3- and 5-day horizons and not the 63-day one, as F-04
  predicts? The prediction is written in `docs/RESULTS.md` before the run.

## What to distrust

On most projects an agent's failure mode is code that does not work. Here it is **a number that
looks like success**, because every mechanism in this repository exists to stop one. A metric
computed on a leaking feature, a baseline quietly weakened, a fold boundary moved by one day, a bad
run not written to the trials file, a golden re-recorded after a change: each of those makes the
project feel like it is going well.

If a result surprises you by being good, distrust the harness before reporting it. Say so, and stop.
