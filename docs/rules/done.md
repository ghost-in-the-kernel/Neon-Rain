# Done: before you hand back or commit (R-029)

Read this when you think your work is done, before you hand back or commit. It is the checklist that
CLAUDE.md used to carry inline (Ghost, 2026-10-26).

The fast loop always; `scripts/precommit.sh` before a push. A refactor changes no golden (P-02). A
number without a trials line and a dispersion does not exist (P-07). A bias or a leak is a finding
before it is a footnote (P-03). A function that holds a decision cites it, `# Decision: R-005`. Every
eighth commit is a tithe (R-012). A finished step is merged to `main` at once. A new task goes to a
fresh Claude Sonnet agent, reviewed before it is pushed (J-027).

Four rules an agent meets only by running the loops (J-057), so they are here, where the loop is
run: (a) no function takes `*args` or `**kwargs` (`scripts/checks/readability.py`); (b) no string in
`neonrain/features/` contains the word "ledger", docstrings included (MOD-04, `scripts/checks/modules.py`);
(c) CLAUDE.md's "Files a routing row opens" metric counts every backticked path in a Start-here cell (a name with a slash or a dot, or one that exists in the repository; a bare word such as a key opens nothing), and a folder as its files, so a row stays at five or fewer; (d) ruff's ANN rules want type hints on every function,
test functions included (`def test_x() -> None:`).

Four traps of phase 3, met by agents running the gate (J-072, J-074, J-076): (e) a test module computes nothing at
import (no synthetic market, scores or labels at module level): build it in a `@pytest.fixture(scope="module")`, since
mutmut sets each mutant's CPU limit from test times, which leave out import, and a market built at import stalled the
gate for hours (exit -24, J-074); (f) a new or changed test file is measured with `.venv/bin/pytest <file>
--durations=0` before it is handed back, and its cost is said; (g) a process is stopped by its PID, never by a
pattern (`pkill -f` matches the shell that runs it), and only one you started. The gate's line is found with
`grep "^precommit:"`, never by the file's last line. (h) The scratchpad is shared across sessions and holds
earlier sessions' files: a wait loop on a `.done` file of an old name returns at once (J-076), so wait on a fresh name.

An open question your work leaves, one a later item depends on (a contract not precise enough, a choice
Ghost has not made), is written into that TODO item, its plan or its check, as well as the journal, so
the agent who takes the item finds it there and not only in a journal entry (Ghost, 2026-10-27, J-066).
