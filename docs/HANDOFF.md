# Handoff: what to work on next, and what is waiting on whom

Read `CLAUDE.md` first, then this. `TODO.md` is the chain in order; `docs/DONE.md` is what is
finished. This file says what the next session should actually do, and what it must not assume.

## Where the project stands (2026-10-23)

Phase 0 is done but for Ghost's items (0.2, 0.4). Phase 1: 1.1 to 1.5 are done (J-013 to J-018,
J-026): the synthetic market, the targets (delisting ends, J-024), the splits, the cost model and
metrics with HAR-07's mirror written blind, and the trials file with HAR-01's config hash; then
`neonrain/harness/market.py`, the frame layouts and HAR-12's stamp refusal (J-029); and 1.6, the
adversarial tests (J-030, J-031); 1.7, the freeze (J-032): the harness is frozen, and a change
that moves a golden needs a decision in force; and 1.8, tithe pass 1 (J-033). Phase 1 is done.
Phase 0 is done (0.4, J-038). **Next is phase 2**, real data: its items are written into `TODO.md`
from ROADMAP phase 2 when it opens. Its trading calendar is the exact NYSE
calendar, derived in the repository from a holiday data file, no new dependency (Ghost, 2026-10-23;
J-033). The slow tests (`pytest -m slow`) run in `precommit.sh`. No real data, no
model, no result.

No decision is `proposed`. **R-011** is in force: the repository is private, all rights reserved.
R-001 (Python), R-002 (harness first) and R-016 (data and artifacts through two private
GitHub repositories, approved 2026-10-23) are in force; R-010 is superseded by R-016.

## Starting a session cold

**Who does a task (J-027):** each new task goes to a fresh Claude Sonnet agent, briefed with the task
and "follow CLAUDE.md" (as J-022 and J-026 did); Claude Opus reviews the diff, runs the gate, writes
the journal entry and pushes. The agent debriefs in `docs/NAVIGATION-LOG.md`; about every ten commits
its entries are reviewed, as its header says.

Clone, then `CLAUDE.md`'s commands (the venv) and its two rules (commits authored as Ghost). Ghost
reads the commit count as velocity, so a session's work lands as several commits, each a deliverable
that stands alone.

Four things about this environment, each measured, not assumed (NR-F-01):

1. **There is no CI and no local machine** (R-003). `scripts/precommit.sh` run in the session is the
   only gate. If a `.github/workflows/` file ever appears, that is an intrusion: change nothing and
   report it.
2. **Only PyPI and GitHub are reachable, as a rule.** Every price and news host is refused by the
   proxy, as are GitHub Releases, Git LFS uploads and REST writes; the Hugging Face Hub was open from
   one session and not another (J-008). Do not write a fetch script for a market-data host.
3. **`pip install` may be refused by the session's own policy classifier** even for PyPI, which is
   open (J-004). If it is, say so and ask Ghost to approve it rather than working around it.
4. **A scratch branch `probe-plain`** is Ghost's to delete; the proxy refuses branch deletion.

---

## For Opus: phase 1, the harness — what holds now that it is built

`docs/HARNESS.md` is the specification; build to it, and when it is not precise enough to implement,
**make the document precise rather than deciding in code** (every step so far found gaps: J-013 to
J-018). Nothing under `neonrain/models/` or `neonrain/baselines/` exists yet; 1.6 has passed, so phases 3 and 4 may begin it (R-002).

- **HAR-12's stamp check exists** (`market.check_stamps`, J-029): 1.6's planted-leak test calls it.
  The news cutoff's time of day is undecided (phase 5, NL-04); until a run gives one, a news stamp
  is refused, not guessed at.
- **A DSR's `N` is `trials_so_far + 1`** from the trials file (HAR-09), counting every earlier line
  of the same metric at any horizon (J-026).
- **1.7 has written the goldens** (J-032). A golden recorded while the harness changes records a bug
  as the expected answer, so a harness change now needs every golden identical or a decision (HAR-14).
- **The portfolio is scored on every universe row, never only labelled rows** (HAR-07, J-018).
- **A run of mutmut timeouts** means a fork problem first (J-013; `pyproject.toml`).

## For Ghost: waiting on you

1. **Delete the `probe-plain` branch** on GitHub.
2. **Approve `pip install` if the classifier blocks it**, or say how you would rather it be done.
3. **Phase 5's news feed is blocked on you** (NR-F-01): a dataset with publish timestamps, obtained
   where there is network access and pushed to `neon-rain-data`. FNSPID on Hugging Face is the
   leading candidate — 15M+ timestamped items with tickers — and its license is yours to check
   before it enters, for commercial use too (R-016(d)). Phases 1 to 4 do not wait on this.
4. **The calibration set, phase 5.3**: 200 news stories hand-labelled by you (bullish / bearish /
   neutral, and which ticker), which is what the scorer's own accuracy is measured against. You are
   the first reviewer here as you are on Katana.

## Waiting on a run

Nothing yet. The zero-edge noise band is measured (`docs/DONE.md`, 1.4). The measurements that change
the plan now are 3.1's baseline edge at each horizon and 3.2's tree.

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

A number that looks like success. If a result surprises you by being good, distrust the harness
before reporting it, say so, and stop (`docs/GHOST-IN-THE-KERNEL.md`).
