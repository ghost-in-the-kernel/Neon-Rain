# Escalations: each hand-off from a Claude Sonnet agent, by kind

One row per escalation under `docs/rules/escalation.md` (R-022), written by the agent that handed back or
the reviewer who took it. A row cites the journal entry that names it (the reviewer writes that entry),
and back-filled rows cite only what the journal states. Adapted from Ghost-Core's register (read only,
R-028 (3)); `scripts/checks/escalations.py` holds this file (`test/test_escalations.py`).

**Kinds**, the cause of the red run, by what would have prevented it:

- `missing-row`: CLAUDE.md had no routing row for the task. Fix: the row.
- `not-read`: the row existed and the agent did not follow it. Fix: make the row or the rule harder to miss.
- `wrong-row`: the row pointed at the wrong files or the wrong contract. Fix: correct the row.
- `stale-pointer`: a file or name a row or document points at was moved or deleted. Fix: the pointer.
- `hard`: the right route was followed and the change was still hard. Fix, if any: a smaller task or a refactor first.
- `no-advisor`: the agent had to escalate and could not invoke Claude Opus (a spawned agent has no Agent tool), so its hand-back was the escalation. Fix: a brief that names the limit, or a task sized to it.

`conflict` is not a kind. A conflict is not a red check but a clash of objectives between agents; it
has no retry and no count and goes to Ghost at once, in the journal and HANDOFF's "For Ghost"
(`docs/rules/conflict.md`, J-023). A count of three before Ghost hears would be the wrong rule there.

**Columns:** Date; Journal (the J-number); Task; Kind; Route taken (the routing row and what the agent
did); What was found (the cause, as the replay or the reviewer found it); Status. Status begins with
`open`, `fixed` (then what fixed it) or `Ghost` (then his date and resolution).

**The rule: three of a kind go to Ghost.** When three rows of one kind are `open`, the kind has no fix and
the routing is what is wrong. Put a numbered item in `docs/HANDOFF.md`'s "For Ghost: waiting on you"
that says "escalations" and names the kind in backticks, and keep it there until the rows are given a
`Ghost` status naming his resolution. A row marked `fixed` does not count. The check fails on three open
rows of one kind with no such item.

| Date | Journal | Task | Kind | Route taken | What was found | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-23 | J-032 | Step 1.7, the freeze: the full mutation check had grown past AGT's 10 minutes | no-advisor | The harness rows and `docs/rules/escalation.md`; 108 minutes and 120 tool calls of edits that could not fix it, then it found a spawned agent has no Agent tool and stopped | The whole-harness golden tests were rerun for every mutant of every module; no edit of the agent's could fix that. Review marked the three tests slow and exempted `goldens.compute` | fixed 2026-10-23: escalation.md makes a spawned agent's hand-back its escalation at once (J-032) |
