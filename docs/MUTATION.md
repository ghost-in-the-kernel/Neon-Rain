# Mutation: the surviving mutants, and why each is harmless

`scripts/precommit.sh` runs `mutmut` over `neonrain/` (R-015a). A mutant that survives — the code
was changed and every test still passed — means the tests do not hold that line. Each survivor gets
either a test that kills it, or one line here saying why it is harmless, and the push is refused
until it has one. Suite Builder does the same with Stryker.

This file is the audit trail for a maintainer who does not read Python by eye: a short file means
the tests hold the code, and a long one means they do not.

| Id | File : line | The mutation | Why it is harmless | Date |
| --- | --- | --- | --- | --- |
| `scripts.checks.results.x_cell__mutmut_2` | scripts/checks/results.py : `cell` | joins matching cells with "XX XX" instead of " " | Equivalent under every reachable input: the patterns read from the joined text (a ± with [min, max], an NR-F-nn, a config hash) never span two cells, and no separator text can form one. | 2026-10-22 |
| `scripts.checks.glossary.x_uses__mutmut_6` | scripts/checks/glossary.py : `uses` | blanks a code span with "XX XX" instead of " " | Equivalent under every reachable input: the filler only has to keep the words on either side of a span apart, and "XX" is no enforced alias, so no filler text can form one. Revisit if an alias containing XX is ever enforced. | 2026-10-22 |
| `scripts.checks.supply_chain.x_import_problems__mutmut_37` | scripts/checks/supply_chain.py : `import_problems` | passes None instead of False as `is_scorer` | Equivalent under every reachable input: the flag is only read as `not is_scorer`, and `not None` is `not False`; the type hint says bool. | 2026-10-22 |

## What counts as harmless

Only these. Anything else gets a test.

- **Equivalent under every reachable input**: the mutated line computes the same thing for every
  value the function can be called with, and a type hint or a validated precondition proves it.
- **Unreachable defensive code**: a branch kept for a failure the system is built to prevent, with
  the invariant that prevents it named. (These are suspicious: if it cannot happen, consider
  deleting it; if it can, write the test.)
- **Logging, formatting or a message string** with no effect on a number or a control decision.
  A mutation to a *reported* number is never harmless — those are the project's output.

A performance-only difference is not harmless; it is untested behaviour with a plausible excuse.
