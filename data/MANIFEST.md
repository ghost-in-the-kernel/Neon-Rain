# Data manifest

Every dataset: source, license, fetch command, date range, hash as last fetched (R-006). A dataset with no line here fails `test/test_manifest.py`.

| Dataset | Source | License | Fetch | Range | Hash |
| --- | --- | --- | --- | --- | --- |
| wiki-prices-raw | Quandl WIKI/PRICES via Nasdaq Data Link, the export (`qopts.export=true`), snapshot 2026-02-03 | public domain | `neon-rain-data` `raw/wiki/`: five parts, `cat WIKI_PRICES.zip.part-* > WIKI_PRICES.zip` | the frozen feed (to 2018-04); the sample 1998-01-02 to 2017-12-29 | sha256 d1b89242ebaf629e541f2a3c77c718f01819fa72dc687a30dadc764c8983e3f6 |

## The artifact store (R-016 b)

Artifacts (large weights, R-025; anything a run produces that is too big for this repository) live in the
private repository `ghost-in-the-kernel/neon-rain-artifacts`, one plain git file each, named by its SHA-256:
`<first two hex characters>/<64-character hash>` on branch `main`. This repository records the hash a result depends
on, never the bytes. The clone is a cache at `$NEONRAIN_ARTIFACTS_CLONE` or `~/.cache/neon-rain/artifacts`, outside
this repository; the remote is `$NEONRAIN_ARTIFACTS_REMOTE` or the GitHub URL. `scripts/fetch/artifacts.py put FILE`
stores a file (commit as Ghost, push) and prints its hash; storing bytes already there is no commit.
`scripts/fetch/artifacts.py get HASH DEST` copies a file out and refuses, writing nothing, if the bytes do not hash to
the name. Files are under 100 MB (R-016 a). Held by `test/test_artifacts.py`.
