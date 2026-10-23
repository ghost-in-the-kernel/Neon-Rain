# The harness: the contract

The harness is the evaluation code: targets, splits, the cost model, the metrics, the trials file.
It is built before any model and frozen when phase 1 closes (theGhost.md R-002); after the freeze it
changes only in a commit where every golden in `harness/goldens/` is byte-identical, or under a
decision in `theGhost.md` that says why not.

Invariants are numbered HAR-01 onward, in this document only, and a number is never reused.
`test/test_harness_doc.py` holds this document to `neonrain/harness/`: the invariants here are the
code's, and the reverse.

**This document is the specification the blind mirror is written from** (R-015c). An agent
reimplementing the metrics must be able to work from this file alone, without reading
`neonrain/harness/`. If something here is not precise enough to implement, that is a defect in this
document, and the fix is to make it precise, not to read the code.

---

## What the harness is given

`neonrain/harness/market.py` holds the `Market` type (the four things below, in this order: `prices`,
`universe`, `features`, `calendar`), these layouts, and `check_market`, which refuses a `Market` that
does not have them (`LayoutRefused`, the message naming the frame and the first offending row or
column). Both the synthetic market (HAR-10) and phase 2's loader build a `Market`; neither imports the
other. Frames are polars; a column is named and typed exactly as below.

- A **price frame**: one row per (ticker, trading date) with adjusted close, and whatever else the
  features need. Columns `ticker` (String), `date` (Date), `close` (Float64), in any order, other
  columns allowed. "Adjusted" means adjusted for splits and cash dividends; a source that does not
  adjust is recorded as a finding and its prices are adjusted by the loader or refused.
- A **universe frame**: for each trading date, the tickers eligible that day (R-006), including
  names that were later delisted. Exactly the columns `ticker` (String) and `date` (Date), in that
  order, one row per eligible (ticker, date).
- A **feature frame**: one row per (ticker, date), every other column a feature, each carrying its
  provenance stamp (HAR-12). Columns `ticker` and `date` as above; then, for each feature `f`, a
  numeric column `f` and a column `f_stamp` (HAR-12 gives its type and meaning). A column whose name
  ends in `_stamp` is a stamp, never a feature; a feature without its stamp column, or a stamp
  without its feature, is refused.
- A **calendar**: the ordered list of trading dates (Python `date`s), strictly ascending and not
  empty. All horizons are counted in trading days on this calendar, never calendar days.

In every frame `ticker` and `date` are never null and a (ticker, date) pair occurs at most once; and
every `date` in any frame is on the calendar. Nothing else is checked about the values: a null or
non-positive `close`, or a ticker absent from the universe, is not a layout fault (HAR-02 counts
missing prices; the frames are read as they come).

The harness never reads the clock, never reaches the network, and never imports `neonrain.models`
or `neonrain.baselines` (modules.json MOD-02).

---

## HAR-01 One run, one row

Every evaluation produces one result object and appends its lines to `harness/trials.tsv`: one line
for each (horizon, metric) pair the run reports (HAR-09), all carrying the run's config hash. A run is
identified by its **config hash**: the SHA-256, truncated to its first 16 lowercase hex digits, of the
canonical JSON of the object

```
{"feature_columns": [...], "target": {...}, "split": {...}, "cost": {...},
 "model": {"name": "...", "hyperparameters": {...}}, "data_manifest": {...}, "harness_version": "..."}
```

- `feature_columns`: the names of the feature columns used, as a list sorted ascending (so their
  order cannot change the hash); a name twice is refused.
- `target`: the target definition, including `min_tickers` (HAR-02). `split`: the split parameters,
  including `E`, the step, the rolling window or its absence, the `k` and `seed` of HAR-05. `cost`:
  the cost parameters of HAR-06. `data_manifest`: dataset name to its manifest hash. Each is a JSON
  object whose values are strings, numbers, booleans, null, lists or objects.
