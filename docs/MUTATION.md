# Mutation: the surviving mutants, and why each is harmless

`scripts/precommit.sh` runs `mutmut` over `neonrain/` and `scripts/checks/` (`pyproject.toml`, R-015a). A mutant that survives — the code
was changed and every test still passed — means the tests do not hold that line. Each survivor gets
either a test that kills it, or one line here saying why it is harmless, and the push is refused
until it has one. Suite Builder does the same with Stryker.

mutmut runs only the tests that reached the mutated function (its stats run), cheapest first
(`test/conftest.py`, R-024); the gate clears `mutants/` first because mutmut keeps a cached verdict
when only the tests change. A slow check is a dear test reached by many mutants, not selection.

What the full check costs, and the knobs (R-024 c): a mutant is one `pytest.main` in a fork of a warmed process,
so a per-run cost is paid 3,896 times. `test/conftest.py` freezes the warmed heap (`gc.freeze()`) at the start of a
run under mutmut, because pytest's unraisable-exception plugin calls `gc.collect()` twice per run and each call walked
that heap for about 85 ms. `mutmut run "<module>.*"` runs one module's mutants in seconds, and
`mutmut results | grep <module>` lists its survivors. Two more costs taken out of the run (J-053): `test/conftest.py` asks
`importlib.metadata` for the installed packages once, at import, so the warm-up pays the 0.2 s walk and no forked mutant does
(it was the cost of every `supply_chain` mutant); and `pytest_add_cli_args = ["-p", "no:cacheprovider"]` leaves the cache
plugin off, since it wrote `.pytest_cache` in every failing run. A function a test file wraps in a cache must not be one
under `source_paths`, or a mutant of it would be answered from the cache. To show a survivor equivalent, brute-force the mutated line over
the function's stated domain and quote the range checked in its row. A new top-level folder the tests import (as
`scripts/probe/` and `scripts/fetch/`) must be added to `also_copy` in `pyproject.toml`.

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

| `neonrain.universe.calendar.x_easter__mutmut_16` | neonrain/universe/calendar.py : `easter` | adds 9 instead of 8 to the century in the Gregorian correction `g` | Equivalent under every reachable input: `g` differs only when the century is 16 (or 41), where `h = (b - g + 1) // 3` is 5 either way; checked for every year from 1583 to 9999, and the sessions only ask for years from 1998. | 2026-10-24 |
| `neonrain.universe.calendar.x_easter__mutmut_26` | neonrain/universe/calendar.py : `easter` | subtracts 15 instead of adding it before `% 30` | Equivalent under every reachable input: -15 and +15 are the same residue mod 30. | 2026-10-24 |
| `neonrain.universe.calendar.x_easter__mutmut_59` | neonrain/universe/calendar.py : `easter` | divides by 452 instead of 451 in the correction `n` | Equivalent for every year below 3165 (checked from 1583 by brute force, and the first year it differs is 3165); the module claims years from 1998 and the tests cross-check 1583 to 2600 against Oudin's algorithm. | 2026-10-24 |
| `neonrain.universe.calendar.x_easter__mutmut_66` | neonrain/universe/calendar.py : `easter` | subtracts 8 * n instead of 7 * n in the month only | Equivalent under every reachable input: when `n` is 1 the sum is far enough from a multiple of 31 that the month is the same; checked for every year from 1583 to 9999 (the day keeps 7 * n and is tested). | 2026-10-24 |
| `neonrain.universe.calendar.x_sessions__mutmut_11` | neonrain/universe/calendar.py : `sessions` | collects the closures of one year past `last_year` | Equivalent under every reachable input: those dates are after the last day of the span, which is never listed, so a closure there removes nothing. | 2026-10-24 |
| `neonrain.universe.membership.x_universe__mutmut_16` | neonrain/universe/membership.py : `universe` | sorts the dates descending instead of ascending before the per-date cut | Equivalent under every reachable input: the cut takes the first rows of each date's own group, whose order is by median and ticker alone, and the result is sorted by date and ticker at the end. | 2026-10-24 |
| `neonrain.universe.membership.x_universe__mutmut_31` | neonrain/universe/membership.py : `universe` | leaves `maintain_order` at its default in the grouping | Equivalent under every reachable input: the groups may come in any order, rows keep their order inside a group, and the result is sorted by date and ticker at the end. | 2026-10-24 |
| `neonrain.universe.membership.x_universe__mutmut_34` | neonrain/universe/membership.py : `universe` | passes `maintain_order=False` to the grouping | Equivalent under every reachable input: the same as the mutant above (groups in any order, the final sort restores the order). | 2026-10-24 |

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
| `neonrain.universe.prices.x_load__mutmut_45` | neonrain/universe/prices.py : `load` | `first < day` instead of `first <= day` in the empty-session test | Equivalent under every reachable input: `first` is the smallest date with a row, so it is in `seen` and `day not in seen` is already false for it. | 2026-10-25 |
| `neonrain.universe.prices.x_load__mutmut_46` | neonrain/universe/prices.py : `load` | `day < last` instead of `day <= last` in the empty-session test | Equivalent under every reachable input: `last` is the largest date with a row, so it is in `seen` and `day not in seen` is already false for it. | 2026-10-25 |
