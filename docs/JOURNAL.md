# Journal: every event in the work, as a record a researcher can count

One entry per event: a contradiction found, a decision taken, a failure caught or missed, a change
of direction, a measurement. Not a restatement of the commit log and not a status list and not the
design: the journal records *what happened while the work was done*. Fixed fields, the same as
Katana's and Suite Builder's, so entries can be counted across projects. Newest last. Written by
whoever was there, in the same commit as the event when possible; an agent writes its own entries.

Fields: **Who**, **Intent**, **Found**, **Options**, **Resolved**, **Touched**, **Caught by** (for a
failure), **Cost**, **Class** (`contradiction`, `ambiguity`, `failure-caught`, `failure-missed`,
`decision`, `measurement`, `direction`, `trial`, `deferred`).

---

### J-001 Founding
- **Who:** Ghost, Claude Fable.
- **Intent:** Found the project with the shape of Katana: decisions, roadmap, routing table, glossary,
  metrics, journal.
- **Found:** Ghost's starting design (every ticker as an input neuron; a Haiku agent scoring stories
  1–10 by ticker; horizons of 3 days, 1 week, 1 month, 3 months; cloud only, no CI, no local runs)
  and his method ("build a rigorous harness first, then the dumbest baseline, then add features one
  at a time").
- **Options:** Absolute price prediction vs cross-sectional direction and rank (took the latter,
  R-004). All-tickers-as-inputs vs pooled per-name training (took pooled, R-009). Live scorer vs a
  once-scored ledger (took the ledger, R-008). Java (Ghost's language) vs Python (proposed Python,
  R-001, for Ghost's word).
- **Resolved:** Fourteen decisions drafted; three left `proposed` for Ghost (R-001 toolchain, R-010
  artifact store, R-011 license).
- **Touched:** every founding document.
- **Class:** decision

### J-002 The ticker-holdout axis
- **Who:** Ghost, Claude Fable.
- **Intent:** Ghost, mid-founding: test on one stock, then another, and use the variance of accuracy
  to tell whether the model fit the data or learned an algorithm.
- **Found:** The variance idea is the only direct test of name-memorization and was missing from
  the plan. The single-stock part cannot stand (too few samples to train on; a held-out name's
  dates still share the market factor with trained names, so time leaks through it).
- **Options:** Replace the time split with a ticker split (refused: time is the primary leak);
  ignore (refused: the dispersion test is real); add as a second axis with dispersion reported
  beside every mean (taken).
- **Resolved:** R-014; the harness's grid is time × group; P-07 extended to require dispersion.
- **Touched:** R-014, R-005 (`See also`), ROADMAP §5, §6 phase 1.3 and 1.6, GLOSSARY (`group`,
  `dispersion`).
- **Class:** decision

### J-003 Python, and the audit it costs
- **Who:** Ghost, Claude Fable.
- **Intent:** Settle R-001.
- **Found:** Ghost chose Python and named its cost: he cannot audit it by hand as he can Java, so
  he will lean on testing.
- **Options:** Java after all (refused by Ghost); Python with ordinary tests (not enough: a test
  that cannot fail is not a check); Python with mutation-tested tests, readable-code rules, blind
  mirrors and hand-checkable ten-row examples (taken).
- **Resolved:** R-001 in force; R-015 added.
- **Touched:** R-001, R-015, CLAUDE.md (precommit now reports the mutation score), TODO 0.5.
- **Class:** decision

### J-004 Reachability
- **Who:** Claude Fable.
- **Intent:** ROADMAP 0.3: measure which hosts the workspace can reach before any fetch script is written.
- **Found:** Every price, news and dataset host refused by the proxy; PyPI and GitHub reachable;
  GitHub Releases, LFS uploads and REST writes refused for the session type; a plain git blob pushes.
  The `pip install` of a package was blocked by the session's own policy classifier on the first
  attempt; `pip download` worked, so PyPI itself is open.
- **Options:** Fetch from the workspace (impossible); Ghost supplies data through a data repository
  or the desktop bridge (taken as the proposal); a scheduled task elsewhere with network (parked for
  the news feed).
- **Resolved:** NR-F-01 written; R-016 proposed; R-010 superseded by it. A scratch branch
  `probe-plain` is left on GitHub because the proxy refuses branch deletion; Ghost deletes it.
- **Touched:** NR-F-01, R-010, R-016, `scripts/probe/reachability.py`.
- **Caught by:** the probe, by design of 0.3 (F-07).
- **Cost:** about twenty minutes.
- **Class:** measurement

### J-005 The handoff, for a long-form Opus project
- **Who:** Ghost, Claude Opus 5.
- **Intent:** Ghost is starting this as a long-form coding project and wants everything an Opus
  session needs to take over cold.
- **Found:** Seven routing rows in `CLAUDE.md` pointed at documents that did not exist, `HARNESS.md`
  among them — and `HARNESS.md` is load-bearing before any code, because R-015(c)'s mirror is
  written from it blind. A handoff alone would have pointed at holes.
- **Options:** Write the handoff only (refused: the rows still dangle); write the handoff plus every
  contract an agent must read before coding, leaving 0.5's tests and the lock for Opus as its first
  real work (taken); write the tests too (refused: it takes the first task away and the handoff is
  the thing that was asked for).
- **Resolved:** `HARNESS.md` (HAR-01 to HAR-13), `GHOST-IN-THE-KERNEL.md`, `LEDGER.md`,
  `SUPPLY-CHAIN.md`, `RESULTS.md`, `MUTATION.md`, `DONE.md`, `requirements.in`, `HANDOFF.md`;
  `CLAUDE.md`'s planning row now opens the handoff first. `test_harness_doc.py` is specified to fail
  until phase 1 exists, deliberately, rather than being written weak.
- **Touched:** every document named above; DONE.md 0.1 and 0.3.
- **Class:** direction

### J-006 The glossary would have failed its own first test
- **Who:** Ghost, Claude Opus.
- **Intent:** Read the founding documents before 0.5 and find what the doc tests would trip on.
- **Found:** Three enforced aliases had honest uses elsewhere: `prediction` in nine documents
  (the prediction ledger, the network's output, the glossary's own definition of ledger), `signal`
  and `oracle` in theGhost.md, ROADMAP.md and GHOST-IN-THE-KERNEL.md, each in its right sense.
  `test_glossary.py` as specified would have been red on the empty project. The handoff's red
  condition for that test ("backtester" in ROADMAP.md) named an unenforced alias, so it would not
  have turned the test red either.
- **Options:** Rewrite nine documents around the word (refused: the word is right there); enforce
  aliases only by whole phrase (refused: the test grows a parser for no gain); unenforce the three
  and say when an alias may be enforced (taken).
- **Resolved:** GLOSSARY.md's three aliases lose their backticks and its preamble gives the rule;
  HANDOFF.md's red condition uses `timeframe`.
- **Touched:** docs/GLOSSARY.md, docs/HANDOFF.md.
- **Caught by:** reading the documents against the tests specified for them, before writing any.
- **Class:** contradiction

### J-007 Three counts of the open decisions, none agreeing
- **Who:** Ghost, Claude Opus.
- **Intent:** The same read as J-006.
- **Found:** HANDOFF.md said four decisions were `proposed` and named two; TODO.md and ROADMAP.md
  0.2 were titled "three decisions" when one of the three was in force and another superseded.
  theGhost.md was right: R-011 and R-016 are the two proposed.
- **Options:** Keep a count in each title (refused: it goes stale at every decision); name the
  decisions and drop the count (taken).
- **Resolved:** 0.2 is "Ghost's founding decisions" in both files; HANDOFF.md says two.
- **Touched:** docs/HANDOFF.md, TODO.md, docs/ROADMAP.md.
- **Caught by:** reading the documents against theGhost.md.
- **Class:** contradiction

### J-008 The Hugging Face Hub answered
- **Who:** Ghost, Claude Opus.
- **Intent:** Bring `scripts/probe/reachability.py` under R-015(b)'s readability rules (type hints,
  one import per line, a `main`) and run it to show it still works.
- **Found:** In this session the Hugging Face Hub is reachable; J-004's session was refused it.
  Every other dataset host is still refused. FNSPID's card says CC BY-NC 4.0 and its news files are
  5.7 GB and 23 GB.
- **Options:** Change R-016's route to fetch from the Hub (refused: R-016 is Ghost's, and a route
  that depends on which session you got is not a route); record it and leave the decision to Ghost
  (taken).