- `harness_version`: the string `"0"` while phase 1 builds; the freeze (ROADMAP 1.7) sets it to `"1"`.
- **Canonical JSON** is exactly: keys sorted ascending at every depth, no whitespace (separators `,`
  and `:`), non-ASCII characters escaped as `\uXXXX`, UTF-8 bytes, NaN and infinity refused. A number
  is written as the shortest text that reads back as itself (`0.1`, `1.0`, `3`); the integer `1` and
  the float `1.0` are different texts and so hash differently, so a caller gives each parameter the
  same type every run.

Two runs with the same config hash must produce identical numbers; a line whose hash, horizon and
metric match an earlier line that has a mean, but whose mean or dispersion text differs, is a failure:
it is still appended (the trial happened), with `CONFLICT: numbers differ from an earlier line with
this hash` at the start of its note, and reported as an error, never averaged away.

## HAR-02 The four horizons and their two labels

For ticker *i*, date *t* and horizon *h* ∈ {3, 5, 21, 63} trading days:

- **Forward return** `r(i,t,h) = P(i, t+h) / P(i, t) − 1`, where `t+h` is the *h*-th trading date
  after *t* on the calendar and `P` is adjusted close.
- **Excess return** `x(i,t,h) = r(i,t,h) − median{ r(j,t,h) : j ∈ universe(t) }`, the median taken
  over the tickers eligible on *t* that have a price at both *t* and *t+h*.
- **Direction label** `d(i,t,h) = 1` if `x(i,t,h) > 0`, else `0`. A row with `x` exactly `0` has
  no direction label and is counted in the run's `dropped_ties`; it keeps its rank label. With an
  odd number of tickers the median is one ticker's own return, so about one direction cell in
  `N(t)` is a tie every date: expected, not a fault (J-014).
- **Rank label** `q(i,t,h) = (rank(i) − 1) / (N(t) − 1)` ∈ [0, 1], where `rank` is the ascending
  rank of `x(i,t,h)` among the `N(t)` eligible, priced tickers on *t*, ties taking the average rank.
  `N(t) < min_tickers` makes the date unusable: it is dropped and counted in `dropped_thin_dates`.
  `min_tickers` is part of the run's config, 20 unless a test says otherwise.

The cells are the (ticker, date) pairs of the universe frame whose date has an *h*-th trading date
after it on the calendar; the last *h* dates have none, make no cells and are not counted. A ticker
whose last price comes before *t+h* was delisted: its last close stands as `P(i, t+h)` (a delisting
return), and the cell is counted in `delisting_ends` (NR-F-02, resolved by Ghost, J-024). A ticker
missing a price at *t*, or at *t+h* while it trades again later (a gap in the data), is excluded
from that (i,t,h) cell and counted in `dropped_missing`. The three dropped counts appear in every result; a run that drops more than 5% of
its cells is reported with that fact beside its numbers.

The harness predicts nothing else. There is no price-level and no raw-return target (R-004).

## HAR-03 Walk-forward, purged and embargoed

A **fold** is three spans of the calendar, in order: a training span `[a, b)`, an **embargo** span
`[b, b + E)` that belongs to neither, and a test span `[b + E, c)`.

