# Escalation: a Claude Sonnet agent and a change that stays red (R-022)

Read this when you are a Claude Sonnet model and the fast loop, ruff or `scripts/precommit.sh` is red
after your first attempt at a code change. (Your system prompt names your model.)

- **A fix you can see, or an easy one, you make; no escalation.** That includes a red run whose
  output names the cause (a `NameError`, a typo, a rule the readability check quotes): fix that and
  run again.
- **Any other code change gets one attempt.** If it is still red and the output does not make the
  cause plain, do not try again. Invoke a Claude Opus instance (the Agent tool, model `opus`) with:
  the task, the routing row you started from, your diff, and the failing output. Continue from its
  answer; it advises, and you make the edits (one writer per working tree, `docs/rules/conflict.md`).
- **If you cannot invoke one** (an agent another agent spawned has no Agent tool), your hand-back is
  the escalation: stop, and report the task, your diff and the failing output to the agent that
  spawned you, which takes it to Claude Opus. Do not keep trying (J-032: one such agent spent 108
  minutes on a metric no edit of its could fix).
- **Name the escalation** in the journal entry (`docs/JOURNAL.md`).

Why: the cheaper model does the routine work; the costly failure is retrying a hard fix until
something passes for the wrong reason, which in this project is the failure the harness exists to
stop (theGhost.md R-022; J-019, J-022).