- **Resolved:** NR-F-01 re-measured; R-016 and phase 5 unchanged pending Ghost. Worth his word:
  whether a session with the Hub open may stream FNSPID, filter it to the universe, and push the
  result to `neon-rain-data` in chunks under 100 MB, which would unblock phase 5 without his
  machine. The non-commercial license bears on R-011.
- **Touched:** scripts/probe/reachability.py, docs/FINDINGS.md, docs/HANDOFF.md (the clone path no
  longer assumes a home directory).
- **Caught by:** the probe, re-run as R-016's `Held by` asks.
- **Cost:** a few minutes.
- **Class:** measurement

### J-009 The lock's compiler
- **Who:** Ghost, Claude Opus.
- **Intent:** Settle how `requirements.lock` is compiled before 0.5 compiles it.
- **Found:** The handoff named `pip-compile` (pip-tools), which no file declares.
- **Options:** Add pip-tools to `requirements.in` (an eleventh dependency to build the lock of ten);
  `uv pip compile`, already in the session (taken by Ghost).
- **Resolved:** R-017; HANDOFF.md, SUPPLY-CHAIN.md and `requirements.in` name it. Still open for 0.5:
  PyPI's Linux torch wheel brings the CUDA libraries, and the CPU-only index
  (download.pytorch.org) is refused from this session.
