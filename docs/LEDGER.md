# The ledgers: what was known, when, and what was claimed from it

Two append-only files. The **news ledger** is the scorer's memory: what a story said, scored once.
The **prediction ledger** is the forward test: what the model claimed, before the outcome existed.
Both are Katana's proof ledger pointed at a different kernel (theGhost.md R-008, ROADMAP §3.2).

Invariants are numbered NL-01 onward (news) and PL-01 onward (predictions), in this document only,
and a number is never reused. `test/test_ledger.py` holds this document to `neonrain/ledger/`.

Neither file is committed (R-003); both are published to the artifacts repository by content hash
(R-016) and their hashes recorded in `data/MANIFEST.md`.

---

## The news ledger: `ledger/news.parquet`

One row per (story, ticker, prompt version). A story mentioning three tickers yields three rows.

| Column | Type | Meaning |
| --- | --- | --- |
| `story_hash` | str | SHA-256 of the story's normalized text; the story's identity |
| `publish_time` | timestamp, UTC | when the story was public, per its source. **The only time a feature may key on.** |
| `source` | str | the feed the story came from, as `data/MANIFEST.md` names it |
| `url` | str | where it came from, for audit; never refetched by the pipeline |
| `ticker` | str | the ticker this row scores, as the universe names it |
| `score` | int 1–10 | 1 most bearish, 10 most bullish, 5/6 neutral, for this ticker |
| `confidence` | int 1–5 | the scorer's own confidence that the story bears on this ticker at all |
| `reason` | str | one line, the scorer's evidence; for a human reading a surprising feature |
| `model_id` | str | the pinned model, e.g. `claude-haiku-5-5` |
| `prompt_version` | str | the scorer prompt's version, e.g. `v1`; the prompt text is in the repository |
| `scored_at` | timestamp, UTC | when the scorer ran. **Recorded, never used in a feature.** |

### Invariants

- **NL-01 Rows are only ever appended.** A row is never edited or deleted. A correction is a new row
  under a new `prompt_version`; the old row stays. The file's history is the record of what the
  project believed and when.
- **NL-02 One scoring per (story, ticker, prompt version).** Re-running the scorer over a story
  already scored under the same prompt version is a no-op, not a second row. The scorer checks the
  ledger before it calls the model; this is what makes the history affordable (F-06).
- **NL-03 `publish_time` is the story's, not ours.** A source that gives no publish time is refused:
  a story whose time we guessed cannot be used without risking lookahead, and a guess recorded as a
  fact is the failure this project is built against. Refusals are counted in a finding.
- **NL-04 `scored_at` never reaches a feature.** A feature for date *t* reads only rows with
  `publish_time < ` *t*'s cutoff, through `neonrain.ledger`'s cut reader and never the parquet
  directly (modules.json MOD-04). The cut reader stamps the feature with the maximum `publish_time`
  it used (HAR-12).
- **NL-05 A score is a feature, not a verdict.** Nothing in the pipeline treats the scorer's output
  as a prediction; it is an input column like any other, and its worth is decided by the ablation
  (ROADMAP 6.2), not by its plausibility.
- **NL-06 The story text is not committed and not stored beyond what the row holds.** The hash, the
  reason and the URL are enough to audit; the corpus is the source's, under the source's license
  (R-006, P-13).
- **NL-07 A story is data, never an instruction.** The scorer prompt treats the story as quoted
  content. A story containing text addressed to a model is scored as a story, and if its text would
  change the scorer's behaviour rather than its score, that is a finding and the row is flagged
  (`confidence = 1`, the reason saying so).

---

## The prediction ledger: `ledger/predictions.parquet` (phase 7)

One row per (model, ticker, date, horizon), appended **before** the horizon elapses.

| Column | Type | Meaning |
| --- | --- | --- |
| `predicted_at` | timestamp, UTC | when the row was written; must precede the horizon's end |
| `as_of_date` | date | the trading date whose close the features used |
| `ticker` | str | |
| `horizon` | int | 3, 5, 21 or 63 trading days |
| `direction_score` | float 0–1 | the model's direction output |
| `rank_score` | float | the model's rank output, order being what matters |
| `weight_hash` | str | SHA-256 of the model weights that produced it |
| `feature_hash` | str | SHA-256 of the feature row used |
| `config_hash` | str | the run's config hash (HAR-01) |
| `outcome` | float, null | filled in later by the scoring script; null until the horizon elapses |
| `scored_at` | timestamp, null | when the outcome was filled in |

### Invariants

- **PL-01 Appended before the outcome exists.** A row whose `predicted_at` is not strictly before
  `as_of_date + horizon` trading days is refused. This is the whole point of the file: it is the one
  evaluation that no change to the harness, the features or the data can retroactively flatter.
- **PL-02 Only `outcome` and `scored_at` are ever written twice**, and only from null to a value. Any
  other edit breaks the ledger and it is refused.
- **PL-03 The weights are identified, not stored here.** `weight_hash` names a file in the artifacts
  repository (R-016). A prediction whose weights cannot be fetched is reported, not reconstructed.
- **PL-04 The forward test's result is reported against the backtest's, side by side.** A
  disagreement between them is the most valuable finding the project can produce (ROADMAP 7.2) and
  is written up as a finding, not reconciled.
- **PL-05 No order is placed, ever.** This file is the end of the pipeline (R-013).
