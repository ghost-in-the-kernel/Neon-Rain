# TODO: the open items, in order

The roadmap as a chain: items are done in this order, never out of it, and an item that cannot be
done as written stops the chain and goes to Ghost. Each item's plan is its step in docs/ROADMAP.md
§6, by the same number; its check is the roadmap's, copied here. A done item moves to `docs/DONE.md`
with its number kept. `test/test_todo.py` (phase 0.5) holds this file: headings in numeric order,
and the first open item has a check.

## Phase 0: founding

### 0.2 Ghost's three decisions

Check: `test/test_ghost.py` passes and no phase-1 step cites a `proposed` decision. Waiting on
Ghost: R-011 (license). R-001 is in force (Python, 2026-10-22). R-016 (data and artifacts through GitHub) is proposed from 0.3's measurement.

### 0.4 Artifact store and data repository (R-016, waiting on Ghost)

Check: `ghost-in-the-kernel/neon-rain-data` and `neon-rain-artifacts` exist; `scripts/fetch/artifacts.py`
round-trips a 1 MB file by content hash through the artifacts repository.

### 0.5 The doc tests and `precommit.sh`

Check: every doc test passes on the empty project; `test_ghost` fails on a deliberately conflicting
pair, then passes when one is superseded; `precommit.sh` runs `mutmut` and refuses an unexplained
survivor (R-015); the readability lint of R-015(b) is configured.

### 0.6 Tithe pass 0

Check: the fresh-agent trial opens `CLAUDE.md` first, `docs/modules.json` within three reads, and
changes nothing.

## Phase 1: the harness

## Phase 2: real data

## Phase 3: baselines

## Phase 4: the network

## Phase 5: news

## Phase 6: the news-augmented model and the ablations

## Phase 7: the forward test
