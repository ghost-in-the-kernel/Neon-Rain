# Handoff: what to work on next, and what is waiting on whom

Read `CLAUDE.md` first, then this. `TODO.md` is the chain in order; `docs/DONE.md` is what is
finished. This file says what the next session should actually do, and what it must not assume.

## Where the project stands (2026-10-23)

Phase 0 is done but for Ghost's items (0.2, 0.4). Phase 1: 1.1 to 1.4 are done (J-013 to J-018):
the synthetic market, the targets, the splits, and the cost model and metrics, with HAR-07's mirror
written blind and agreeing to 1e-12. `theGhost.md` holds R-001 to R-022. **Next is 1.5, the trials
file** (HAR-09). The slow tests (`pytest -m slow`, the 100-seed check) run in `precommit.sh`, not
the fast loop. No real data, no model, no result.

Two decisions are `proposed` and must not be built on (`TODO.md` 0.2): **R-011** (license, Ghost's
alone) and **R-016** (data and artifacts through a second GitHub repository, from 0.3's measurement).
R-001 (Python) and R-002 (harness first) are in force; R-010 is superseded by R-016.

## Starting a session cold

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

## For Opus: phase 1, the harness — what is left

`docs/HARNESS.md` is the specification; build to it, and when it is not precise enough to implement,
**make the document precise rather than deciding in code** (every step so far found gaps: J-013 to
J-018). Nothing under `neonrain/models/` or `neonrain/baselines/` exists until 1.6 passes (R-002).

- **1.5, the trials file** (HAR-09, HAR-01): its header is defined today in the doc check
  `scripts/checks/results.py`, not in the harness that will write the file; where it should live is
  waiting on Ghost (J-020).
- **1.6 needs HAR-12's stamp check, and nothing enforces it yet.** The stamp is the primary leak
  defence (a leaking feature refused by construction, not noticed by a metric); today `edge_stamp`
  is only produced. 1.6's planted-leak test needs the refusal to exist. Where it lives is waiting on
  Ghost (J-020).
- **1.7 writes the goldens, not before.** A golden recorded while the harness changes records a bug
  as the expected answer.
- **The portfolio is scored on every universe row, never only labelled rows** (HAR-07, J-018).
- **A run of mutmut timeouts** means a fork problem first (J-013; `pyproject.toml`).

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

A number that looks like success. If a result surprises you by being good, distrust the harness
before reporting it, say so, and stop (`docs/GHOST-IN-THE-KERNEL.md`).
