# Results: every number the project stands behind

One row per (run, horizon, metric). A number appears here only when it meets HAR-13: a trials line,
both axes' dispersion, the three cost levels, the dropped-cell counts, the findings it carries cited
by number, and the goldens unchanged if the harness was touched. `test/test_results.py` holds this
file to `harness/trials.tsv`: every row here has a line there, and every `config_hash` here exists.

Nothing is reported yet. The first rows are phase 3's baselines.

## How to read a row

```
mean ± sd [min, max]            over folds, then over groups (HAR-08)
DSR                             deflated Sharpe: < 0.95 is not evidence of an edge (HAR-07)
c = 0 / 10 / 25 bps             one-way cost; the edge's survival across them is the point (HAR-06)
```

A row whose **group-axis sd exceeds its group-axis mean** is marked *fits names, not an algorithm*
and does not count as beating a baseline, however good its mean (R-014).

## Baselines (phase 3)

| Run | Horizon | Metric | Folds: mean ± sd [min, max] | Groups: mean ± sd [min, max] | DSR | Costs | Findings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| *(none yet)* | | | | | | | |

## The network (phase 4)

| Run | Horizon | Metric | Folds | Groups | DSR | Costs | vs. tree | Findings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| *(none yet)* | | | | | | | | |

## The scorer's own number (phase 5.3)

Agreement between the pinned Haiku scorer and Ghost's hand labels on the 200-story calibration set,
with FinBERT on the same set as the scorer's baseline. Not a market result; a measurement of the
feature's input quality.

| Scorer | Agreement | Ticker accuracy | Notes |
| --- | --- | --- | --- |
| *(none yet)* | | | |

## Ablations (phase 6.2)

The prediction, written before the run (F-04): news features help the 3- and 5-day horizons and do
little at 63 days. Recorded here either way.

| Feature families | Horizon | Metric | Folds | Groups | vs. prices-only | Findings |
| --- | --- | --- | --- | --- | --- | --- |
| *(none yet)* | | | | | | |

## The forward test (phase 7)

Predictions ledgered before their outcomes existed (PL-01), scored as each horizon elapsed, with the
backtest's number beside it. A disagreement is a finding, not a reconciliation (PL-04).

| Period | Horizon | Metric | Forward | Backtest | Findings |
| --- | --- | --- | --- | --- | --- |
| *(none yet)* | | | | | |
