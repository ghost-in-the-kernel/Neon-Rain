# Findings: what the data carries, what the harness caught, what did not work

Numbered NR-F-01 onward; a number is never reused. Each is written **before** any result that
depends on it is reported (P-03), and every row of `docs/RESULTS.md` cites the findings it carries.

| Id | Finding | Evidence | Qualifies |
| --- | --- | --- | --- |
| NR-F-01 | Reachability from the workspace (ROADMAP 0.3), measured 2026-10-22: see the table below. Every market-data and news host is refused from the shell; only GitHub (git and read-only REST) and PyPI are open. GitHub Releases, Git LFS uploads and REST writes are refused for this session type. Plain git blobs push. Changed 2026-10-24: Ghost allowed `data.nasdaq.com` and its S3 download host (J-042). | `scripts/probe/reachability.py`, J-004 | every fetch script; R-010 |
| NR-F-02 | HAR-02 drops a cell whose ticker has no price at *t+h*, and a ticker delisted inside the window has none: the windows in which names fall to delisting, the worst returns there are, are dropped from every label. The labels carry survivorship bias even on an honest universe, and the bias grows with the horizon (more windows cross a delisting at 63 days than at 3). The usual remedy takes the delisting price as the value at *t+h* (a delisting return). **Resolved 2026-10-23 by Ghost (J-024): the delisting price is the end value; `targets.py` builds it and counts `delisting_ends`.** Before that: the contract's author was to decide (J-014); until then `dropped_missing` at each horizon is reported beside every number, and 1.6's survivorship test must be read with it. The same hole would have leaked into the portfolio: scored on labelled rows only, it never held a name that delists in its hold (J-018); HAR-07 now scores the portfolio on every universe row, and `test/test_mirror.py` shows both. | `neonrain/targets.py`, `test/test_targets.py` (the delisted market), J-014 | HAR-02, 1.6, every result |
| NR-F-03 | WIKI has survivorship bias before 2014-04: not one of its 3,196 sample tickers has a last date before 2014-04-01, so for 1998 to 2013 every name that left the market before then is missing, and the share leaving is 0% a year against the few percent the market loses. From 2014-04 the loss is 3.2% (2014, nine months), 6.4%, 7.5% and 8.4% a year; 739 tickers (23%) have their last row inside the sample, all of them after 2014-03 (37 of them have rows again after 2017-12-29, so 702 are gone from the whole export). A universe built from it is the 2014 survivors looked at backwards, and a result for 1998 to 2013 carries that. | `scripts/probe/wiki_findings.py`, NR-F-03 below | NR-F-02 (no delisting end exists before 2014), every result on the sample |
| NR-F-04 | The feed stops adding names: first rows (tickers whose first date is in the year) run from 49 to 160 a year in 1999 to 2013, then 80, 12, 11 and 10 in 2014 to 2017. From 2014 the universe can only shrink, 2,872 tickers trading in 2016-01 to 2,473 in 2017-12, and a recent IPO is never in it. | `scripts/probe/wiki_findings.py`, NR-F-04 below | 2.1 membership, every result on 2014 onward |
| NR-F-05 | Ticker reuse is rare and cannot be told from a crash by price alone. A gap of 180 days or more inside one ticker's dates: 15 tickers (9 of them 365 days or more; the adjusted close moved 2x or more across the gap for 7). A one-row adjusted-close jump of 4x or more with no gap: 168 events in 90 tickers, which is mostly crashes and unrecorded splits. Candidates for inspection, either test: 98 of 3,196 tickers (3%). None is merged or split here. | `scripts/probe/wiki_findings.py`, NR-F-05 below | 2.1 membership; 2.2 returns across a gap |
| NR-F-06 | WIKI does not mark a delisting. The fourteen columns hold no flag, and no row exists after a ticker's last date. The last row of a ticker that leaves is only a little unusual: zero volume 2.6% (all rows 1.3%), the close equal to the day before 17.6% (4.3%), a close under 1 dollar 10.4% (1.6%). A last row says neither why a name left (merger, bankruptcy, a move) nor whether the feed merely stopped covering it. | `scripts/probe/wiki_findings.py`, NR-F-06 below | NR-F-02: the delisting price is the last close, which may not be a price anyone could trade at |
| NR-F-07 | The feed decays at its end, but not in the ticker count. Corporate actions stop first: the first session with no rows at all is 2017-11-08, dividends are missing on 8 of the 14 sessions of 2017-11-10 to 2017-11-30 and then end after 2017-12-05, splits end after 2017-11-28, and nothing is recorded in 2018-01 or 2018-02 (a burst of 59 dividend rows and 2 splits on 2018-03-01 to 07 follows). The adjusted columns after about 2017-11-07 do not carry the actions of those weeks. The ticker count falls steadily, 2,872 (2016-01) to 2,473 (2017-12), 2,444 (2018-02), with no cliff. 2017-12-29 is not the right last date; 2017-11-07 was proposed (below). **Resolved 2026-10-24 by Ghost (R-026): the sample ends 2017-11-07, the proposed date.** | `scripts/probe/wiki_findings.py`, NR-F-07 below | TODO phase 2 (the sample's end), 2.2 |
| NR-F-08 | WIKI and the calendar disagree in two ways inside the sample: 120 WIKI dates are no session of the calendar (all weekdays, none a weekend; 165 rows on them, at most 9 rows on one date, usually 1), and 1 session has no rows at all (2017-11-08). Counted only; 2.2 decides what to do. | `scripts/probe/wiki_findings.py`, NR-F-08 below | 2.2 |

## NR-F-03 to NR-F-08: WIKI membership, 2026-10-24 (TODO 2.1 b)

Measured on the sample as first planned (R-026 later ended it at 2017-11-07; these counts are of the earlier sample) (1998-01-02 to 2017-12-29: 12,051,622 rows, 3,196 tickers, 5,151 dates) and, for the end of the
feed, on the whole export (15,389,314 rows, 3,199 tickers, 1962-01-02 to 2018-03-27). Only counts, shares and dates are
written here (R-006). `python scripts/probe/wiki_findings.py <data clone>/wiki/prices <export CSV>` prints every table.
A ticker "leaves" when its last row is before 2017-12-29; a year's share is the leavers whose last row is in the year over
the tickers with a row in it.

**NR-F-03 and NR-F-04, by year.** Tickers trading, leaving, share leaving, first rows:

| Year | Trading | Left | % left | First rows | Year | Trading | Left | % left | First rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1998 | 1,673 | 0 | 0.00 | 1,673 (the start) | 2008 | 2,544 | 0 | 0.00 | 55 |
| 1999 | 1,803 | 0 | 0.00 | 130 | 2009 | 2,596 | 0 | 0.00 | 52 |
| 2000 | 1,892 | 0 | 0.00 | 89 | 2010 | 2,709 | 0 | 0.00 | 113 |
| 2001 | 1,941 | 0 | 0.00 | 49 | 2011 | 2,804 | 0 | 0.00 | 95 |
| 2002 | 1,995 | 0 | 0.00 | 54 | 2012 | 2,923 | 0 | 0.00 | 119 |
| 2003 | 2,055 | 0 | 0.00 | 60 | 2013 | 3,083 | 0 | 0.00 | 160 |
| 2004 | 2,153 | 0 | 0.00 | 98 | 2014 | 3,163 | 102 | 3.22 | 80 |
| 2005 | 2,268 | 0 | 0.00 | 115 | 2015 | 3,073 | 196 | 6.38 | 12 |
| 2006 | 2,362 | 0 | 0.00 | 94 | 2016 | 2,883 | 217 | 7.53 | 11 |
| 2007 | 2,489 | 0 | 0.00 | 127 | 2017 | 2,681 | 224 | 8.36 | 10 |

The earliest last date of any ticker is 2014-04-01 (13 tickers in 2014-04, 7 in 2014-05, 10 in 2014-06), in the sample and in
the whole export alike. Over the sample the pooled share is 1.5% a year, and 0% in 16 of its 20 years. Of the 3,196
tickers 2,457 have a row on 2017-12-29; 37 of the other 739 return after it, and for most of them (the median and both quartiles) the last in-sample row is
248 days before the sample's end: one batch, not 37 stories. In all 2,491 tickers of the sample have a row after 2017-12-29. Of the 2,259 names that ever enter the
universe (below) 493 leave, none of them before 2014-04. What this does to a model: for 1998 to 2013 the universe never loses
a name, so no label sees a delisting, and the survivors' returns are the ones taught. Whether to start the sample in 2014-04
instead, or to carry the bias as a finding beside every number, is Ghost's.

**The universe, by `neonrain/universe/membership.py`.** On the sample with the calendar's sessions, 1,000 names a day from
1998-04-02 (63 sessions after the first row) to 2017-12-29: 4,969 dates, 4,969,000 rows, 2,259 distinct names. The one session with no prices
(2017-11-08) has no universe row. The rule that a name needs all 63 sessions of the window is not sensitive: asking 60 of 63
keeps 99.88% of the rows (the new set is 99.82% the old); asking 42 of 63 keeps 99.70%.

**NR-F-05, how the reuse is looked for.** From each ticker's own consecutive rows: the calendar days between them, and the
ratio of adjusted closes. A gap of 180 days or more is a ticker that went away and came back; 15 events in 15 tickers,
largest gap 952 days, 9 of 365 days or more, 7 with the adjusted close moved 2x or more across it. A 4x move
in one row (up, or down to a quarter) with no gap: 168 events in 90 tickers; at 3x, 290 events in 149 tickers; at 10x, 43
events in 29. Raw closes with no split recorded give the same count (166 events at 4x), so the jumps are mostly real crashes and
splits the feed did not record, not new companies. Reuse proper (a different company under an old symbol) is the gap
cases at most, 15 tickers, 0.5% of the sample; the 98 candidates are not read one by one here.

**NR-F-06.** Compared the last row of the 739 leavers with all rows (table in the finding). Splits recorded on the
last row: none; dividends 0.14% against 0.78%. The median last close of a leaver is 20 dollars (10th percentile 0.92, 90th 79)
so most leave at a real price, a merger or a move more than a failure.

**NR-F-07, tickers trading per month and the corporate actions** (whole export; dividends = rows with a non-zero
`ex-dividend`, splits = rows with `split_ratio` not 1):

| Month | Tickers | Dividends | Splits | Month | Tickers | Dividends | Splits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2016-01 | 2,872 | 246 | 2 | 2017-03 | 2,633 | 667 | 7 |
| 2016-02 | 2,844 | 573 | 5 | 2017-04 | 2,615 | 237 | 8 |
| 2016-03 | 2,827 | 695 | 3 | 2017-05 | 2,575 | 615 | 6 |
| 2016-04 | 2,816 | 256 | 1 | 2017-06 | 2,559 | 576 | 9 |
| 2016-05 | 2,796 | 620 | 10 | 2017-07 | 2,546 | 230 | 2 |
| 2016-06 | 2,782 | 628 | 9 | 2017-08 | 2,535 | 616 | 3 |
| 2016-07 | 2,760 | 254 | 6 | 2017-09 | 2,519 | 515 | 4 |
| 2016-08 | 2,746 | 665 | 6 | 2017-10 | 2,500 | 245 | 5 |
| 2016-09 | 2,729 | 542 | 8 | 2017-11 | 2,486 | 258 | 8 |
| 2016-10 | 2,708 | 261 | 10 | 2017-12 | 2,473 | 21 | 0 |
| 2016-11 | 2,696 | 674 | 8 | 2018-01 | 2,454 | 0 | 0 |
| 2016-12 | 2,676 | 572 | 7 | 2018-02 | 2,444 | 0 | 0 |
| 2017-01 | 2,660 | 228 | 7 | 2018-03 (to 03-27) | 2,471 | 59 | 2 |
| 2017-02 | 2,650 | 547 | 3 | | | | |

Dividends run in a three-month cycle (about 230 to 260 in January, April, July, October; 515 to 695 in the other months).
2017-10 (245) is whole; 2017-11 (258 against 674 a year before) is not; 2017-12 (21 against 572) and 2018-01, 2018-02 (0) are
not. By day: 2017-11-08 has no rows at all; from 2017-11-10 to 2017-11-30 dividends are zero on 8 of 14 sessions (11-10, 13, 14,
16, 22, 24, 29, 30); the last dividend day before 2018 is 2017-12-05 (21 rows), and the last split day is 2017-11-28. Share of rows whose adjusted close equals the raw close, 0.84 in mid-October 2017 to
1.00 from 2017-12-05, as it must when no later action is recorded. The ticker count, in contrast, has no cliff: it
falls 10 to 20 a month the whole time (NR-F-04). The proposal: end the sample at **2017-11-07**, the last session before the
first hole (the plan's 2017-12-29 stood until Ghost moved it, R-026); 2017-10-31, the last whole month, is the cautious
alternative. Cost of either: about 36 sessions of the sample's 5,031 (2017-11-07), or 41 (2017-10-31). Unrecorded
splits in the last weeks would be returns of -50% or worse that no ticker had; raw closes show 2 to 4 drops of 45% or
more with no split recorded in each of 2017-12 to 2018-02, inside the 0 to 12 a month before, so no burst is seen, but the
adjusted history before a missed action is wrong by its factor.

**NR-F-08.** The 120 dates are weekdays of the calendar's closures (holidays whose rule holds, 2001-09-11 to 09-14 among them):
WIKI carries a stray row on a day the exchange was shut, mostly one ticker, never a market-wide set. Dates with prices 5,151,
sessions 5,032 to 2017-12-29, so 5,151 - 120 = 5,031 sessions with prices and one with none.

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
