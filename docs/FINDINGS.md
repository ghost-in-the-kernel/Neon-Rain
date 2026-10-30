# Findings: what the data carries, what the harness caught, what did not work

Numbered NR-F-01 onward; a number is never reused. (The `F-01` to `F-08` of `docs/ROADMAP.md` §1 are another series: facts the plan stands on, from the literature or measured before the build; these NR-F entries are what this project's own data and harness showed.) Each is written **before** any result that
depends on it is reported (P-03), and every row of `docs/RESULTS.md` cites the findings it carries.

| Id | Finding | Evidence | Qualifies |
| --- | --- | --- | --- |
| NR-F-01 | Reachability from the workspace (ROADMAP 0.3), measured 2026-10-22: see the table below. Every market-data and news host is refused from the shell; only GitHub (git and read-only REST) and PyPI are open. GitHub Releases, Git LFS uploads and REST writes are refused for this session type. Plain git blobs push. Changed 2026-10-24: Ghost allowed `data.nasdaq.com` and its S3 download host (J-042). | `scripts/probe/reachability.py`, J-004 | every fetch script; R-010 |
| NR-F-02 | HAR-02 drops a cell whose ticker has no price at *t+h*, and a ticker delisted inside the window has none: the windows in which names fall to delisting, the worst returns there are, are dropped from every label. The labels carry survivorship bias even on an honest universe, and the bias grows with the horizon (more windows cross a delisting at 63 days than at 3). The usual remedy takes the delisting price as the value at *t+h* (a delisting return). **Resolved 2026-10-23 by Ghost (J-024): the delisting price is the end value; `targets.py` builds it and counts `delisting_ends`.** Before that: the contract's author was to decide (J-014); until then `dropped_missing` at each horizon is reported beside every number, and 1.6's survivorship test must be read with it. The same hole would have leaked into the portfolio: scored on labelled rows only, it never held a name that delists in its hold (J-018); HAR-07 now scores the portfolio on every universe row, and `test/test_mirror.py` shows both. | `neonrain/targets.py`, `test/test_targets.py` (the delisted market), J-014 | HAR-02, 1.6, every result |
| NR-F-03 | WIKI has survivorship bias before 2014-04: not one of its 3,196 sample tickers has a last date before 2014-04-01, so for 1998 to 2013 every name that left the market before then is missing, and the share leaving is 0% a year against the few percent the market loses. From 2014-04 the loss is 3.2% (2014, nine months), 6.4%, 7.5% and 8.4% a year; 739 tickers (23%) have their last row inside the sample, all of them after 2014-03 (37 of them have rows again after 2017-12-29, so 702 are gone from the whole export). A universe built from it is the 2014 survivors looked at backwards, and a result for 1998 to 2013 carries that. | `scripts/probe/wiki_findings.py`, NR-F-03 below | NR-F-02 (no delisting end exists before 2014), every result on the sample |
| NR-F-04 | The feed stops adding names: first rows (tickers whose first date is in the year) run from 49 to 160 a year in 1999 to 2013, then 80, 12, 11 and 10 in 2014 to 2017. From 2014 the universe can only shrink, 2,872 tickers trading in 2016-01 to 2,473 in 2017-12, and a recent IPO is never in it. | `scripts/probe/wiki_findings.py`, NR-F-04 below | 2.1 membership, every result on 2014 onward |
| NR-F-05 | Ticker reuse is rare and cannot be told from a crash by price alone. A gap of 180 days or more inside one ticker's dates: 15 tickers (9 of them 365 days or more; the adjusted close moved 2x or more across the gap for 7). A one-row adjusted-close jump of 4x or more with no gap: 168 events in 90 tickers, which is mostly crashes and unrecorded splits. Candidates for inspection, either test: 98 of 3,196 tickers (3%). None is merged or split here, and none is dropped: the 2.2 loader keeps every row of every ticker as the export gives it, a reused ticker one ticker, so a return across a gap is still a return (and a candidate); the unit test shows a gapped ticker kept whole. | `scripts/probe/wiki_findings.py`, NR-F-05 below | 2.1 membership; 2.2 returns across a gap |
| NR-F-06 | WIKI does not mark a delisting. The fourteen columns hold no flag, and no row exists after a ticker's last date. The last row of a ticker that leaves is only a little unusual: zero volume 2.6% (all rows 1.3%), the close equal to the day before 17.6% (4.3%), a close under 1 dollar 10.4% (1.6%). A last row says neither why a name left (merger, bankruptcy, a move) nor whether the feed merely stopped covering it. | `scripts/probe/wiki_findings.py`, NR-F-06 below | NR-F-02: the delisting price is the last close, which may not be a price anyone could trade at |
| NR-F-07 | The feed decays at its end, but not in the ticker count. Corporate actions stop first: the first session with no rows at all is 2017-11-08, dividends are missing on 8 of the 14 sessions of 2017-11-10 to 2017-11-30 and then end after 2017-12-05, splits end after 2017-11-28, and nothing is recorded in 2018-01 or 2018-02 (a burst of 59 dividend rows and 2 splits on 2018-03-01 to 07 follows). The adjusted columns after about 2017-11-07 do not carry the actions of those weeks. The ticker count falls steadily, 2,872 (2016-01) to 2,473 (2017-12), 2,444 (2018-02), with no cliff. 2017-12-29 is not the right last date; 2017-11-07 was proposed (below). **Resolved 2026-10-24 by Ghost (R-026): the sample ends 2017-11-07, the proposed date.** | `scripts/probe/wiki_findings.py`, NR-F-07 below | TODO phase 2 (the sample's end), 2.2 |
| NR-F-08 | WIKI and the calendar disagree in two ways inside the sample: 120 WIKI dates are no session of the calendar (all weekdays, none a weekend; 165 rows on them, at most 9 rows on one date, usually 1), and 1 session has no rows at all (2017-11-08). **Decided in 2.2:** the frame holds only session dates, because `check_market` refuses a price row off the calendar; the 165 rows on the 120 dates (24 tickers, none a weekend) are left out of it and handed back in `Loaded.off_calendar`, counted by `scripts/probe/wiki_prices.py`. On the sample ending 2017-11-07 no session has no rows (2017-11-08 is outside it), and `Loaded.empty_sessions` reports any that would be. | `scripts/probe/wiki_findings.py`, NR-F-08 below | 2.2 |
| NR-F-09 | A survivor-only sample flatters a price-pattern strategy by a small amount that has a sign: on the synthetic market (160 tickers, 1,200 sessions, 21% of names delisted, no reversal or momentum planted) taking the delisted names out makes **short-term reversal** look better (long-short Sharpe at 10 bps +0.12 to +0.22, DSR +0.01 to +0.04, IC +0.001 to +0.007), **momentum** look worse (Sharpe -0.11 to -0.14, DSR -0.02 to -0.03, IC -0.004 to -0.023) and a **random** score look the same (every difference inside its seed spread). No scorer here has an edge, so every such difference is bias. It is a fraction of one annualized Sharpe unit, smaller than the cost drag at 3 and 5 days, and measured on synthetic delistings only. Table and reading below. | `scripts/probe/survivorship.py`, `test/test_survivorship_probe.py`, NR-F-09 below | R-026 (b) and (c); NR-F-02, NR-F-03; every result on WIKI before 2014-04-01 |
| NR-F-10 | The zero baseline's portfolio is the tie-break's book, not a null. A constant score ties at every cell, HAR-07 breaks ties by ticker, so the portfolio trades an alphabetical book; its 0 bps Sharpe (about -0.07) is noise, and its after-cost Sharpe is the harness's turnover floor, about 1/h in scale (10 bps, survivor-only / from 2014: h3 -3.32 / -3.71, h5 -2.02 / -2.09, h21 -0.53 / -0.59, h63 -0.20 / -0.36). Reported as the harness computes it (Fable, 2026-10-28). Possible harness v2, not done now, for Ghost: a date whose scores are all equal opens no sleeve. | `harness/trials.tsv` (the zero baseline's lines), `neonrain/baselines/zero.py`, NR-F-10 below | 3.1 (a); the cost floor every later baseline and the network is read against |
| NR-F-11 | The baselines' edge is not concentrated at short horizons, against ROADMAP 3.3's expectation (written before any run: near chance at three months, a small edge at short horizons). The tree's accuracy (0.504 to 0.510) and IC (+0.014 to +0.032) are positive at every horizon in both periods, and its IC at 63 days (+0.022 survivor-only / +0.027 from 2014, not marked *fits names*) is no smaller than at 3 days (+0.032 / +0.025). The signals' edge depends on the period instead: reversal's IC is +0.009 to +0.013 survivor-only and -0.009 to -0.025 from 2014; momentum's +0.014 to -0.002 and -0.019 to +0.009. The costs half held: at 3 and 5 days every baseline's mean Sharpe at 10 bps is negative in both periods. The means that stay positive at 10 bps are at 21 and 63 days, the end where near-chance was expected, and all but one carry *fits names*; the largest DSR mean is 0.122 (tree, 5 days, survivor-only) against 0.95. Read no baseline as evidence of an edge, and read the network against the tree, whose 3-month IC is not zero. The two periods also differ in years, not only in survivorship, so their gap is not NR-F-09's bias alone. | `docs/RESULTS.md` (baselines), `harness/goldens/baseline_tree.json`, `baseline_momentum.json`, `baseline_reversal.json`, `harness/trials.tsv`, ROADMAP 3.3 | 3.3's expectation; phase 4 (the network's bar is the tree); every reading of a baseline |

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

