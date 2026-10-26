# Glossary: one word per concept

The canonical word for each concept, what it means, and the words *not* to write. An alias in
backticks is enforced: `test/test_glossary.py` fails when it appears in a document outside this file.
An alias without backticks is a review guide. Enforce an alias only when it has no other honest use
here: "prediction" (the network's output), "signal" (what daily returns carry little of) and
"oracle" (Katana's P-01, cited) are right words for other things, and a test cannot tell the uses
apart. Add a term before using a new word for a concept (Katana R-039's rule).

| Term | Means | Not |
| --- | --- | --- |
| **universe** | the set of tickers eligible on a given date, with dates in and out | watchlist, basket, index (an index is a published one) |
| **dollar volume** | raw (unadjusted) close times volume for one ticker on one day; the universe ranks tickers by its median over 63 sessions (TODO 2.1b) | turnover, notional |
| **calendar** | the ordered NYSE trading dates (whole days), derived by rule in `neonrain/universe/calendar.py` (TODO 2.1a); the harness counts horizons on it | trading days list, holiday file |
| **horizon** | one of the four forward windows: 3, 5, 21, 63 trading days | window (a window looks back), period, `timeframe` |
| **target** | the label for one ticker, one date, one horizon: direction or rank (R-004) | prediction (that is the network's output), outcome, y |
| **direction** | the sign of the horizon's excess return over the universe median | up/down, class |
| **rank** | the percentile of the horizon's return within the universe that day | score (that is the scorer's), ordering |
| **feature** | one input column of the feature table, per ticker per day | signal (a signal is a trading rule's output), input, indicator (an indicator is one family of features) |
| **feature family** | features that share a source and an ablation: price-derived, indicator, news | feature group, feature set |
| **lookback** | how many sessions of the calendar a feature looks back from its date: a count of sessions, never of calendar days. The returns family uses 3, 5, 21 and 63, the four horizons (TODO 2.3) | window (a window may look forward; the horizon is the forward count), lag |
| **return** | the feature `ret_k`: the adjusted close at *t* over the adjusted close *k* sessions earlier, minus 1, a total return; null when any of the *k*+1 sessions has no price (TODO 2.3). | gain, performance, change, momentum (a trading rule built on returns) |
| **volatility** | the feature `vol_k`: the sample standard deviation (divisor k-1) of the k daily log returns of the adjusted close over the last k sessions, in units of a log return per session, not annualized; the volatility family uses 5, 21 and 63, the horizons but the 3 (TODO 2.3). Null when any of the *k*+1 sessions has no price | risk, vol (outside a column name), variance, dispersion (that is the harness's, over folds and groups) |
| **volume ratio** | the feature `volr_k`: the split-adjusted volume at *t* over the mean volume of the *k* sessions before *t* (*t* not among them), 1 being the usual volume; the volume ratio family uses 5, 21 and 63, the horizons but the 3 (TODO 2.3). Null when a session from *t*-*k* to *t* has no usable volume, or when the mean is zero; 0 when nothing traded at *t* | volume surge, relative volume, turnover (dollar volume is a different thing) |
| **RSI** | the feature `rsi_14`: 100 G / (G + L), G and L the sums of the gains and of the losses of the adjusted close over the last 14 daily changes (the finite-window, simple-average form, not Wilder's exponential one), 0 to 100. Null when any of the 15 sessions has no price, and when the window is flat (G + L = 0) (TODO 2.3, the indicator family) | relative strength index (spell it out once, then RSI), momentum (a return is momentum) |
| **MACD** | the features `macd` and `macd_hist`: the line is the exponential average of 12 sessions of the adjusted close less that of 26, the histogram the line less its signal (the exponential average of 9 lines), each over the exponential average's own last-n closes only and divided by the close at *t*, so a fraction of the price. Null unless the 26 sessions (line) or 34 (histogram) ending at *t* all have a price (TODO 2.3, the indicator family) | signal (as a feature name: the signal is the line less the histogram, no column), convergence |
| **moving-average ratio** | the feature `mar_k`: the adjusted close at *t* over the mean of the closes of the *k* sessions ending at *t* (*t* inside its own mean), 1 being a price on its mean; the family uses 5, 21 and 63, the horizons but the 3 (TODO 2.3). Null when any of the *k* sessions has no price | price over average, MA cross (a ratio of two averages is another feature) |
| **cross-section** | the universe names of one date, taken together: the set a feature is ranked against, and no other date's rows (TODO 2.4). A name outside the universe that date is not in it. | panel (a panel is every date), slice, bucket |
| **normalized feature** | a family's feature after per-day normalization (`neonrain/features/normalize.py`, TODO 2.4): its centred rank within the cross-section, `(rank - 1) / (n - 1) - 0.5` in [-0.5, 0.5], ties the average rank, `n` the names with a value that day, the cross-section's mean exactly 0. Null when it has no value, or when fewer than 20 names have one (HAR-02's `min_tickers`). Same column name and `_stamp` column as the family's; the stamp is the latest stamp of the cross-section's valued cells. A family's frame has the price frame's cells; the normalized frame has the universe's cells, one row each, and a price row outside the universe that date has no row (the two contract questions J-056 left, decided in 2.4). | standardized, scaled (a rank is not a z-score; none is built), percentile (that is the rank label's word) |
| **harness** | the evaluation code: splits, cost model, metrics, trials file (R-002, frozen) | backtester, framework, oracle (Katana's word; here the harness has no oracle but the future) |
| **synthetic market** | the seeded fake market of HAR-10, with an edge of known strength planted in it | simulation, toy data, fake market |
| **fold** | one walk-forward step: its training span, embargo and test span | split (a split is the whole grid), slice |
| **group** | one of *k* seeded partitions of the universe by ticker, held out in turn (R-014) | cluster, bucket |
| **dispersion** | the spread of a metric across folds and across groups: standard deviation and range | variance (a statistic, not the report), error bars |
| **trials line** | one row of `harness/trials.tsv` for one harness run (R-005) | run log, experiment |
| **baseline** | one of the fixed comparators of R-007: zero, momentum, reversal, tree | benchmark (Ghost's word for a horizon; avoided for this), control |
| **tree** | the LightGBM baseline | GBM, booster |
| **network** | the one neural model of R-009 | model (alone: ambiguous with the scorer), `NN`, net |
| **scorer** | the pinned Haiku reader that writes the news ledger (R-008) | sentiment model, agent, classifier |
| **score** | the scorer's 1–10 bullish/bearish value for one story and one ticker | sentiment, polarity, rating |
| **story** | one news item with a publish time | article, headline (a headline is a story's title), post |
| **publish time** | when the story was public, per its source; the only time a feature may key on | fetch time, scored-at (both recorded, neither used for features) |
| **ledger** | an append-only file of what was known when: the news ledger or the prediction ledger (§3.2) | log, cache, history |
| **cut** | the publish-time filter that hides ledger rows at or after the feature date | mask, as-of (as a verb) |
| **golden** | a frozen harness result that a refactor must reproduce byte-identically (P-02) | snapshot, fixture |
| **finding** | an entry in `docs/FINDINGS.md`: a bias, a leak, a failed hypothesis, said before the result it qualifies | caveat, limitation, known issue |
| **forward test** | phase 7: predictions appended to the prediction ledger before their outcome is known | paper trading (implies orders), live test |
| **tithe** | a commit or pass that improves the agent's environment and changes no result (R-012) | cleanup, refactor (a refactor changes code shape; a tithe may not) |
