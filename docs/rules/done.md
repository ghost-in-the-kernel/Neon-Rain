# Done: before you hand back or commit (R-029)

Read this when you think your work is done, before you hand back or commit. It is the checklist that
CLAUDE.md used to carry inline (Ghost, 2026-10-26).

The fast loop always; `scripts/precommit.sh` before a push. A refactor changes no golden (P-02). A
number without a trials line and a dispersion does not exist (P-07). A bias or a leak is a finding
before it is a footnote (P-03). A function that holds a decision cites it, `# Decision: R-005`. Every
eighth commit is a tithe (R-012). A finished step is merged to `main` at once. A new task goes to a
fresh Claude Sonnet agent, reviewed before it is pushed (J-027).

Three rules an agent meets only by running the loops (J-057), so they are here, where the loop is
run: (a) no function takes `*args` or `**kwargs` (`scripts/checks/readability.py`); (b) no string in
`neonrain/features/` contains the word "ledger", docstrings included (MOD-04, `scripts/checks/modules.py`);
(c) CLAUDE.md's "Files a routing row opens" metric counts every backticked name in a Start-here cell,
and a folder as its files, so a row stays at five or fewer.
