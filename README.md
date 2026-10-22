# Neon Rain

A market-prediction research project that refuses to fool itself.

Neon Rain trains a non-LLM neural network to predict equity moves at four horizons (3 trading days,
1 week, 1 month, 3 months) from prices, technical indicators and news, and holds every claim it makes
to a backtesting harness that was built, adversarially tested and frozen before the first model
existed. The harness is the product as much as the model: walk-forward, purged and embargoed, costs
included, every trial counted, every prediction timestamped before its outcome is known. A model that
cannot beat the harness's dumb baselines out of sample is a finding, reported as such, never a
number tuned until it looked good.

News enters as a feature, not a model: a pinned Claude Haiku scorer reads each story once, writes
`(ticker, score, confidence)` to an append-only ledger with the story's publish time, and never runs
again on that story. The predictor itself is a plain network over tabular and sequential features.

Maintainer: Ghost (GitHub: ghost-in-the-kernel). Runs in the cloud for now: no CI, no local runs (see
theGhost.md R-003). The roadmap is `docs/ROADMAP.md`; the decisions are `theGhost.md`; agents start at
`CLAUDE.md`.
