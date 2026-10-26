# Data manifest

Every dataset: source, license, fetch command, date range, hash as last fetched (R-006). A dataset with no line here fails `test/test_manifest.py`.

| Dataset | Source | License | Fetch | Range | Hash |
| --- | --- | --- | --- | --- | --- |
| wiki-prices-raw | Quandl WIKI/PRICES via Nasdaq Data Link, the export (`qopts.export=true`), snapshot 2026-02-03 | public domain as described; accepted for private research (data D-002) | `neon-rain-data` `raw/wiki/`: five parts, `cat WIKI_PRICES.zip.part-* > WIKI_PRICES.zip` | the frozen feed (to 2018-04); the sample 1998-01-02 to 2017-11-07 (R-026) | sha256 d1b89242ebaf629e541f2a3c77c718f01819fa72dc687a30dadc764c8983e3f6 |
| wiki-prices | the sample of `wiki-prices-raw`, one parquet file per year, columns as exported, rows sorted by ticker then date | public domain as described; accepted for private research (data D-002) | `python scripts/fetch/wiki.py <neon-rain-data clone> <scratch dir>` writes `wiki/prices/<year>.parquet` (each under 100 MB) and `wiki/prices/index.tsv` (year, file, SHA-256) in `neon-rain-data`, refusing the raw parts unless they hash to the row above | 1998-01-02 to 2017-11-07 (R-026) | sha256 867d708b43bd772a8f820211885d9e6603b3aaaa602188ce115b950128370a65 (of `index.tsv`) |

## The artifact store (R-016 b)

Artifacts (large weights, R-025; anything a run produces that is too big for this repository) live in the
private repository `ghost-in-the-kernel/neon-rain-artifacts`, one plain git file each, named by its SHA-256:
`<first two hex characters>/<64-character hash>` on branch `main`. This repository records the hash a result depends
on, never the bytes. The clone is a cache at `$NEONRAIN_ARTIFACTS_CLONE` or `~/.cache/neon-rain/artifacts`, outside
this repository; the remote is `$NEONRAIN_ARTIFACTS_REMOTE` or the GitHub URL. `scripts/fetch/artifacts.py put FILE`
stores a file (commit as Ghost, push) and prints its hash; storing bytes already there is no commit.
`scripts/fetch/artifacts.py get HASH DEST` copies a file out and refuses, writing nothing, if the bytes do not hash to
the name. Files are under 100 MB (R-016 a). Held by `test/test_artifacts.py`.
