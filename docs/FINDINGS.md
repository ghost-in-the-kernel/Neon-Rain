# Findings: what the data carries, what the harness caught, what did not work

Numbered NR-F-01 onward; a number is never reused. Each is written **before** any result that
depends on it is reported (P-03), and every row of `docs/RESULTS.md` cites the findings it carries.

| Id | Finding | Evidence | Qualifies |
| --- | --- | --- | --- |
| NR-F-01 | Reachability from the workspace: which data sources, news sources and artifact stores the session's network allows (ROADMAP 0.3) | *to be measured* | every fetch script |