- **Touched:** theGhost.md, docs/HANDOFF.md, docs/SUPPLY-CHAIN.md, requirements.in.
- **Class:** decision

### J-010 The first lock
- **Who:** Ghost, Claude Opus.
- **Intent:** 0.5's first step: compile and install `requirements.lock`.
- **Found:** Eight direct dependencies resolve to 27 packages; mutmut brings most of the rest
  (textual, rich, libcst, click, setproctitle). Every one has a cp312 Linux wheel, so the install
  runs with `--only-binary :all:` and no package builds or runs a script. The venv is 662 MB.
  The first install also upgraded the venv's pip from PyPI, outside the lock; caught on reading
  the output, the venv was rebuilt without it.
- **Options:** Drop mutmut for something lighter (refused: R-015a names it, and nothing lighter
  does the job); accept (taken).
- **Resolved:** R-018 (torch and anthropic wait for their phases; seven-day cooldown);
  `requirements.lock` committed; CLAUDE.md's install line is the full command.
- **Touched:** requirements.in, requirements.lock, theGhost.md, CLAUDE.md, docs/SUPPLY-CHAIN.md,
  docs/HANDOFF.md.
- **Caught by:** reading the install's output (the pip upgrade).
- **Class:** decision

### J-011 Step 0.5: the documents held, and what holding them found
- **Who:** Ghost, Claude Opus.
- **Intent:** TODO 0.5: a test for every founding document, `precommit.sh`, the readability lint.
- **Found:** Writing each red condition as a permanent test (a planted break the check must report)
  rather than breaking a document once by hand made the handoff's "watch it fail" repeatable. The
  checks then caught, on their first runs: the handoff's own example writing an enforced alias
  outside backticks; "HAR-nn" matching the alias `NN` (an alias in capitals now matches only in
  capitals); AGENT.md recording 2 files for the widest routing row when it was 3. Mutation testing
  over `scripts/checks/` left 139 survivors of 1,133. Most were unreachable defaults and
  `zip(strict=)` flips, designed out rather than explained (B905 off, its reason in
  `pyproject.toml`); the rest were real gaps: a `continue` no test told from a `break`, a
  `conflicts-with:` naming no entry passing silently, and **`neonrain/__init__.py` skipped by the
  module check, so an `import anthropic` there would have passed MOD-01**. Three equivalent
  mutants are explained in `docs/MUTATION.md`.
