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
