# Neon Rain roadmap: a market-prediction model that refuses to fool itself

**Name: Neon Rain** (Ghost, 2026-10-22). Repository: `ghost-in-the-kernel/neon-rain`, private.

**Status: proposed** (2026-10-22), written from the conversation that founded the project and the
lessons of Suite Builder and Katana as recorded in their `theGhost.md`, `docs/GHOST-IN-THE-KERNEL.md`
and `docs/ROADMAP.md`. Where this document states a number from the literature it names the source;
where it states an estimate it says so. Nothing here has been measured yet; phase 0 measures.

This is a plan, not a decision log. When a phase is built, its section shrinks to a ten-line header
naming the decisions it produced and what is left (Suite Builder lesson T-08), and the decisions
live in `theGhost.md`.

---

## 0. The product, in three sentences

Neon Rain trains a non-LLM neural network to predict, for every stock in a universe on every trading
day, the direction and cross-sectional rank of its return over the next 3 days, 1 week, 1 month and
3 months, from prices, indicators and news. Every claim it makes passes through a backtesting harness
built and adversarially tested before the first model, walk-forward in time and held out by ticker
group, costs included, trials counted, dispersion reported with every mean. News enters through a
pinned Claude Haiku scorer that writes once to an append-only, publish-time-keyed ledger; the
predictor itself never calls a model.

The thesis to hold: **a harness that cannot be fooled, and whatever the model turns out to be worth
under it.** The thesis to refuse: a backtest that looks good. The honest result may be that nothing
beats the tree baseline after costs; that is a result, written up as one.

---

## 1. What is settled: facts the roadmap stands on

- **F-01** Daily equity returns carry little predictable signal; the cross-sectional literature
  (momentum, reversal, value) finds effects measured in basis points per month that decay as they are
  published. Source: the factor-zoo literature (Harvey, Liu & Zhu 2016 on the multiple-testing
  problem; Hou, Xue & Zhang 2020 on replication). Implication: the harness must count trials (R-005).
- **F-02** Random k-fold on overlapping time-series labels leaks; walk-forward with purging and an
  embargo is the standard remedy (López de Prado, *Advances in Financial Machine Learning*, 2018,
  ch. 7 and 11; the deflated Sharpe ratio, Bailey & López de Prado 2014). Held by R-005.
- **F-03** Gradient-boosted trees are the empirical winner on tabular financial features in most
  published comparisons (Gu, Kelly & Xiu 2020, *Empirical Asset Pricing via Machine Learning*, where
  trees and shallow networks tie and both beat linear models). Implication: LightGBM is the baseline
  the network must beat (R-007).
- **F-04** News sentiment has real but short-lived predictive content, strongest at the 1–5 day
  horizon and decaying by a month (Tetlock 2007 on media pessimism; the FNSPID dataset paper, Dong et
  al. 2024, which pairs 15M+ timestamped financial news items with tickers). Implication: the news
  features are expected to help the short horizons and do little at three months; that is the
  ablation's prediction, written before the ablation (R-008).
- **F-05** Survivorship bias in free daily-price sources is real: a universe built from today's
  listings omits every name that was delisted, which inflates every backtest. Point-in-time
  constituent lists are mostly paid. Implication: the universe file records what it can and
  `docs/FINDINGS.md` records what it cannot (R-006).
- **F-06** Claude Haiku 5.5 is listed at $0.10 per million input tokens and $0.50 per million
  output tokens (platform.claude.com/docs/en/models/overview, read 2026-10-22). A thousand-token
  story with a hundred-token structured answer is about $0.00015; a million stories is about $150.
  Implication: scoring once into a ledger is affordable; scoring on every run is waste (R-008).
- **F-07** This session's shell reaches package registries and GitHub through an allowlist; other
  hosts are usually refused (observed in this workspace). Implication: which data sources and
  artifact stores are reachable is step 0.3's measurement, not an assumption; a source that is not
  reachable from here is fetched by Ghost and attached, or replaced.