- **Options:** `test_harness_doc`'s code-reference half, which must fail until phase 1: leave it
  red (refused: the gate would refuse every push until phase 1), skip it (refused: weakening), a
  strict xfail conditioned on `neonrain/harness/` not existing (taken: it fails now, the loop goes
  red if it ever passes without the folder, and it runs for real once the folder exists).
- **Resolved:** 0.5 done (DONE.md). Friction worth Ghost's eye: AGENT.md's "Largest source file"
  is stale-checked, so every commit that grows the largest file must rerun `scripts/metrics.py
  --write`; it happened five times this step. Recording it only at tithe passes would end that.
  Two "Unsure" lines are in the code (MOD-04's static check; which RESULTS.md tables are held).
- **Touched:** `pyproject.toml`, `scripts/checks/`, `scripts/metrics.py`, `scripts/survivors.py`,
  `scripts/precommit.sh`, `test/`, docs/AGENT.md, docs/MUTATION.md, docs/DONE.md, TODO.md,
  docs/HANDOFF.md, CLAUDE.md.
- **Caught by:** the tests' first runs, and mutmut.
- **Cost:** one session.
- **Class:** measurement

### J-012 Tithe pass 0: the fresh-agent trial, and the trial that read its own answer key
- **Who:** Ghost, Claude Opus (running the trial), a fresh Claude Opus session (the subject).
- **Intent:** ROADMAP 0.6. Task, as given: "Propose where the cost model goes and what it would
  contain; say which files you would change, then stop." Pass: `CLAUDE.md` first,
  `docs/modules.json` within three reads, nothing changed.
- **Found:** A first attempt never ran: a short commit id as the session's revision is "ref not
  found" (use a branch or the full hash). The second, on `main` at 77ff4e2, took four turns, 29 s,
  $0.40. Its first call was `git log`, `ls` and a grep for "cost" over HARNESS.md, theGhost.md,
  HANDOFF.md, TODO.md and GLOSSARY.md; its second read HANDOFF.md, HARNESS.md, then modules.json.
  It changed nothing. Its proposal was right: `neonrain/harness/cost.py` under HAR-06, the three cost
  levels, turnover over the union of tickers, pure functions, after 1.1 to 1.3. It also found:
  (a) HAR-06 leaves four questions open (entry and exit, overlapping sleeves, both legs,
  delistings); (b) creating `neonrain/harness/` for one file would turn 0.5's harness-doc xfail red
  and block every push until all thirteen HARs were cited. But the grep had read HANDOFF.md's
  description of this very trial: it named the trial and scored itself, and claimed it had opened
  `CLAUDE.md` first, which the tool loads for every session.
- **Options:** Score it as written (pass by tool call, fail by file, with a contaminated subject);
  rerun on a stripped copy (no way to strip files from a fresh session's checkout without a branch);
  record the result with its caveats and stop trials reading their own key (taken, R-020 proposed).
- **Resolved:** 0.6 done with caveats (DONE.md). (b) fixed: the harness-doc test now refuses always a
  HAR the code names that the document lacks, and expects the converse to fail until 1.7 freezes the
  harness; a planted `neonrain/harness/split.py` citing HAR-03 passes, one citing HAR-99 is refused.
  (a) is in HANDOFF.md for 1.4, the contract's author to settle. The same planted file showed "Docs
  lines per source line" will go stale on every phase-1 commit, as the largest file did; proposed to
  Ghost to fold into R-019. The spent prompt removed from HANDOFF.md and ROADMAP.md. AGENT.md
  re-measured (the tithe's recording, R-019).
- **Touched:** test/test_harness_doc.py, scripts/checks/harness_doc.py, theGhost.md (R-020),
  docs/HANDOFF.md, docs/ROADMAP.md, docs/DONE.md, TODO.md, docs/AGENT.md.
- **Caught by:** the trial (b, and a); reading its transcript (the contamination).
- **Cost:** $0.40 for the trial; a few minutes lost to the short commit id.
- **Class:** trial

### J-013 Step 1.1: the synthetic market, and two contract sentences that could not be built
- **Who:** Ghost, Claude Opus.
- **Intent:** ROADMAP 1.1 / HAR-10: a seeded market with a planted edge of known strength.
- **Found:** (a) HAR-10 named the edge but not what it predicts; a choice in code would have been a
  decision hidden in a function. (b) HAR-12 refused a feature stamped "at or after" the close of its
  date, which every honest price feature is (a feature from the close of *t* is known at *t*): built
  as written, the stamp check would have refused them all. (c) Mutation testing reported 57
  "survivors" of the generator that were timeouts; run by hand, each was killed at once. mutmut
  forked its workers from the process that had run the suite, and polars's thread pool deadlocks
  across a fork. (d) After that, six real survivors: the noise's sign and `ρ**3` for `ρ**2` (too small
  for a statistical test to see), `<=` for `<` at the delisting line, a dropped frame schema (only
  an empty market shows it), and a missing calendar (the determinism test compared None with None).
- **Options:** (a) the edge predicts the next day's idiosyncratic return, so against an *h*-day
  return it thins to about ρ/√h and the four horizons differ for a reason (taken), or a persistent
  edge (more parameters, no test that needs it yet). (c) one thread for polars in the tests, or
  mutmut's fork server (taken: it isolates the cause without changing what the tests run).
- **Resolved:** HAR-10's model written exactly before the code; HAR-12 reads "later than *t*" for
  price features and keeps "at or after" for news (the ledger's cut). The generator built to it;
  the six survivors killed by tests (one return rebuilt from HAR-10's text alone, the line case,
  the empty market, the calendar's value) and the slow kill made fast (the test's join declares
  itself one-to-one). Glossary: "synthetic market".
- **Touched:** docs/HARNESS.md (HAR-10, HAR-12), docs/GLOSSARY.md, `neonrain/`, test/test_synthetic.py,
  `pyproject.toml`, docs/modules.json (entry point), TODO.md (phase 1's items), docs/DONE.md,
  docs/HANDOFF.md.
- **Caught by:** writing the code against the contract (a, b); mutmut, then running its mutants by
  hand (c, d).
- **Class:** ambiguity

### J-014 Step 1.2: the targets, and a bias written into the contract
- **Who:** Ghost, Claude Opus.
- **Intent:** ROADMAP 1.2 / R-004 / HAR-02: direction and rank labels at the four horizons.
- **Found:** (a) With an odd number of tickers the median is one ticker's own return, so that
  ticker's excess is exactly 0 every date: "dropped ties" is about 1/N of the direction cells, not a
  rare event, and HAR-02 did not say whether the tied row keeps its rank. (b) HAR-02 did not say
  whether the last *h* dates (no *t+h* on the calendar) count as missing; counted, every run would
  carry 63 days of "missing" cells. (c) The fixed `N(t) < 20` made the step's own check impossible:
  a three-ticker series is thin on every date. (d) A ticker delisted inside a window has no price at
  *t+h*, so HAR-02 drops exactly the windows in which names fall to delisting: survivorship bias in
  the labels themselves, on an honest universe. (e) Mutation: the joins' `validate=` guards were
  redundant with each other, so no single one could be shown to matter; the output's order was
  unpinned; and an eligible ticker with no price on the day itself had no test, so an inner join
  could have hidden it.
- **Options:** (d) build a delisting return now (refused: it changes the contract, the author's
  call); build as written and record it first (taken, P-03).
- **Resolved:** HAR-02: a tie loses its direction label and keeps its rank; the last *h* dates make
  no cells and are not counted; `min_tickers` is config, 20 by default. NR-F-02 written; with Ghost
  in HANDOFF.md. The redundant guards replaced by one check at the entry (no (ticker, date) twice in
  prices or universe, a strictly increasing calendar, `min_tickers` ≥ 2), naming every reason; tests
  for the order and the missing-at-*t* case. The planted edge's rank correlation thins with the
  horizon as HAR-10 says, which checks 1.1 and 1.2 against each other.
- **Touched:** docs/HARNESS.md (HAR-02), docs/FINDINGS.md (NR-F-02), `neonrain/targets.py`,
  test/test_targets.py, docs/modules.json, TODO.md, docs/DONE.md, docs/HANDOFF.md.
- **Caught by:** writing the code against the contract (a to d); mutmut (e).
- **Class:** ambiguity

### J-015 Step 1.3: the splits, where a day either way is a leak
- **Who:** Ghost, Claude Opus.
- **Intent:** ROADMAP 1.3 / R-005 / R-014 / HAR-03 to HAR-05: walk-forward folds with purge and
  embargo, crossed with seeded ticker groups.
- **Found:** (a) "756 training dates after purging" depended on the horizon, since purging is per
  horizon, while HAR-03 wants one set of folds for all four. (b) Nothing said whether a partial last
  test span is a fold. (c) `sha256(seed + ticker)` does not run with an integer seed, and read as
  string concatenation it makes seed 1 with "2AB" the same as seed 12 with "AB". (d) A hash partition
  can leave a group empty on a small universe. (e) Not a gap, worth knowing: with E ≥ 63 the embargo
  alone already keeps every training label out of every test span; the purge is what keeps labels
  out of the *embargo*, which is HAR-04's "< s − E". And training labels' medians include the
  held-out group's past returns: the ticker axis is not a pure split, as R-014 already says. (f)
  Writing `cell` showed that "not in the other groups" would have tested any ticker missing from
  the group map. (g) Mutation: an off-by-one at the test span's end had no test; and two mutants
  turned the fold loop infinite, killed only by hanging.
- **Options:** (a) count at the longest horizon (taken: the same folds for every horizon, and the
  shorter horizons simply keep more rows).
- **Resolved:** HAR-03: the first fold's `b` is the first with `b − a − 63 ≥ 756`; whole test spans
  only; `a = b − W` for a rolling window. HAR-05: `sha256(f"{seed}:{ticker}")`; an empty group is
  refused, naming it. `cell` selects the held-out group by name and refuses an unmapped ticker; the
  fold loop is a `range`, which cannot run forever; tests for the end of the test span, the default
  seed, the empty calendar, and the error messages' numbers.
- **Touched:** docs/HARNESS.md (HAR-03, HAR-05), `neonrain/harness/split.py`, test/test_split.py,
  docs/modules.json, TODO.md, docs/DONE.md, docs/HANDOFF.md.
- **Caught by:** writing the code against the contract (a to d, f); mutmut (g).
- **Class:** ambiguity

### J-016 Step 1.4a: the cost answers, the portfolio, and a sum that depended on row order
- **Who:** Ghost, Claude Opus.
- **Intent:** ROADMAP 1.4, first part: HAR-06's four questions and HAR-07's long–short decile
  portfolio after costs. 1.4 as a whole (a cost model, five metrics, the deflated Sharpe, two-axis
  dispersion, a 100-seed check and a blind mirror) is several sittings, so it is taken in three
  parts, recorded in TODO.md.
- **Found:** (a) Beyond HAR-06's four questions, HAR-07's portfolio left open: how many names a leg
  holds when `N/10` is not whole or is under one; ties at the decile edge; what a sleeve holds over
  its `h` days; what the day counts before `h` sleeves exist; where a delisted member's slot goes;
  and a sleeve still open when the calendar ends. (b) Mutation: the first version kept per-day sums
  in dicts with `.get(day, 0.0)` defaults, and most of its 18 survivors lived in those defaults
  (they matter only when a whole leg has nothing earning on a day). (c) Two survivors were
  `group_by(maintain_order=...)` flips: if polars visits the dates in another order, the floats are
  added in another order and the sums can differ in the last bits between runs, against HAR-11.
  (d) A name with no price the day after it is bought closes on the opening day, which no test had.
- **Options:** (b) explain the defaults as equivalent, or write arrays over the calendar where adding
  is plain addition (taken). (c) sort inside polars and trust it, or loop over the sorted dates in
  Python (taken: the order is visible in the code).
- **Resolved:** R-021 (Ghost: everything pays, nothing nets). HAR-07's sleeve made exact: `⌊N/10⌋`
  names a leg, none under ten; ties by ticker; equal weights held through the hold; cash before the
  first `h` sleeves; a delisted slot closed at its last price, paying, then earning 0; a sleeve open at
  the calendar's end closed there. `neonrain/harness/portfolio.py` built to it with arrays and
  `for` loops (none can run forever); a test that any row order gives the same bits. On the
  synthetic market the steady daily cost is exactly `4c/h` and the planted edge pays before costs.
- **Touched:** theGhost.md (R-021), docs/HARNESS.md (HAR-06, HAR-07), `neonrain/harness/portfolio.py`,
  test/test_portfolio.py, docs/modules.json, TODO.md, docs/HANDOFF.md.
- **Caught by:** writing the code against the contract (a); mutmut (b to d).
- **Class:** ambiguity

### J-017 Step 1.4b: the metrics, and a deflated Sharpe that was undefined on the first run
- **Who:** Ghost, Claude Opus.
- **Intent:** ROADMAP 1.4, second part: HAR-07's accuracy, balanced accuracy, IC, Sharpe and DSR in
  `neonrain/harness/metrics.py`. Every ambiguity is settled in HAR-07's text, not only in the code,
  because 1.4c's mirror is written from that text alone.
- **Found:** (a) HAR-07's DSR formula is undefined at `N = 1`: `Z⁻¹(1 − 1/N)` is `Z⁻¹(0) = −∞`, so
  the first run of every project would have had no DSR. (b) It did not say whether `V` is the
  variance of annualized or daily Sharpes (it must be daily, the unit of `SR`), which skewness and
  kurtosis estimators, or which divisor for any standard deviation. (c) Accuracy did not say what a
  tie row (no direction label) does, or a score of exactly 0.5; balanced accuracy is undefined with
  an empty class; the IC had no rule for a date whose scores or labels are all equal, and a fixed 20
  where HAR-02 now has `min_tickers`. (d) Worked by hand, the DSR's square root
  `1 − skew·SR + (kurt − 1)/4·SR²` is never negative for real data (kurt − 1 ≥ skew², so it is at
  least `(1 − skew·SR/2)²`): its "undefined" branch is a float-error guard. (e) Mutation: no test
  had two thin or two flat IC dates, a dropped date before a good one, a two-day Sharpe, or a root
  between 0 and 1.
- **Options:** (a) the formula as written with `N ≥ 2` required (refused: the first run is real);
  `SR₀ = 0` at `N = 1`, so the DSR is then the probabilistic Sharpe ratio (taken: nothing was
  selected, so nothing is deflated).
- **Resolved:** HAR-07 states each choice: labelled rows only, 0.5 predicts 0; undefined metrics are
  reported as undefined (`None` in code, never a stand-in number); IC by Pearson on average ranks,
  thin and flat dates dropped and counted, `min_tickers` from HAR-02; every `sd` with divisor
  `n − 1`; moments with divisor `T`; `V` over daily Sharpes; `SR₀ = 0` at `N = 1`. The DSR's
  arithmetic is its own function, so the guard is tested on chosen numbers. HAR-07's `SR₀` is
  checked against the true expected maximum of 10 and 100 normals (1.5388, 2.5076) within 0.05.
- **Touched:** docs/HARNESS.md (HAR-07), `neonrain/harness/metrics.py`, test/test_metrics_har07.py,
  docs/modules.json, TODO.md, docs/HANDOFF.md.
- **Caught by:** writing the code against the contract and the hand examples (a to d); mutmut (e).
- **Class:** ambiguity

### J-018 Step 1.4c: the blind mirror, a leak it uncovered by agreeing, and the noise band
- **Who:** Ghost, Claude Opus; a second agent for the mirror.
- **Intent:** ROADMAP 1.4, last part: HAR-08's dispersion, the mirror of HAR-07 (R-015c), and 1.4's
  check (a zero-edge strategy inside its noise band across 100 seeds).
- **Found:** (a) The mirror, written from HAR-06 and HAR-07's text with no file read, agreed with
  the code to 1e-12 at once. Breaking the code three ways to see it fail, one break (a delisting's
  cost booked a day late) was not caught: no held name ever delisted in the comparison. (b) The
  reason was a leak, not a test gap: the scores had been built from label rows, and a label needs a
  price at *t+h* (NR-F-02), so every name about to delist had been kept out of the tradable set by
  knowledge of day *t+h*. (c) The mirror's own list of ambiguities found four places HAR-07 left to
  the reader (which leg takes the earlier ticker at a tie, the day a delisting's cost is booked, a
  price that returns, an IC with zero spread); code and mirror had chosen alike, by luck of reading.
  The mirror also noted that booking a delisting's cost on its last price day is a look-ahead in the
  daily timing (no total moves). (d) HAR-08 did not say what an undefined cell does to the averages.
  (e) The 100-seed check costs 45 s, over the fast loop's budget.
- **Options:** (b) score the portfolio on every universe row with features (taken; written into
  HAR-07 and NR-F-02). (e) run fewer seeds (refused: the band is about the 5% tail) or mark it slow
  and run it in `precommit.sh` (taken, AGENT.md: the harness on the synthetic market has its own
  budget).
- **Resolved:** HAR-07 states the four, and the scoring rule; HAR-08 leaves undefined cells out of
  both averages and counts them. `test/test_mirror.py` asserts at least 20 held delistings and shows
  that scoring labelled rows holds none; with it, all three breaks turn the mirror red. Noise band,
  `pytest -m slow`: 3 of 100 seeds ≥ 0.95 at zero cost, mean 0.471; after 10 bps 0 and 0.012; at
  ρ = 0.1 all 100, so the check discriminates. 1.4 done.
- **Touched:** docs/HARNESS.md (HAR-07, HAR-08), docs/FINDINGS.md (NR-F-02),
  `neonrain/harness/dispersion.py`, test/mirror_har07.py (the mirror's, unchanged), test/test_mirror.py,
  test/test_dispersion.py, test/test_noise_band.py, `pyproject.toml` (the slow marker),
  `scripts/precommit.sh`, docs/modules.json, TODO.md, docs/DONE.md, docs/HANDOFF.md.
- **Caught by:** breaking the code on purpose to watch the mirror fail (a, b); the mirror's report (c).
- **Class:** failure-caught

### J-019 An escalation rule, so a Claude Sonnet agent can work here
- **Who:** Ghost, Claude Opus.
- **Intent:** Ghost, 2026-10-23: a Sonnet agent tries a code fix once; an easy fix needs no
  escalation; a hard failure goes to a Claude Opus instance. In the entrance path.
- **Found:** "Fails in a way that is difficult" needed a test an agent can apply to itself.
- **Options:** a retry count alone (refused: a typo the output names is not difficult); a judgement
  of difficulty (refused: unmeasurable); red after the one attempt and the cause not plain from the
  output (taken).
- **Resolved:** R-022; its own short section in CLAUDE.md (913 words, under AGT-03's 1,200), with
  what to hand the Opus instance (task, routing row, diff, failing output) and what to do if none
  can be invoked (stop and say so).
- **Touched:** CLAUDE.md, theGhost.md (R-022), docs/HANDOFF.md, docs/AGENT.md.
- **Class:** decision
