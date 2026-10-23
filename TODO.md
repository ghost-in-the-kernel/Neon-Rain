# TODO: the open items, in order

The roadmap as a chain: items are done in this order, never out of it, and an item that cannot be
done as written stops the chain and goes to Ghost. Each item's plan is its step in docs/ROADMAP.md
§6, by the same number; its check is the roadmap's, copied here. A done item moves to `docs/DONE.md`
with its number kept. `test/test_todo.py` (phase 0.5) holds this file: headings in numeric order,
and the first open item has a check.

## Phase 0: founding

### 0.2 Ghost's founding decisions

Check: `test/test_ghost.py` passes and no phase-1 step cites a `proposed` decision. Waiting on
Ghost: R-011 (license) and R-016 (data and artifacts through GitHub, proposed from 0.3's
measurement; it supersedes R-010). R-001 is in force (Python, 2026-10-22).

### 0.4 Artifact store and data repository (R-016, waiting on Ghost)

Check: `ghost-in-the-kernel/neon-rain-data` and `neon-rain-artifacts` exist; `scripts/fetch/artifacts.py`
round-trips a 1 MB file by content hash through the artifacts repository.

## Phase 1: the harness

Nothing under `neonrain/models/` or `neonrain/baselines/` begins until 1.6 passes (R-002).

### 1.7 Freeze

Check: `harness/goldens/` written from the synthetic market; a harness change after it is a commit
with every golden identical or a decision saying why not; `trials.HARNESS_VERSION` becomes `"1"`
(HAR-01).

### 1.8 Tithe pass 1

Check: AGENT.md re-measured; a fresh-agent trial run under R-020.

## Phase 2: real data

## Phase 3: baselines

## Phase 4: the network

## Phase 5: news

## Phase 6: the news-augmented model and the ablations

## Phase 7: the forward test
