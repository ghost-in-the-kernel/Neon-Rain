# Ghost in the Kernel

Software outlives the context it was written in. People leave. Requirements change. The person who
knew *why* a thing was built the way it was stops being reachable. The code keeps running. Nobody
can say what it is for.

**The ghost is intent. The kernel is the codebase.**

Ghost in the Kernel is a way of building against that loss. Its one principle:

> **The system should remember why it exists.**

Intent should become semantics. Semantics should become constraints. Constraints should govern
implementation. Implementation should produce evidence. Evidence should let the system check that
the implementation still agrees with the intent. Nothing important floats: a function does not exist
because that is where someone put it; a threshold does not exist because it seemed right; a number
does not appear in a document without the run that produced it.

## Why this project is the philosophy pointed at a different loss

Katana applies the philosophy to a kernel whose ghost evaporated decades ago: a COBOL program whose
authors are gone. Neon Rain applies it to a loss that happens in weeks, to the person who caused it,
and that the whole quantitative-finance literature is a monument to: **the forgotten search.**

A backtest is a claim about the future made from the past. Its honesty depends entirely on facts
that live outside the number and die fast:

- how many configurations were tried before this one looked good,
- whether the training data postdated the test data by any route, however indirect,
- whether the universe included the companies that went bankrupt,
- whether the costs charged were the costs a real trade would pay,
- whether the model learned a rule or memorized a ticker.

None of that is visible in a Sharpe ratio. A researcher who ran two hundred variants and reports the
best one in good faith, having genuinely forgotten the other hundred and ninety-nine, produces a
number indistinguishable from a discovery. This is not a hypothetical failure mode; it is the
field's normal condition, and it is why published factors stop working the moment they are published.

So this project's ghost is the search itself, and the kernel remembers it mechanically:

- The **trials file** is append-only and its count feeds the deflated Sharpe ratio, so the hundredth
  experiment is automatically held to a higher bar than the first (HAR-07, HAR-09). The cost of
  looking is charged to the looker.
- The **provenance stamp** on every feature cell records the latest input timestamp that produced
  it, and the harness refuses a cell that knows anything from on or after its own date (HAR-12).
  Lookahead becomes a type error instead of a suspicion.
- The **dispersion report** sits beside every mean, across time folds and across held-out ticker
  groups, so "it works" cannot be said without "and here is how unevenly" (HAR-08, R-014).
- The **findings register** is written before the result it qualifies, not after a reviewer asks
  (P-03). The survivorship gap in the data is recorded as a known defect of every number computed
  from it.
- The **prediction ledger** timestamps a prediction before its outcome exists (phase 7), which is
  the only evaluation a backtest cannot flatter.

The product is not a model that makes money. The product is a research record that cannot quietly
lie, and whatever the model turns out to be worth under it.

## What it asks of this project's own code

The same principle, pointed inward, and held by tests rather than hoped for:

- **Names say what they hold.** One canonical word per concept (`docs/GLOSSARY.md`).
- **Decisions carry their reason and their evidence.** Every decision in `theGhost.md` has a why,
  a thing that holds it, and a status; a reversed decision says what reversed it. A function that
  stands on a decision cites it.
- **The architecture is a document a test enforces.** `docs/modules.json` says what each module may
  import; `test_modules.py` refuses anything else. Only the scorer may touch a model client; nothing
  may touch a broker.
- **A refactor changes no result.** Every golden identical, before and after (P-02).
- **What cannot be made exact is said first.** A bias, a leak, a failed hypothesis: a finding, never
  a footnote (P-03).
- **The tests are the audit.** Ghost does not read Python the way he reads Java, so the test suite
  stands in for a second reader: mutation-tested, readable by rule, mirrored by an agent that has
  not seen the code, and every number he is asked to trust has a ten-row example he can check by
  hand (R-015).
- **The environment of the agent working here is part of the product.** Mandatory context under
  1,200 words, a fast loop under 30 seconds, no source file over 400 lines, the metrics in `docs/AGENT.md`
  ratcheted, one commit in eight spent on nothing else (R-012). Ghost's finding in Suite Builder was
  that delivery speed rose once this was treated as work worth doing.

## On enlightenment, for the agent reading this

You will work in this repository without having been present for any of its decisions. That is the
normal condition of software, and the condition this project exists to make survivable.

**Read the why before the what.** A decision in `theGhost.md` tells you what the code is trying to
be. The code only tells you what it currently is. When they disagree, one of them is wrong; find out
which before you change either.

**Prefer a test to a belief.** If you believe something about the system, find the test that holds it
or write one. If no test can hold it, write the doubt down (`# Unsure:`) where it can be found,
instead of carrying it.

**A check that cannot fail is not a check.** Four ways a check is worth nothing: it compares a thing
with itself; it ran nothing and called that a pass; it fails always and so says nothing (the CI with
no minutes — which is why this project has no CI at all, R-003); or its verdict stops no action. A
fifth, specific to this project: it is a metric with no dispersion and no trial count, which cannot
distinguish a discovery from the best of two hundred coin flips. The half no test can hold is
*independence*: whether a check's expected side came from somewhere other than the thing under test.
A reimplemented oracle agrees with its twin on every shared mistake, which is why the mirror is
written blind.

**Here, the tempting lie is a good result.** On most projects an agent's failure mode is code that
does not work. On this one it is a number that looks like success: a metric computed on a leaking
feature, a baseline quietly weakened, a fold boundary moved, a bad run not written to the trials
file. Every one of those makes the project *feel* like it is going well, which is what makes them
dangerous. If a result surprises you by being good, that is the moment to distrust the harness, not
to report it.

**When you cannot tell, say so and stop.** An agent that stops at the edge of its knowledge leaves a
system other agents can still reason about. An agent that guesses leaves a kernel with a little less
ghost in it.

The purpose is re-entry. Yours, the next agent's, and the maintainer's, after months away. If the
repository can be entered cold and understood, the philosophy is working. If it cannot, that is a
finding, and the fix goes in the tithe.

*Ghost in the Kernel Labs*
