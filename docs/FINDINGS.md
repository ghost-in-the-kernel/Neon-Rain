# Findings: what the data carries, what the harness caught, what did not work

Numbered NR-F-01 onward; a number is never reused. Each is written **before** any result that
depends on it is reported (P-03), and every row of `docs/RESULTS.md` cites the findings it carries.

| Id | Finding | Evidence | Qualifies |
| --- | --- | --- | --- |
| NR-F-01 | Reachability from the workspace (ROADMAP 0.3), measured 2026-10-22: see the table below. Every market-data and news host is refused from the shell; only GitHub (git and read-only REST) and PyPI are open. GitHub Releases, Git LFS uploads and REST writes are refused for this session type. Plain git blobs push. | `scripts/probe/reachability.py`, J-004 | every fetch script; R-010 |
| NR-F-02 | HAR-02 drops a cell whose ticker has no price at *t+h*, and a ticker delisted inside the window has none: the windows in which names fall to delisting, the worst returns there are, are dropped from every label. The labels carry survivorship bias even on an honest universe, and the bias grows with the horizon (more windows cross a delisting at 63 days than at 3). The usual remedy takes the delisting price as the value at *t+h* (a delisting return). Open: the contract's author decides (J-014); until then `dropped_missing` at each horizon is reported beside every number, and 1.6's survivorship test must be read with it. The same hole would have leaked into the portfolio: scored on labelled rows only, it never held a name that delists in its hold (J-018); HAR-07 now scores the portfolio on every universe row, and `test/test_mirror.py` shows both. | `neonrain/targets.py`, `test/test_targets.py` (the delisted market), J-014 | HAR-02, 1.6, every result |

## NR-F-01: reachability, 2026-10-22

Measured from the cloud workspace's shell with one small GET per host (`scripts/probe/reachability.py`,
run with `python3 -I`). "Refused" is the proxy's `403 Forbidden` on the tunnel: the host is on no
allowlist, and no client or retry changes that.

| Host | Purpose | Result |
| --- | --- | --- |
| PyPI | packages | reachable |
| GitHub (git clone, fetch, push) | the repository | reachable |
| GitHub REST API, reads | repository metadata | reachable |
| GitHub REST API, writes (branch delete, releases) | artifact store | **refused** for this session type |
| GitHub Releases (`gh release create`) | artifact store candidate | **refused** (HTTP 403, "not permitted for this session type") |
| Git LFS upload (`github-cloud.s3.amazonaws.com`) | artifact store candidate | **refused** (Forbidden on the object PUT; the pointer commit went through) |
| Plain git blob, 1 MB, scratch branch | artifact store candidate | **pushed** (branch `probe-plain`, left for Ghost to delete: the proxy refuses branch deletion) |
| Stooq daily CSV | prices | refused |
| Yahoo Finance chart API | prices | refused |
| Tiingo | prices | refused |
| Polygon | prices | refused |
| Alpha Vantage | prices | refused |
| FRED | rates | refused |
| SEC EDGAR | filings | refused |
| GDELT doc API | news | refused |
| Hugging Face Hub (FNSPID dataset) | news, artifact store candidate | refused; **reachable** from a later session the same day (below) |
| Kaggle | datasets | refused |
| Claude's web-fetch tool (outside the shell) | small text pages | needs Ghost to paste each URL into the chat; not a route for bulk data |
| Ghost's own computer, through the desktop-app bridge | staging files into the workspace | available when his machine is on and the app open; his machine is unstable (R-003) |

What this means for the plan (decided as R-016):

- **Data arrives by hand, not by script.** Ghost downloads a dataset on his machine and either
  pushes it to a separate data repository on GitHub (plain git, under 100 MB per file, chunked
  parquet if larger) or stages it through the desktop-app bridge when his machine is up. The
  "fetch script" of R-006 becomes a *verify* script: it checks the manifest hash of what Ghost
  supplied. The manifest still records source and license.
- **The artifact store is a second GitHub repository holding plain git blobs** (R-010): weights,
  ledger snapshots and feature caches, each under 100 MB, chunked and content-addressed, with the
  main repository recording hashes. A GitHub Release would have been cleaner and is refused.
- **The scorer's news feed is the one piece that must be fetched live**, and it cannot be fetched
  from here. Phase 5 depends on a news dataset with publish timestamps that Ghost obtains (FNSPID
  on Hugging Face is the leading candidate) and supplies as above, or on a scheduled task that runs
  somewhere with network access. Until that is settled, phase 5 is blocked and phases 1–4 are not.

### Re-measured, 2026-10-22, a later session (J-008)

The same probe, unchanged in what it fetches, from a different cloud session: the price, rates,
filings and news hosts and Kaggle are still refused, and **the Hugging Face Hub is reachable** (the
dataset API, and `resolve/main/README.md` from the FNSPID repository). Reachability is a property of
the session's network policy, not of the project: two sessions on one day disagreed. What was read,
and nothing more: FNSPID's card says CC BY-NC 4.0 (non-commercial; see R-011), and its news files
are `Stock_news/All_external.csv` (5.7 GB) and `Stock_news/nasdaq_exteral_data.csv` (23 GB), with
prices in `Stock_price/full_history.zip`. Each is far past this session's disk and R-016's 100 MB
per git file, so nothing was downloaded and R-016's route is unchanged until Ghost decides
otherwise.
