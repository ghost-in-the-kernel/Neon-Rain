# Data manifest

Every dataset: source, license, fetch command, date range, hash as last fetched (R-006). A dataset with no line here fails `test/test_manifest.py`.

| Dataset | Source | License | Fetch | Range | Hash |
| --- | --- | --- | --- | --- | --- |
| wiki-prices-raw | Quandl WIKI/PRICES via Nasdaq Data Link, the export (`qopts.export=true`), snapshot 2026-02-03 | public domain as described; accepted for private research (data D-002) | `neon-rain-data` `raw/wiki/`: five parts, `cat WIKI_PRICES.zip.part-* > WIKI_PRICES.zip` | the frozen feed (to 2018-04); the sample 1998-01-02 to 2017-11-07 (R-026) | sha256 d1b89242ebaf629e541f2a3c77c718f01819fa72dc687a30dadc764c8983e3f6 |
| wiki-prices | the sample of `wiki-prices-raw`, one parquet file per year, columns as exported, rows sorted by ticker then date | public domain as described; accepted for private research (data D-002) | `python scripts/fetch/wiki.py <neon-rain-data clone> <scratch dir>` writes `wiki/prices/<year>.parquet` (each under 100 MB) and `wiki/prices/index.tsv` (year, file, SHA-256) in `neon-rain-data`, refusing the raw parts unless they hash to the row above | 1998-01-02 to 2017-11-07 (R-026) | sha256 867d708b43bd772a8f820211885d9e6603b3aaaa602188ce115b950128370a65 (of `index.tsv`) |
| feature-table | built from `wiki-prices` (index sha256 867d708b43bd772a8f820211885d9e6603b3aaaa602188ce115b950128370a65): the four price families (returns, volatility, volume ratios, indicators) each ranked within the day's universe (`neonrain/features/table.py`, `normalize.py`, `membership.py`), 34 columns, one row per universe cell of the raw-ranked universe (`prices.universe`, J-079; the baselines' universe), one parquet file per year | derived from `wiki-prices`; public domain as described, accepted for private research (data D-002); kept in the private artifact store only, never in this repository (R-006) | `PYTHONPATH=. python scripts/fetch/feature_table.py <neon-rain-data clone> <scratch dir>` writes `<year>.parquet` (each under 100 MB) and `index.tsv` (year, file, SHA-256), the same bytes each run; the files and the index are stored with `scripts/fetch/artifacts.py put`, each by its own hash (index first in the section below) | 1998-04-02 to 2017-11-07 (the universe starts 63 sessions after the first price row) | sha256 ee1beff8adaa2565d137acb5bc72fddc8064b1094d3ce60775e0db4544eeb225 (of `index.tsv`; built with polars 2.0.0, whose version is written into every file, so the bytes hold only with it) |

## The artifact store (R-016 b)

Artifacts (large weights, R-025; anything a run produces that is too big for this repository) live in the
private repository `ghost-in-the-kernel/neon-rain-artifacts`, one plain git file each, named by its SHA-256:
`<first two hex characters>/<64-character hash>` on branch `main`. This repository records the hash a result depends
on, never the bytes. The clone is a cache at `$NEONRAIN_ARTIFACTS_CLONE` or `~/.cache/neon-rain/artifacts`, outside
this repository; the remote is `$NEONRAIN_ARTIFACTS_REMOTE` or the GitHub URL. `scripts/fetch/artifacts.py put FILE`
stores a file (commit as Ghost, push) and prints its hash; storing bytes already there is no commit.
`scripts/fetch/artifacts.py get HASH DEST` copies a file out and refuses, writing nothing, if the bytes do not hash to
the name. Files are under 100 MB (R-016 a). Held by `test/test_artifacts.py`.

**A multi-file artifact is recorded as one row of the table above, by the hash of its index** (the feature table is the
first; a ledger snapshot or weights in parts follow it). **The feature table's row** (hash of its `index.tsv`, as `wiki-prices` is), not in
this section: it is a dataset the loaders and `test/test_manifest.py` hold to six columns, its index has the same
`year<TAB>file<TAB>sha256` layout, and the one hash names the whole table, since the index names every file's hash. The
row names its input (the `wiki-prices` index hash) and its code (the files it names; the commit that records the row
is the version of that code); a different input hash, a different polars version or a changed parquet setting gives a
different hash, so the row is stale on any of them. To fetch it: `artifacts.py get <index hash> index.tsv`, then `get`
each file's hash from that index; `feature_table.py` rebuilds the same bytes from the data repository (TODO 2.5).