- `E ≥ 63` trading days, the longest horizon, for every fold regardless of the horizon under test
  (one embargo for all four, so the four horizons' results are comparable fold by fold).
- **Purge**: a training row (i, t) is dropped from the training set when `t + h ≥ b` for the horizon
  under test — its label window reaches into the embargo or the test span. Purging is applied to
  the training set, never to the test set.
- Folds roll forward: `b` advances by the **step** (default 126 trading days, about six months),
  `c = b + E + step`. Training is expanding by default (`a` fixed at the start of data); a rolling
  window is a parameter, and which was used is in the config hash.
- The first fold requires at least 756 training dates (about three years) after purging at the
  **longest** horizon: its `b` is the first with `b − a − 63 ≥ 756`, counted in trading dates. The
  folds are therefore the same for all four horizons (J-015). Earlier dates are warm-up, not folds.
- A fold exists only when its whole test span is on the calendar (`c ≤` the number of dates); a
  partial last span is not a fold. With a rolling window of `W` dates, `a = b − W`.

**There is no random k-fold, no shuffled split, and no stratified sampling over dates, ever.** A
function in the harness that shuffles rows across dates is a defect.

## HAR-04 Nothing in a fold's training may postdate its test span

Mechanically: for a fold with test span starting at `s`, every input used to fit anything — model
weights, feature normalization statistics, imputation values, the universe median of HAR-02,
hyperparameter choices, early-stopping decisions — is computed from rows with date `< s − E`. Early
stopping uses a validation slice carved from the *end of the training span* (before the embargo),
never from the test span.

This is the invariant the adversarial tests attack first, and the one the provenance stamp of
HAR-12 enforces per feature.

## HAR-05 The second axis: held-out ticker groups (R-014)

The universe is partitioned into `k` groups (default `k = 5`) by `group(ticker) =
int(sha256(f"{seed}:{ticker}".encode("utf-8")).hexdigest(), 16) % k`, with the seed in the config
hash (the colon keeps seed 1 with ticker "2AB" apart from seed 12 with "AB", J-015). A ticker is in
exactly one group for the whole run; a ticker that enters or leaves the universe keeps its group. A
partition that leaves a group empty is refused, naming the group: its grid cells would test nothing.

Every evaluation is the **grid** of folds × groups: for each fold and each group `g`, train on the
fold's training rows for tickers not in `g`, and test on the fold's test rows for tickers in `g`.
The model is trained pooled across the tickers of the other groups; a model trained on one ticker is
refused (R-014).

## HAR-06 The cost model

A result is reported both before and after costs. Cost is charged on turnover: for a portfolio with
weights `w` rebalanced to `w'`, the cost is `c · Σ|w'ᵢ − wᵢ| / 10000` where `c` is the one-way cost
in basis points of notional. `c` is a parameter; the default is **10 basis points** (0.10%), standing
for commission, half-spread and slippage on a liquid US name, and every result also reports `c = 0`
and `c = 25` so a reader sees how fast the edge dies. A result quoted at one `c` only is incomplete.

Which trades pay (R-021, every answer the one that does not understate cost):

- **Opening and closing both pay.** A sleeve (HAR-07) opened from zero pays on its full gross
  weight, and closing it at the end of its hold pays again; so does the last sleeve of a test span.
- **Each sleeve pays for itself.** The `h` overlapping sleeves are charged separately, each at its
  `1/h` share, with no netting of one sleeve's buys against another's sells. A real book that nets
  would pay less; the harness never assumes it does.
- **Both legs count.** Turnover sums the long and the short leg: opening a sleeve is
  `Σ|w| = 2` (gross 1 per leg) and so is closing it, so a sleeve's round trip costs `4c / 10000` of
  its share.
- **A delisting pays.** A position whose ticker leaves the universe while held is closed at its
  last price and pays on that weight then (see NR-F-02 for the labels' side of delistings).

Direction accuracy and rank correlation are cost-free by construction and reported once; only the
portfolio metrics carry costs.

## HAR-07 The metrics, defined exactly

Let a run produce, for each horizon, a set of test-set predictions: for direction, a score in [0, 1]
per (i, t); for rank, a real-valued score per (i, t) whose order is what matters.

- **Accuracy**: over test rows that have a direction label (a tie has none, HAR-02), the fraction
  where `(score > 0.5) == (d == 1)`. A score of exactly 0.5 predicts 0.
- **Balanced accuracy**: the mean of the two per-class recalls, `(TP/(TP+FN) + TN/(TN+FP)) / 2`, the
  prediction being `score > 0.5` as above. Reported alongside accuracy always, because the direction
  classes are near but not exactly balanced by construction. With no rows of one class it is
  undefined (reported as such, never as a number). Accuracy over no rows is undefined too.
- **Information coefficient (IC)**: for each test date *t*, the Spearman rank correlation between
  the predicted scores and `q(i,t,h)` over the tickers tested on that date: the Pearson correlation
  of their ranks, ties taking the average rank. A date with fewer than `min_tickers` (HAR-02, 20 by
  default) tested tickers is dropped, and so is a date whose scores, or whose labels, are all equal
  (no correlation exists); both are counted. The run's IC is the mean over the remaining `n_dates`,
  reported with the standard error of that mean `sd / √n_dates` and `IC_t = mean / (sd / √n_dates)`,
  where `sd` is the sample standard deviation (divisor `n_dates − 1`). With fewer than two dates
  the standard error and `IC_t` are undefined; with `sd = 0` the standard error is 0 and `IC_t` is
  undefined.
- **Long–short decile return**: on each test date, sort the tested tickers by predicted score; long
  the top decile and short the bottom decile, equal-weighted within each leg, gross exposure 1 per
  leg. The position is held `h` trading days, so `h` overlapping portfolios run in parallel and the
  day's return is their average (this is the standard overlapping-portfolio construction; it keeps
  the daily series i.i.d.-ish rather than counting the same bet `h` times). Exactly (J-016):
  - The portfolio is scored on **every universe row of the test date** that has its features, never
    only on the rows that have a label: a label needs a price at *t+h* (HAR-02), so trading only
    labelled rows would keep out every name about to delist, a choice on *t* made with *t+h*'s
    knowledge (J-018, NR-F-02). Accuracy and IC, which need the label, use the labelled rows.
  - A leg holds `n = ⌊N(t)/10⌋` names of the `N(t)` tickers with a score and a price on *t*; with
    `n = 0` the date opens no sleeve. The tickers are ordered ascending by (score, ticker), so the
    order is total and the same every run: the short leg is the first `n`, the long leg the last `n`
    (J-018: at a tie the earlier ticker goes short).
  - A **sleeve** opened at the close of *t* earns on each of the next `h` trading dates `d` the mean
    daily return `P(i,d)/P(i,d−1) − 1` of its long names minus that of its short names: equal
    weights, held through the `h` days. The day's portfolio return is the sum over the sleeves open
    that day of `1/h` times the sleeve's return, less the costs of HAR-06 paid that day; a sleeve
    that does not exist yet (the first `h − 1` days of a span) is cash, earning 0.
  - A name that has no price on a day of its hold was delisted: its last return is the one up to its
    last price, it is closed there and pays its cost (HAR-06) on the date of that last price, and its
    slot earns 0 for the rest of the sleeve, so the leg's mean still divides by `n`; a price that
    returns later does not reopen it. (The cost is booked a day before the missing price is seen:
    a look-ahead in the daily timing that moves no total, J-018.)
  - Sleeves open on test dates only; a sleeve opened on the span's last dates runs past it into the
    next span's dates, so the daily series covers the test dates plus up to `h` after. A sleeve
    still open on the calendar's last date is closed there and pays.
- **Sharpe**: `mean(daily) / sd(daily) · √252`, on the after-cost daily series, excess of zero (not
  of a risk-free rate; the comparison is to not trading, and the series is already long–short).
  `sd` is the sample standard deviation (divisor `T − 1`); a series with fewer than two days, or
  with `sd = 0`, has no Sharpe.
- **Deflated Sharpe ratio (DSR)**, after Bailey & López de Prado (2014), the one number that
  accounts for how many things were tried:

  ```
  γ   = 0.5772156649                      (Euler–Mascheroni)
  Z   = standard normal CDF, Z⁻¹ its inverse
  N   = the number of trials, ≥ 1: HAR-09's trials_so_far + 1
  V   = the variance of the Sharpe ratios across those trials
  SR₀ = √V · [ (1 − γ)·Z⁻¹(1 − 1/N) + γ·Z⁻¹(1 − 1/(N·e)) ]
  DSR = Z[ (SR − SR₀)·√(T − 1) / √(1 − skew·SR + ((kurt − 1)/4)·SR²) ]
  ```

  where `SR` is the non-annualized Sharpe of the `T` daily returns (`mean / sd`, `sd` with divisor
  `T − 1`) and `skew`, `kurt` are their moment estimates with divisor `T`: `skew = m₃ / m₂^1.5`,
  `kurt = m₄ / m₂²` (kurtosis not excess), `mₖ` the mean of `(x − mean)ᵏ`. `V` is the sample variance
  (divisor `N − 1`) of the trials' **non-annualized** Sharpes, the same unit as `SR`. With `N = 1`
  nothing was selected: `SR₀ = 0` and `V` is not needed (the formula's `Z⁻¹(0)` is −∞; J-017), so the
  DSR is then the probabilistic Sharpe ratio. If the term under the square root is not positive the
  DSR is undefined. `DSR` is the probability the true Sharpe exceeds zero given the selection. A
  result whose `DSR < 0.95` is not evidence of an edge, and is written up as such.

## HAR-08 Every number carries its dispersion (R-014, P-07)

A metric is never reported as a single number. For each horizon and metric, a result reports:

```
fold axis   : mean ± sd over folds,  [min, max],  n_folds
group axis  : mean ± sd over groups, [min, max],  n_groups
```

where the fold-axis statistics average over groups within each fold first, and the group axis
averages over folds within each group first. Exactly (J-018): `sd` has divisor `n − 1` and is
undefined for a single value; a grid cell whose metric is undefined (HAR-07) is left out of both its
fold's and its group's average and counted as `undefined_cells`; a fold or group with no defined
cell is left out of its axis, so `n_folds` and `n_groups` count what was averaged. The **group-axis spread is the memorization test**: a
model whose group-axis sd exceeds its group-axis mean in absolute value is reported as *fits names,
not an algorithm*, and does not count as beating a baseline however good its mean (R-014).

## HAR-09 The trials file

Every run appends tab-separated lines to `harness/trials.tsv`, which is git-tracked and
append-only: `config_hash`, `date`, `horizon`, `metric`, `mean`, `dispersion`, `trials_so_far`,
`note`. The first line of the file is these eight names joined by tabs. A run appends one line for
each (horizon, metric) pair it reports (HAR-01). `trials_so_far` is the count of lines before this one
that share the metric, whatever their hash or horizon and whether they failed or not — a run's own
earlier lines count, and so does a repeat of an earlier run. The `N` of HAR-07's DSR is
`trials_so_far + 1`: this line counts as a trial too, so `N ≥ 1` on the first. The deflation grows as
the project searches. A number quoted in `docs/RESULTS.md` with no line here does not exist
(`test/test_results.py`).

Each field, exactly. Every line ends with `\n` (never `\r\n`), the file is UTF-8, and no field holds a
tab or a line break (in `note` each is replaced by one space; in any other field it is refused).

- `config_hash`: the 16 hex digits of HAR-01. `date`: the run's date as `YYYY-MM-DD`, given by the
  caller, since the harness never reads the clock.
- `horizon`: the number of trading days, e.g. `5`; empty when the run failed before it had one.
- `metric`: the metric's name, e.g. `IC`, free text without a tab or line break.
- `mean`: the fold-axis mean of HAR-08, as the shortest text that reads back as itself (`0.02`);
  NaN and infinity are refused; empty when the run has no number, in which case `note` is not empty.
- `dispersion`: both axes of HAR-08, as `folds: M ± S [LOW, HIGH] n=K; groups: M ± S [LOW, HIGH] n=K;
  undefined_cells=U`, numbers written as in `mean`, an axis with no defined value as `folds:
  undefined`, an sd that is undefined as `undefined`, and `; fits names` appended when R-014's flag is
  set. Empty when the run has no number.
- `trials_so_far`: the integer above. `note`: free text, empty for an ordinary run.

A line is appended after the file's header and last line break are checked: a file with another
header, or whose last line has no line break, is refused and left as it was. A missing file is
created with its header.

Runs that fail, crash or are abandoned still append a line, with the failure in `note`. A deleted
line is a falsified trial count; the file's history is the record.

## HAR-10 The synthetic market comes first

`neonrain/harness/synthetic.py` generates fake prices for `N` tickers over `T` dates from a seed,
with a planted edge: a feature correlated with the forward return at a chosen strength `ρ`, a chosen
market factor, a chosen cross-sectional volatility, and an option to delist the worst performers (so
the survivorship test of 1.6 has something to catch). Everything in phase 1 is tested on it, because
it is the only market where the right answer is known.

The model, exactly (J-013). Tickers `T000` … on a calendar of weekdays from 2000-01-03; every close
starts at 100. For each date *t* and ticker *i*, from one `numpy.random.default_rng(seed)` drawn in
the order market, feature, noise, all standard normal:

- the **edge** feature `f(i,t)`, known at the close of *t* (its stamp is *t*, HAR-12);
- the next day's log return `log(P(i,t+1) / P(i,t)) = μ + σ_m·m(t+1) + σ_x·(ρ·f(i,t) + √(1−ρ²)·z(i,t+1))`,
  where `μ` is the market drift, `σ_m` the market volatility, `σ_x` the cross-sectional
  (idiosyncratic) volatility, and every ticker has a market beta of one;
- with delisting on, a ticker whose close falls below the chosen fraction of 100 is delisted that
  day: that close is its last price and its last eligible date, and it has no rows after.

So `ρ` is the correlation between the edge and the next day's idiosyncratic return; against an
*h*-day return it is about `ρ/√h`, since only the first day of the window carries it.

Required behaviours: at `ρ = 0` every metric sits inside its noise band across 100 seeds; at the
planted `ρ` a linear model recovers it; the harness's own numbers on a fixed seed are the goldens.

## HAR-11 Determinism

Given the same inputs, config and seed, a run produces byte-identical output. Every source of
randomness takes the seed from the config: data order, group assignment, model initialization,
dropout, and any sampling. No call to a global random state. Floating-point reductions are over
sorted keys, so a frame's row order cannot change a number.

## HAR-12 Every feature carries a provenance stamp, and the harness checks it

A feature column `f` is accompanied by a column `f_stamp` holding, for each (ticker, date) cell, the
**maximum timestamp of any input row used to compute it**. The stamp's type says what kind of
feature it is, and with it the rule:

- **A price feature**: `f_stamp` is a `Date`, the trading date of the latest close used. It is
  refused when later than the cell's date *t* (the close of *t* itself is known at *t*).
- **A news feature**: `f_stamp` is a `Datetime` without a time zone, in UTC, the latest story
  publish time used (NL-04). It is refused at or after the **cut** of *t*: *t* at 00:00 UTC plus
  the run's **news cutoff time**, a time of day UTC that the caller gives (`cutoff`, a `datetime.time`
  without a time zone). A stamp equal to the cut is refused. The harness fixes no cutoff time: which
  one is a decision of phase 5 (R-008, NL-04), and until the run says one, a `Datetime` stamp is refused
  as a layout fault rather than checked against a guess.
- **No stamp where there is a value**: a cell whose stamp is null while its feature value is not null
  is refused (a stamp that says nothing proves nothing). Where the value is null (nothing was
  computed, e.g. a warm-up) the stamp may be null, and the cell is not checked.
- Any other stamp type is refused as a layout fault.

`check_stamps(features, cutoff=None)` and `check_market` do this and raise `StampRefused`, a
`ValueError`, never return a boolean. The refusal **names the feature and the cell**: the first
feature in ascending name order that has an offending cell, and within it the first cell by
(ticker, date) ascending; the message is `feature 'f' refused at cell (TICKER, YYYY-MM-DD): <reason>`,
with ` (and N more cells)` appended when N > 0 others of that feature are also offending. The
reason is `stamp S is after the cell's date`, `stamp S is at or after the news cut`, or `value has
no stamp`. (J-013: this read "at or after" for both, which would have refused every honest price
feature.)

This is the mechanical half of HAR-04: a leak becomes a type error rather than a suspiciously good
number. The statistical checks of 1.6 remain as the second line, because a stamp can be computed
wrongly: the label-shuffle test (permute labels within each date; every metric must collapse to
chance), the planted-leak test (a feature deliberately built from `t+1` must be refused by the stamp
check and, if the check is disabled, must show impossibly high accuracy), and the mirror test
(R-015c).

## HAR-13 What makes a result reportable

All of: a trials line (HAR-09); both axes' dispersion (HAR-08); the three cost levels (HAR-06); the
dropped-cell counts (HAR-02); the findings it carries cited by number (P-03); and the goldens
unchanged if the harness was touched (R-002). A result missing any of these is a draft, and
`docs/RESULTS.md` does not hold drafts.
