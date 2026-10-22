# Glossary: one word per concept

The canonical word for each concept, what it means, and the words *not* to write. An alias in
backticks is enforced: `test/test_glossary.py` fails when it appears in a document outside this file.
An alias without backticks is a review guide. Add a term before using a new word for a concept
(Katana R-039's rule).

| Term | Means | Not |
| --- | --- | --- |
| **universe** | the set of tickers eligible on a given date, with dates in and out | watchlist, basket, index (an index is a published one) |
| **horizon** | one of the four forward windows: 3, 5, 21, 63 trading days | window (a window looks back), period, `timeframe` |
| **target** | the label for one ticker, one date, one horizon: direction or rank (R-004) | `prediction` (that is the model's output), outcome, y |
| **direction** | the sign of the horizon's excess return over the universe median | up/down, class |
| **rank** | the percentile of the horizon's return within the universe that day | score (that is the scorer's), ordering |
| **feature** | one input column of the feature table, per ticker per day | `signal` (a signal is a trading rule's output), input, indicator (an indicator is one family of features) |
| **feature family** | features that share a source and an ablation: price-derived, indicator, news | feature group, feature set |
| **harness** | the evaluation code: splits, cost model, metrics, trials file (R-002, frozen) | backtester, framework, `oracle` (Katana's word; here the harness has no oracle but the future) |
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
