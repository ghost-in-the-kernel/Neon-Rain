# Conflict: another agent's work against yours (J-023)

Read this when another agent's work breaks yours, contradicts your task, or keeps changing what you
just changed.

1. **Stop at once.** There is no retry and no count.
2. **Assume a conflict of objectives, never sabotage.** From inside one agent's view the two look
   the same; only Ghost can tell them apart.
3. **Write it down:** a journal entry of class `conflict` (`docs/JOURNAL.md`) with **Mine** and
   **Theirs**, each objective stated plainly as you understand it, with no guess at intent.
4. **List it** under `docs/HANDOFF.md`'s "For Ghost", and ask Ghost to resolve it. It stays listed
   until its **Resolved** line names Ghost (`test/test_journal.py` holds this).
5. **Never touch what you did not start:** never kill or stop a process another agent or person
   started; never revert, force-push over or rewrite another agent's commit; never edit the journal
   or `theGhost.md` to get around a conflict.

One writer per working tree: an agent you invoke to advise (an escalation, a reviewer) reads; you edit.

Why: J-023, after three agents with conflicting objectives overwrote each other's work and ran kill
scripts against each other, each assuming sabotage, and none told the human who could have
deconflicted them.
