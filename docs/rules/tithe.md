# Tithe: improving the agent's environment, changing no result (R-012)

Read this when your task is a tithe. A **tithe commit** (every eighth) is one improvement: steps 1,
3 and 5, no metrics. A **tithe pass** (the last item of a phase, TODO's "Tithe pass N") is every
step, by one agent in one session (R-023).

**You may change:** routing rows, documents, the glossary, names, cross-references, a document's
length, `scripts/checks/`. **You may not change:** any result (`.venv/bin/python
scripts/goldens.py` shows every golden identical), any test's assertions, anything under
`neonrain/`, `docs/HARNESS.md`'s rules, `theGhost.md`, `docs/ROADMAP.md`, `test/mirror_har07.py`,
a metric's target, the navigation log's entries. A fix that needs one of those, however small, is
a question for step 5. You write no feature, test or module: a tithe that builds has overshot.

## The steps

1. **Note every miss as it happens:** what you looked for, where you looked first, where it was.
   The notes are the pass's product; steps 3 and 5 are made of them.
2. **Re-measure** (pass only). `scripts/precommit.sh > <file>`; grep the file for `FAILED`,
   `Error`, `refused`, `unexplained`; its last line gives the fast loop's seconds and the full
   check's minutes, and that run's numbers are the ones recorded:
   `.venv/bin/python scripts/metrics.py --fast-loop <s> --full-check <min> --write`. It refuses
   while an armed metric has regressed: a question for step 5, never a number or a target to edit.
3. **Fix what the notes found:** a routing row, a stale sentence, a pointer. Each fix is one small
   diff. `CLAUDE.md` stays under 1,200 words; run `scripts/metrics.py --write` after changing it,
   and the fast loop after every fix.
4. **Read the debriefs** (pass only) in `docs/NAVIGATION-LOG.md`. Each complaint gets one verdict:
   acted on earlier, acted on now (step 3), not valid, open. Each entry's "Opened" list, read
   against the routing row its task matched, is the phase's measure of whether a fresh agent found
   its way (reads by file, in order; `CLAUDE.md` does not count); say where one did not.
5. **Stop and hand back.** Debrief as the log's header says. The handback: the precommit line, the
   metrics before and after, your notes, step 4's verdicts, the open questions, each with what it
   needs (a decision for Ghost, a ROADMAP line, a target that cannot be met). Commit nothing.

## The reviewer, not you

Reads the diff against the notes; wipes the log's entries and sets "Last review"; writes the
journal entry with step 4's verdicts and step 5's questions; moves the item to `docs/DONE.md`;
runs the gate and pushes, the message starting `tithe:`. Open questions go to Ghost.
