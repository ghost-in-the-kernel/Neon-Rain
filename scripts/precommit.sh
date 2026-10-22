#!/usr/bin/env bash
# The check before a push: there is no CI (R-003, AGT-07), so this is the gate. Quote its last line in the commit.
# In order: the fast loop, ruff (R-015b), mutation testing with every survivor explained (R-015a), the metrics.
set -uo pipefail
cd "$(dirname "$0")/.."
bin=.venv/bin
started=$(date +%s)

stop() { echo "precommit: refused at $1"; exit 1; }

loop_started=$(date +%s.%N)
$bin/pytest || stop "the fast loop"
fast_loop=$(python3 -c "print(round($(date +%s.%N) - $loop_started, 2))")

$bin/ruff check . || stop "ruff (R-015b)"

rm -rf mutants
$bin/mutmut run > /dev/null 2>&1 || stop "mutmut run (rerun it by hand to see why)"
results=$($bin/mutmut results --all true 2>/dev/null || $bin/mutmut results)
total=$(grep -c ': ' <<< "$results")
killed=$(grep -c ': killed$' <<< "$results")
$bin/python scripts/survivors.py <<< "$results" || stop "an unexplained survivor (R-015a, docs/MUTATION.md)"

full_check=$(python3 -c "print(round(($(date +%s) - $started) / 60, 2))")
$bin/python scripts/metrics.py --fast-loop "$fast_loop" --full-check "$full_check" || stop "a metric that regressed"

echo "precommit: passed; fast loop ${fast_loop}s, mutants ${killed}/${total} killed, the rest explained, ${full_check} min"
