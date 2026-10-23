# Mutation: the surviving mutants, and why each is harmless

`scripts/precommit.sh` runs `mutmut` over `neonrain/` and `scripts/checks/` (`pyproject.toml`, R-015a). A mutant that survives — the code
was changed and every test still passed — means the tests do not hold that line. Each survivor gets
either a test that kills it, or one line here saying why it is harmless, and the push is refused
until it has one. Suite Builder does the same with Stryker.

A survivor in a file you did not touch is still yours: `scripts/precommit.sh` refuses the push for it all
the same, so kill it with a test or explain it here.

This file is the audit trail for a maintainer who does not read Python by eye: a short file means
the tests hold the code, and a long one means they do not.

| Id | File : line | The mutation | Why it is harmless | Date |
| --- | --- | --- | --- | --- |
| `scripts.checks.results.x_cell__mutmut_2` | scripts/checks/results.py : `cell` | joins matching cells with "XX XX" instead of " " | Equivalent under every reachable input: the patterns read from the joined text (a ± with [min, max], an NR-F-nn, a config hash) never span two cells, and no separator text can form one. | 2026-10-22 |
| `scripts.checks.glossary.x_uses__mutmut_6` | scripts/checks/glossary.py : `uses` | blanks a code span with "XX XX" instead of " " | Equivalent under every reachable input: the filler only has to keep the words on either side of a span apart, and "XX" is no enforced alias, so no filler text can form one. Revisit if an alias containing XX is ever enforced. | 2026-10-22 |
| `scripts.checks.supply_chain.x_import_problems__mutmut_37` | scripts/checks/supply_chain.py : `import_problems` | passes None instead of False as `is_scorer` | Equivalent under every reachable input: the flag is only read as `not is_scorer`, and `not None` is `not False`; the type hint says bool. | 2026-10-22 |
| `neonrain.harness.trials.x_config_hash__mutmut_30` | neonrain/harness/trials.py : `config_hash` | passes allow_nan=None instead of False to json.dumps | Equivalent under every reachable input: json.dumps reads the flag only as `not allow_nan`, and `not None` is `not False`, so NaN and infinity are still refused (tested). | 2026-10-23 |
| `neonrain.harness.goldens.x_dumped__mutmut_5` | neonrain/harness/goldens.py : `dumped` | passes allow_nan=None instead of False to json.dumps | Equivalent under every reachable input: json.dumps reads the flag only as `not allow_nan`, and `not None` is `not False`; the same mutant of `trials.config_hash` is explained above. | 2026-10-23 |
| `neonrain.harness.goldens.x_metric_values__mutmut_12` | neonrain/harness/goldens.py : `metric_values` | spells the excluded column "ic" as "XXicXX" in the name filter | Equivalent under every reachable input: a cell's `ic` is then listed among the scalar names, but the next line assigns `found["ic"]` again from the IC's mean, so the entry that stood there is replaced before anyone reads it. | 2026-10-23 |
| `neonrain.harness.goldens.x_metric_values__mutmut_13` | neonrain/harness/goldens.py : `metric_values` | spells the excluded column "ic" as "IC" in the name filter | Equivalent under every reachable input, for the reason of the mutant above: `found["ic"]` is assigned afterwards from the IC's mean. | 2026-10-23 |

## Exempt from mutation

Code marked `# pragma: no mutate start` … `end`, each region listed here with what holds it instead
(`test/test_mutation.py` refuses a pragma in a file not listed). Ghost's alone to grant.

| File | Region | What holds it instead | Granted |
| --- | --- | --- | --- |
| `neonrain/harness/goldens.py` | `compute` | It runs every harness module, so any test of it reruns for every mutant of every module (a 20-minute full check). Its output is the goldens, compared byte for byte by `test/test_the_freeze.py` (slow, before every push): a mutant that changes it fails there. | Ghost, 2026-10-23 (J-032) |

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
