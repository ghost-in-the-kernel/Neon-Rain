# The agent's environment: its contract and its metrics

What an agent working in Neon Rain can count on, and the metrics the navigation tithe ratchets
(docs/ROADMAP.md §5, R-012). A metric may improve; it never regresses without a decision in
`theGhost.md`. `test/test_metrics.py` holds the table once `scripts/metrics.py` exists (phase 0.5);
until a metric is first measured within its target it is "not armed" and not compared.

## The contract

- **AGT-01 A clean clone installs from the lockfile and runs the fast loop with no data, no model
  and no network** beyond `pip`. Nothing a test needs is fetched.
- **AGT-02 The fast loop runs under 30 s.** Doc tests and unit tests only; the harness on the
  synthetic market is its own target with its own budget.
- **AGT-03 Mandatory context stays under 1,200 words.** `CLAUDE.md` plus whatever an agent must read
  before a task.
- **AGT-04 A routing row opens at most five files, none over 400 lines.**
- **AGT-05 Every generated artifact has a command that regenerates it and a test that fails when it
  is stale**: the feature table, the goldens, the metrics table. Two exceptions, R-019: the largest
  source file and docs per source line are re-recorded at tithe passes (`scripts/metrics.py
  --write`), and between them only their targets are held.
- **AGT-06 Every number carries its trials line and its dispersion** (P-07). An agent never reports a
  metric from a run that wrote no line.
- **AGT-07 The session is the machine.** There is no CI and no local run (R-003);
  `scripts/precommit.sh` is the gate and the agent runs it, every push, and quotes it.
- **AGT-08 Data and artifacts are fetched by hash**, never assumed present and never committed.

## The metrics

| Metric | Phase 0 target | Measured | Why it matters to the agent |
| --- | --- | --- | --- |
| Mandatory context (words) | < 1,200 | 1153 | every task pays it |
| Fast loop (s) | < 30 | 2.91 | run after every edit |
| Full check, `precommit.sh` (min) | < 10 | 0.82 | paid before every push while there is no CI |
| Largest source file (lines) | < 400 | 383 | fits a read without paging |
| Files a routing row opens | ≤ 5 | 3 | first five reads decide the task |
| Decisions without `See also` | 0 | 0 | links find what grep misses |
| Results without a trials line | 0 | 0 | P-07 |
| Results without dispersion | 0 | 0 | R-014 |
| Datasets without a manifest line | 0 | 0 | R-006 |
| Docs lines per source line | < 0.35 | 2.75 | Suite Builder reached 0.37 and it hurt |