**NR-F-08, in 2.2 (the sample to 2017-11-07, through `neonrain/universe/prices.py`).** 11,965,174 rows, 3,194 tickers, 5,116 dates; 165 rows
on 120 dates are no session (24 tickers, every one also a ticker with rows on sessions), so the frame has 11,965,009 rows on 4,996 sessions of 1998-01-02
to 2017-11-07; 0 sessions in that span have no row; the 36 sessions of the calendar after 2017-11-07 (to 2017-12-29) lie outside the sample. A row is left out only
because the harness would refuse it, and it is returned, never lost; the loader cannot tell a stray row from a mis-dated one, and does not try.

## NR-F-09: how much a survivor-only sample flatters a result, 2026-10-25 (R-026 c)

Measured on the synthetic market (HAR-10), through the frozen harness, before the first baseline's result. Synthetic only; no
line was appended to `harness/trials.tsv` (a measurement of the harness is not a trial, HAR-09). `python scripts/probe/survivorship.py 8 OUT.json` prints
every row below and more (the full and survivor means, the undefined cells, the seed spread); about 3.6 minutes on four cores.

**What was run.** Each seed makes one market: 160 tickers, 1,200 sessions, `rho` 0 (no planted edge), `delist_below` 0.4 (a name
leaves at its first close under 40% of its start price). On average 21% of the tickers delist, and 2,074 label cells at the 63-day
horizon end in a delisting (HAR-02, J-024). The survivor-only market is the same market with those tickers taken out of
prices, universe and features entirely, as a survivor-only source gives them: the construction of
`survivorship_market` and `mean_forward` in `test/test_harness_adversarial.py` (TODO 1.6), copied into the probe. Control: it
inflates the mean 63-day forward return by +0.0133 (the adversarial test's margin is 0.02 on its own, higher-volatility market), so the
removal does what that test shows. Both markets run through `split.folds` at its defaults (HAR-03: two folds on 1,200 sessions),
`split.ticker_groups` (five groups, seed 5), `targets.labels`, `metrics.information_coefficient`, `portfolio.daily`
(scored on every universe row of the test span, R-021) at c = 10 bps, `metrics.sharpe` and `metrics.deflated_sharpe` with **one
trial** (no trials-file line exists for these runs, so no deflation by N is applied: the DSR here is the probabilistic Sharpe
ratio). Eight seeds (0 to 7), run on four processes: one seed gave differences of the size of their own noise for the Sharpe, and
eight give a spread over seeds and a count of seeds on each side of zero.

**The scorers** (all price-only, from the market's own closes; none is a model): *random*, a hash of (ticker, date, seed), the
same value for a cell in both markets, so the control cannot differ by luck of the draw; *reversal-5* and *reversal-21*, minus
the return over the last 5 or 21 sessions (the recent losers rank high); *momentum-126*, plus the return over the last 126
sessions (about six months). Lookbacks are named choices: 5 and 21 are a week and a month, the reversal horizons the literature
uses; 126 is a medium momentum window that fits inside the 1,200 sessions and the first fold's training span. The market plants
no edge in any of them (`synthetic.py` plants only the `edge` column, a forward-looking feature not used here), which is the point:
anything they earn beyond zero, or lose below it, is the sample.

**Survivor-only minus full market** (mean of the eight seeds; each seed's value is the mean over its fold-by-group cells; "folds sd" and "groups sd" are HAR-08's
dispersion of the per-cell difference averaged over seeds; "seed sd" is the sd of the eight per-seed differences; "+ seeds" counts seeds above zero):

| Scorer | Horizon | IC diff | Sharpe full | Sharpe survivors | Sharpe diff (folds sd, groups sd, seed sd) | + seeds | DSR diff (seed sd) | + seeds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random | 3 | +0.0000 | -1.722 | -1.683 | +0.039 (0.004, 0.066, 0.084) | 6/8 | +0.012 (0.020) | 6/8 |
| random | 5 | +0.0010 | -1.361 | -1.362 | -0.001 (0.037, 0.083, 0.084) | 4/8 | +0.005 (0.018) | 6/8 |
| random | 21 | +0.0002 | -0.273 | -0.291 | -0.018 (0.012, 0.143, 0.174) | 4/8 | -0.008 (0.035) | 3/8 |
| random | 63 | -0.0007 | -0.377 | -0.353 | +0.024 (0.053, 0.066, 0.205) | 5/8 | +0.008 (0.041) | 5/8 |
| reversal-5 | 3 | +0.0007 | -1.295 | -1.169 | +0.126 (0.161, 0.083, 0.165) | 6/8 | +0.017 (0.030) | 6/8 |
| reversal-5 | 5 | +0.0020 | -0.977 | -0.814 | +0.163 (0.153, 0.069, 0.189) | 7/8 | +0.030 (0.035) | 7/8 |
| reversal-5 | 21 | +0.0023 | -0.338 | -0.115 | +0.223 (0.102, 0.123, 0.231) | 7/8 | +0.044 (0.041) | 8/8 |
| reversal-5 | 63 | +0.0048 | -0.092 | +0.072 | +0.164 (0.097, 0.098, 0.131) | 8/8 | +0.032 (0.021) | 8/8 |
| reversal-21 | 3 | +0.0015 | -1.036 | -0.856 | +0.180 (0.180, 0.136, 0.285) | 7/8 | +0.014 (0.028) | 5/8 |
| reversal-21 | 5 | +0.0021 | -0.597 | -0.435 | +0.162 (0.157, 0.160, 0.236) | 6/8 | +0.022 (0.029) | 6/8 |
| reversal-21 | 21 | +0.0005 | +0.057 | +0.208 | +0.151 (0.024, 0.141, 0.131) | 7/8 | +0.036 (0.029) | 7/8 |
| reversal-21 | 63 | +0.0074 | +0.023 | +0.144 | +0.121 (0.058, 0.135, 0.086) | 8/8 | +0.028 (0.019) | 8/8 |
| momentum-126 | 3 | -0.0040 | -1.124 | -1.230 | -0.106 (0.051, 0.203, 0.181) | 2/8 | -0.019 (0.033) | 2/8 |
| momentum-126 | 5 | -0.0057 | -0.637 | -0.766 | -0.129 (0.104, 0.180, 0.119) | 1/8 | -0.027 (0.028) | 1/8 |
| momentum-126 | 21 | -0.0109 | -0.054 | -0.193 | -0.139 (0.113, 0.126, 0.119) | 1/8 | -0.034 (0.027) | 2/8 |
| momentum-126 | 63 | -0.0225 | +0.037 | -0.106 | -0.143 (0.063, 0.073, 0.167) | 2/8 | -0.029 (0.037) | 2/8 |

The IC differences' seed sds are 0.0008 to 0.003 (random), 0.004 to 0.012 (reversal), 0.007 to 0.026 (momentum); the IC is
undefined in 10 of 80 cells on the full market and 16 of 80 on the survivors (a ticker group under the 20 tickers a date needs, HAR-07),
so the IC rows average over slightly different cells.

**Reading.**

- **The mechanism has the sign it should.** A name that falls under 40% leaves the survivor-only sample, so among survivors a
  recent loser is one that fell and did not die, and its next return runs higher than the same loser's would with the dead ones
  counted; a recent winner is not hurt the same way. The control (random) shows no difference beyond its spread, so the harness does not
  invent one; reversal gains in 6 to 8 seeds of 8 at the horizons from 5 days up, momentum loses in 6 to 7 of 8 at every horizon.
- **It is not large.** The best case is about +0.2 of an annualized long-short Sharpe (reversal-5 at 21 days) and +0.04 of DSR; at 3 and 5
  days the cost drag (Sharpe -1 or worse here) swamps it. The spread over seeds is as big as the difference for most rows
  (a single seed is not enough), and the spread over groups is as large again: the difference is a tilt, not a
  number to subtract.
- **Momentum is understated, not overstated.** On a survivor-only sample a momentum result is, if anything, pessimistic; a reversal-like
  or mean-reverting result is optimistic. The direction depends on the strategy, so no single correction applies.
- The IC differences grow with the horizon (reversal-21 +0.0074, momentum -0.0225 at 63 days; the Sharpe differences do not
  grow steadily): more of a longer window's names reach the barrier, as in NR-F-02.

**For WIKI's survivor-only period (R-026 b).** Read 1998 to 2013 as an upper bound for a strategy that buys what fell and as a
lower bound for one that buys what rose; a rank or direction model that learns either pattern carries the same tilt without saying
so. This probe puts a size on the synthetic case only: well under half a Sharpe unit and a few hundredths of DSR for a no-edge
strategy. Read with R-026's two periods apart, a number from before 2014-04-01 that beats the one from 2014 on by about this much
is what survivorship alone produces; a gap much larger than the seed and group spread here is not explained by it.

**Limits.** (1) Synthetic delistings are a random walk crossing a barrier at 40% of the start price, 21% of the names over 4.8 years
(about 4.5% a year). Real ones are mergers (a buyout at a premium, which flatters nothing), bankruptcies (a collapse with a
gap and no recovery), and moves between exchanges; the real loss of names is 3 to 8% a year, with a heavier tail of ruin than a
barrier at 60% down. (2) The market has no momentum or reversal planted and no link between a name's quality and its fate beyond its path, no
sectors, no fat tails, no volatility clustering, and one idiosyncratic volatility for every ticker; real delistings are
concentrated in the names that already look bad on every feature. (3) The scorers are three price rules, not a trained
network; a model that learns *who* delists would be flattered more or differently. (4) Two folds and five groups of about 25 to 32 tickers (fewer
on the survivors) give the dispersions few degrees of freedom. (5) One trial per DSR; a real result deflates by its N (HAR-09), which this
probe does not. (6) The survivor-only sample here lacks every delisted name; WIKI's 1998 to 2013 lacks the real ones, which are not a random 21%. (7) Delisting ends use the last close
(J-024); the survivor-only market has none, which is the inflation of +0.0133 in the 63-day mean forward return.


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

## NR-F-10: the zero baseline is an alphabetical book, 2026-10-28 (TODO 3.1 a)

The zero baseline scores every cell 0.5. HAR-07's IC is then undefined (every date is in `dropped_flat`), but the portfolio
is not: with every score tied, HAR-07 breaks ties by ticker, so each date's long and short legs are the alphabetically first
and last names, and the portfolio trades that book. Its 0 bps Sharpe (about -0.07) is noise. Its after-cost Sharpe is the
harness's turnover floor, about 1/h in scale. 10 bps, survivor-only / from 2014:

| Horizon | Sharpe at 10 bps, survivor-only | from 2014 |
| --- | --- | --- |
| 3 | -3.32 | -3.71 |
| 5 | -2.02 | -2.09 |
| 21 | -0.53 | -0.59 |
| 63 | -0.20 | -0.36 |

Decided (Fable, 2026-10-28): zero is reported as the harness computes it. A later baseline is read against these floors, not
against zero. Possible harness v2, not done now and for Ghost to decide (it would move a golden, HAR-14): a date whose scores
are all equal opens no sleeve.