- **F-08** The organization's GitHub Actions minutes are reserved for other projects and Ghost's
  desktop is not stable enough to run on (Ghost, 2026-10-22). Held by R-003.

---

## 2. Principles carried from Suite Builder and Katana

Each is a rule the project enforces by a test or a document from its first commit, not advice.

- **P-01 The oracle before the thing it checks.** The harness is adversarially tested and frozen
  before any model trains (R-002). Katana P-01; Suite Builder's bench arrived late and had to refuse
  rules retroactively.
- **P-02 Goldens are the only definition of done for a refactor.** A change to the harness, the
  features or the data pipeline that is not meant to change results lands as its own commit with
  every golden identical (R-002). Katana P-02.
- **P-03 Findings before claims.** A bias the data carries, a baseline the model failed to beat, a
  leak the adversarial test found: each is written to `docs/FINDINGS.md` before any result that
  depends on it is reported. Katana P-03.
- **P-04 One shape until it is proven.** One network, one feature table, until it beats the tree at
  one horizon out of sample (R-009). Katana P-04.
- **P-05 Decisions numbered, with supersession checked by a test.** Katana P-05; `test/test_ghost.py`.
- **P-06 Plans shrink into decisions.** A built phase becomes a ten-line header. T-08.
- **P-07 Every number has a trials line and a dispersion.** No metric is reported without the count
  of trials that produced it (R-005) and its spread across time folds and ticker groups (R-014). New
  here; the financial analogue of "a check that cannot fail is not a check."
- **P-08 One canonical word per concept, from the first file.** `docs/GLOSSARY.md` before the second
  source file; a test holds the docs to it. Katana P-08.
- **P-09 The routing table is the front door.** `CLAUDE.md` is a table from task to the two to five
  files to open. Katana P-09; Suite Builder's best artifact.
- **P-10 Ratchets only where there is debt.** T-07.
- **P-11 Proven by a run, not on paper.** A feature family is in the model when its ablation ran
  through the harness and its trials line exists, not when its code merged. Katana P-11.
- **P-12 The only model in the pipeline is the scorer, pinned, run once, ledgered.** The predictor
  imports no model client; the scorer is the one module that does; its model ID and prompt version
  are written on every ledger row (R-008). The analogue of Katana R-004 for a project where a model
  does run, bounded to one place.
- **P-13 Nothing proprietary or license-restricted enters git.** Raw data is regenerated by script
  with its license in the manifest (R-006). Katana P-13.
- **P-14 The agent's environment is a first-class deliverable.** One commit in eight and a pass per
  phase (R-012), with metrics that ratchet (`docs/AGENT.md`). Ghost's finding in Suite Builder.
- **P-15 No order is ever placed from this repository.** R-013.

---

## 3. Architecture

### 3.1 The pipeline

```
scripts/fetch/   →  data/ (ignored)  →  neonrain/universe   →  neonrain/features  →  neonrain/targets
                                                                      ↑
news feed  →  neonrain/scorer (Haiku, pinned)  →  ledger/news.parquet (append-only, publish-time keyed)

neonrain/features + neonrain/targets  →  neonrain/harness (split · cost · metrics · trials)
                                                 ↓                       ↓
                                        neonrain/baselines        neonrain/models (one network)
                                                 ↓                       ↓
                                        harness/goldens/          docs/RESULTS.md (mean ± dispersion, trials line)
                                                                         ↓
                                                               ledger/predictions.parquet (phase 7: timestamped before outcome)
```

Each arrow is a pure function of what is to its left plus a date; nothing reads the clock except the
fetch scripts and the forward test.

### 3.2 The two ledgers, and why they are append-only

**The news ledger** (`ledger/news.parquet`, `docs/LEDGER.md` NL-01 onward) is the scorer's memory:
story hash, publish time, source, ticker, score (1–10), confidence, reason, model ID, prompt
version, scored-at time. Append-only; a new prompt version adds rows and never edits. Features read
it with a publish-time cut, so a feature for date *t* sees only rows with publish time < *t*'s close.

**The prediction ledger** (`ledger/predictions.parquet`, phase 7) is the forward test: every
prediction the model makes on a live date is appended with the model's weight hash, the feature
snapshot hash and the time, before the horizon elapses; a script scores it after. This is the one
evaluation no backtest can fake, and the project's proof if it ever has one.

Both are Katana's proof ledger pointed at a different kernel: what was known, when, and what was
claimed from it.

### 3.3 Module layout

`docs/modules.json` says what each module is for and what it may import; `test/test_modules.py`
refuses anything else. Adding a module is a decision (Katana R-043's rule applies here).

| Module | Purpose | May import |
| --- | --- | --- |
| `neonrain/universe` | which tickers exist on which dates; delistings where known | nothing of ours |
| `neonrain/features` | the feature table: price-derived, indicator, and news features, per ticker per day | `universe`, the ledger reader |
| `neonrain/targets` | the four horizons' labels, direction and rank | `universe` |
| `neonrain/harness` | splits (time × ticker group), cost model, metrics, the trials file | `features`, `targets` |
| `neonrain/baselines` | zero, momentum, reversal, LightGBM | `harness` |
| `neonrain/models` | the one network, liftable one way (R-025) | nothing of ours |
| `neonrain/training` | trains the network and runs it through the harness | `models`, `harness`, `features`, `targets` |
| `neonrain/scorer` | the Haiku scorer and the ledger writer; **the only module that imports a model client** | nothing of ours |
| `neonrain/ledger` | readers for both ledgers, with the publish-time cut | nothing of ours |

Rules: **MOD-01** only `scorer` imports a model client. **MOD-02** `harness` never imports `models`,
`baselines` or `training` (the referee does not read the players' code; Katana MOD-05). **MOD-03** no module
imports a broker or order client (R-013). **MOD-04** `features` reads the news ledger only through
`ledger`'s cut reader. **MOD-06** `models` imports nothing of ours and only `training` imports it
(R-025).

### 3.4 The network (phase 4; the shape is R-009's decision, recorded when phase 4 opens)

Candidates, to be chosen by one decision after the tree baseline is frozen: (a) a multilayer
perceptron over the per-day cross-sectionally normalized feature row, four heads (the Gu–Kelly–Xiu
shape; simplest, and the one that tied trees in F-03); (b) a temporal convolution or GRU over a
60-day window of per-ticker features, four heads; (c) (a) plus a small cross-sectional attention
over the day's universe, refused until (a) or (b) has beaten the tree (R-009). Training is pooled
across tickers; the loss is per-horizon classification for direction and pairwise ranking for rank.

### 3.5 What is deliberately not built

No price-level or raw-return prediction (R-004). No intraday data. No options, futures or crypto.
No live trading (R-013). No architecture search before a win (R-009). No notebook as a source of
truth (R-001). No CI (R-003).

---

## 4. Meta-architecture: what holds the project together for a person and an agent

| Document | What it holds | Test |
| --- | --- | --- |
| `theGhost.md` | every decision, numbered | `test/test_ghost.py` |
| `docs/ROADMAP.md` | this plan; shrinks as phases close | |
| `docs/HARNESS.md` | the harness contract, HAR-01 onward | `test/test_harness_doc.py` |
| `docs/LEDGER.md` | both ledgers' schemas, NL-01 onward | `test/test_ledger.py` |
| `docs/FINDINGS.md` | biases, leaks and failures, NR-F-01 onward, written before the result they qualify | `test/test_results.py` (a result cites its findings) |
| `docs/RESULTS.md` | every reported number: horizon, metric, mean, dispersion, trials line, findings cited | `test/test_results.py` |
| `docs/GLOSSARY.md` | one word per concept | `test/test_glossary.py` |
| `docs/AGENT.md` | the agent's environment: contract and ratcheted metrics | `test/test_metrics.py` |
| `docs/JOURNAL.md` | what happened while the work was done, fixed fields | |
| `docs/modules.json` | modules and their imports | `test/test_modules.py` |
| `data/MANIFEST.md` | every dataset: source, license, fetch command, hash | `test/test_manifest.py` |
| `harness/trials.tsv` | every evaluation run | `test/test_results.py` |
| `TODO.md` | the open items, in order | `test/test_todo.py` |
| `CLAUDE.md` | the routing table | mandatory-context word count in `AGENT.md` |

The doc tests are plain `pytest` files with no fixture beyond the repository; `scripts/precommit.sh`
runs them, the unit tests, and the import rule, and prints a line the agent quotes in the commit.

---

## 5. The navigation tithe

Every eighth commit is a tithe (R-012): no result changes, the agent's environment improves. Every
phase ends with a tithe pass, one agent in one session following `docs/rules/tithe.md`: re-measure
`docs/AGENT.md`, fix what agents ran into, and score the phase's debriefs, each "Opened" list read
against the routing row its task matched (by file, in order; `CLAUDE.md` does not count). The
separate fresh-agent trial of R-020 is retired (R-023).

| Metric | Phase 0 target | Why it matters to the agent |
| --- | --- | --- |
| Mandatory context (words) | < 1,200 | every task pays it |
| Fast loop (s) | < 30 | unit and doc tests, no data, no model; run after every edit |
| Full check, `precommit.sh` (min) | < 10 | paid before every push while there is no CI (R-003) |
| Largest source file (lines) | < 400 | fits a read without paging |
| Files a routing row opens | ≤ 5 | first five reads decide the task |
| Decisions without `See also` | 0 | links find what grep misses |
| Results without a trials line | 0 | P-07 |
| Results without dispersion | 0 | R-014 |
| Datasets without a manifest line | 0 | R-006 |
| Docs lines per source line | < 1.5 | records left out; arms as phases 2 to 4 add source (R-024) |

---

## 6. Phases

Each phase has steps; each step has a check that fails before the work and passes after; each phase
names the decisions it records and ends with a tithe pass. Durations are estimates for one engineer
working with agents in cloud sessions, and are the team's own.

### Phase 0: founding (a few days)

0.1 **Repository and documents.** This commit: `README.md`, `CLAUDE.md`, `theGhost.md` (R-001 to
    R-014), this roadmap, `GLOSSARY.md`, `AGENT.md`, `JOURNAL.md`, `TODO.md`, `.gitignore`.
    *Check:* `git log` shows Ghost as author; the files exist.
0.2 **Ghost's founding decisions.** R-001 (Python), R-010 (artifact store, after 0.3; since
    superseded by R-016) and R-011 (license) move from `proposed` to `in force` or are replaced.
    Nothing in phase 1 starts on a `proposed` entry.
    *Check:* `test/test_ghost.py` passes and no phase-1 step cites a `proposed` decision.
0.3 **Reachability.** From this workspace, with the shell: `pip install` from the lockfile; fetch one
    day of daily prices from each candidate source (Stooq, Yahoo via `yfinance`, Tiingo free tier,
    Polygon free tier, a Kaggle mirror on GitHub); fetch one page of GDELT and one of a financial
    news dataset; push a 1 MB file to a GitHub Release and read it back; the same for a Hugging Face
    Hub repository. Record each as reachable or refused in `docs/FINDINGS.md` NR-F-01.
    *Check:* the findings entry exists; every later fetch script names a source that was reachable
    or says Ghost attaches it.
0.4 **Artifact store** chosen by R-010 from 0.3's result; `scripts/fetch/artifacts.py` round-trips a
    file by content hash.
0.5 **The doc tests and `scripts/precommit.sh`.** `test_ghost`, `test_glossary`, `test_todo`,
    `test_modules` (on an empty `modules.json` with the eight modules declared), `test_manifest`
    (empty manifest passes), `test_supply_chain` (no workflow file, lockfile-only). `scripts/precommit.sh`
    runs them and the fast loop and prints the AGENT.md line.
    *Check:* every doc test passes on the empty project; `test_ghost` fails on a deliberately
    conflicting pair, then passes when one is superseded.
0.6 **Tithe pass 0:** the fresh-agent trial on the empty project; its task and pass condition are
    in J-012, written after the run (R-020).

Decisions recorded: R-001, R-010, R-011 settled; R-002 to R-009 and R-012 to R-014 in force.

### Phase 1: the harness, adversarially tested and frozen (about two weeks)

Nothing under `neonrain/models/` or `neonrain/baselines/` begins until 1.6 passes (R-002).

1.1 **Synthetic market.** `neonrain/harness/synthetic.py`: a generator of fake daily prices for *N*
    tickers over *T* days with a known, planted, tunable edge (a feature that predicts the forward
    return with a chosen correlation) and a known cost. Everything in phase 1 is tested on it, so the
    harness is proven on a market where the truth is known before it touches real data.
    *Check:* the generator is seeded and deterministic; the planted edge is recoverable by a linear
    model at the chosen strength.
1.2 **Targets.** `neonrain/targets.py` per R-004: four horizons, direction and rank, excess of the
    universe median.
    *Check:* `test/test_targets.py` on a hand-built ten-day, three-ticker series.
1.3 **Splits.** `neonrain/harness/split.py`: walk-forward with purge and embargo ≥ 63 days (R-005)
    × seeded ticker groups (R-014).
    *Check:* no training label's horizon window overlaps any test date; every ticker is in exactly
    one group; the grid is reproducible from a seed.
1.4 **Cost model and metrics.** Per-trade cost as a parameter (basis points of notional, with a
    default to be justified in `docs/HARNESS.md`); metrics: accuracy and balanced accuracy on
    direction, rank correlation (Spearman) on rank, and a long–short decile portfolio's return,
    Sharpe and deflated Sharpe after costs; each reported as mean ± dispersion across both axes.
    *Check:* a zero-edge strategy on the synthetic market reports a deflated Sharpe inside its noise
    band after costs across 100 seeds.
1.5 **The trials file.** Every harness run appends to `harness/trials.tsv`; `docs/RESULTS.md`'s test
    refuses a number with no line.
1.6 **Adversarial tests** (`test/test_harness_adversarial.py`), each a check that must turn red:
    a feature that peeks one day ahead is caught (its accuracy is impossibly high and the leak
    detector, which shifts the feature forward and watches the metric collapse, flags it); a
    universe with delisted names removed is caught (the synthetic market delists losers and the
    biased universe shows the inflation); a label that crosses the embargo is caught; a model that
    memorizes a ticker (a lookup table of name → mean return) shows the R-014 dispersion signature;
    the harness's own metric code agrees with an independent, deliberately naive reimplementation
    on the synthetic market (the mirror test: the two are written by different agents from the
    contract, not from each other).
    *Check:* every test red on the broken input, green on the honest one.
1.7 **Freeze.** `harness/goldens/` written from the synthetic market; `docs/HARNESS.md` HAR-01 to
    HAR-nn record the contract. From here, a harness change is a commit with every golden identical
    or a decision in `theGhost.md` saying why not.
1.8 **Tithe pass 1.**

Decisions recorded: the cost default; the embargo length; the group count *k*; HAR-01 onward.

### Phase 2: real data (about two weeks)

2.1 **Universe.** A liquid US equity universe (a few hundred to a thousand names) with dates in and
    out, delistings where the source gives them; `docs/FINDINGS.md` NR-F records the survivorship
    gap honestly.
2.2 **Daily prices.** OHLCV from the source 0.3 found reachable, fetched by script, manifested
    (R-006), ten or more years.
2.3 **Price-derived features**, one family at a time, each with a glossary term: returns at several
    lookbacks, realized volatility, volume ratios, and the standard indicators (RSI, MACD, moving
    average ratios), each computed by a pure function from prices alone with a unit test against a
    hand-computed window. The indicators are kept because Ghost asked for them and because the
    ablation will say what they are worth; the expectation (F-03) is that the network learns most of
    them from returns.
2.4 **Cross-sectional normalization** per day (rank or z-score within the universe), so no feature
    carries the market level.
2.5 **The feature table** cached to the artifact store by content hash; a fetch rebuilds it.
2.6 **Tithe pass 2.**

### Phase 3: baselines, frozen (about one week)

3.1 Zero, momentum (12-1), short-term reversal (1-month), each through the harness at all four
    horizons, mean ± dispersion, trials lines.
3.2 LightGBM on the full feature table, walk-forward, with a small fixed hyperparameter set chosen
    once and recorded (no search; a search is trials and is counted if it happens).
3.3 `harness/goldens/baseline_*.json`; `docs/RESULTS.md` gets its first honest table. The
    expectation, written now: the baselines are near chance at three months and show a small edge
    at short horizons that may not survive costs.
3.4 **Tithe pass 3.**

### Phase 4: the network (about three weeks)

4.1 **The shape decision** (R-009): one of §3.4's candidates, recorded in `theGhost.md` with its why.
4.2 **The model**, one file in `neonrain/models/` (nothing of ours imported, R-025), pooled training
    in `neonrain/training/`, four heads, early stopping on the walk-forward validation fold only
    (never on test); its weights beside it, or in `neon-rain-artifacts` by hash when large.
4.3 **The run** through the harness: mean ± dispersion at all four horizons against the tree.
4.4 **The write-up** in `docs/RESULTS.md`, whichever way it went. If the network does not beat the
    tree at any horizon, `docs/FINDINGS.md` gets the entry and the project's honest state is "the
    tree is the model" until something changes it.
4.5 **Tithe pass 4.**

### Phase 5: news (about three weeks)

5.1 **The feed.** A news source with publish timestamps and, ideally, ticker tags, found reachable in
    0.3 (FNSPID, GDELT, or a feed Ghost attaches); fetched by script, manifested, never committed.
5.2 **The scorer** (`neonrain/scorer/`, R-008): the prompt (versioned, in the repository), the
    structured output schema, the pinned model ID, temperature 0, the ledger writer. A story is
    scored once per prompt version.
    *Check:* `test/test_ledger.py`: append-only; a row with publish time after its own scored-at time
    is refused; re-scoring under the same version is a no-op.
5.3 **A calibration set.** Two hundred stories hand-labelled by Ghost (bullish/bearish/neutral,
    ticker), used to measure the scorer's agreement before any feature is built from it; recorded in
    `docs/RESULTS.md` as the scorer's own number. A cheaper non-LLM scorer (FinBERT) is run on the
    same set as the scorer's baseline.
5.4 **Scoring the history.** The feed's history through the scorer into the ledger, in batches, with
    the cost logged in the journal against F-06's estimate.
5.5 **News features** through `ledger`'s publish-time cut: per ticker per day, the count, mean score,
    confidence-weighted score and recency-decayed score over 1, 5 and 21 days.
5.6 **Tithe pass 5.**

### Phase 6: the news-augmented model and the ablations (about two weeks)

6.1 The tree and the network re-run with news features; mean ± dispersion; trials lines.
6.2 Ablations one family at a time: prices only; prices + indicators; prices + news; everything.
    F-04's prediction (news helps the short horizons, not the long) is checked and the result
    written either way.
6.3 `docs/RESULTS.md` becomes the project's result table; `docs/FINDINGS.md` its caveats.
6.4 **Tithe pass 6.**

### Phase 7: the forward test (one quarter, elapsed)

7.1 **The prediction ledger** (§3.2): on each trading day, a session scores the live feature row for
    the universe and appends predictions with the weight hash and the time. This is the one place the
    project reads the clock.
7.2 **Scoring**, after each horizon elapses, into `docs/RESULTS.md`'s forward-test table, with the
    backtest's number beside it. A forward test that disagrees with the backtest is the most valuable
    finding the project can produce.
7.3 **The decision** (a new R-nnn, Ghost's): what the forward test showed and what, if anything,
    happens next. Trading real money is a separate decision with its own why (R-013).

---

## 7. Trial agents and roles

As on Katana: Ghost as program director; Claude Fable for decisions, contracts, trial designs and the
adversarial tests' design; Claude Opus for implementation; Claude Haiku inside the pipeline as the
scorer, and nowhere else. The mirror test in 1.6 is written by an agent that has not seen the
harness's metric code, by design.
