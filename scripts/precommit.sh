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

# The slow tests (R-024 c): independent files, so one pytest process each, side by side (the box has cores to spare);
# the last process takes every slow test in a file not named above, so a new slow file is run, never left out.
slow_started=$(date +%s)
slow_logs=$(mktemp -d)
named=(test/test_harness_adversarial.py test/test_noise_band.py test/test_the_freeze.py test/test_survivorship_probe.py)
# Each process gets its own temp root: side by side, they raced on pytest's shared `pytest-current` link (J-055).
for n in 1 2 3 4; do mkdir -p "$slow_logs/tmp$n"; done
PYTEST_DEBUG_TEMPROOT="$slow_logs/tmp1" $bin/pytest -m slow test/test_harness_adversarial.py > "$slow_logs/1" 2>&1 & slow_pids=($!)
PYTEST_DEBUG_TEMPROOT="$slow_logs/tmp2" $bin/pytest -m slow test/test_noise_band.py > "$slow_logs/2" 2>&1 & slow_pids+=($!)
PYTEST_DEBUG_TEMPROOT="$slow_logs/tmp3" $bin/pytest -m slow test/test_the_freeze.py test/test_survivorship_probe.py > "$slow_logs/3" 2>&1 & slow_pids+=($!)
PYTEST_DEBUG_TEMPROOT="$slow_logs/tmp4" $bin/pytest -m slow "${named[@]/#/--ignore=}" > "$slow_logs/4" 2>&1 & slow_pids+=($!)
slow_failed=0
for n in 0 1 2 3; do
  wait "${slow_pids[$n]}"; code=$?
  [ "$n" = 3 ] && [ "$code" = 5 ] && code=0  # pytest's 5 is "no tests collected": no other slow file, fine
  [ "$code" = 0 ] || slow_failed=1
done
cat "$slow_logs"/[0-9]
[ "$slow_failed" = 0 ] || stop "the slow tests (the harness on the synthetic market)"
slow=$(( $(date +%s) - slow_started ))

$bin/ruff check . || stop "ruff (R-015b)"

rm -rf mutants
$bin/mutmut run > /dev/null 2>&1 || stop "mutmut run (rerun it by hand to see why)"
results=$($bin/mutmut results --all true 2>/dev/null || $bin/mutmut results)
total=$(grep -c ': ' <<< "$results")
killed=$(grep -c ': killed$' <<< "$results")
$bin/python scripts/survivors.py <<< "$results" || stop "an unexplained survivor (R-015a, docs/MUTATION.md)"

full_check=$(python3 -c "print(round(($(date +%s) - $started) / 60, 2))")
$bin/python scripts/metrics.py --fast-loop "$fast_loop" --full-check "$full_check" || stop "a metric that regressed"

reviewed=$(sed -n 's/^Last review: \([0-9a-f]*\) .*/\1/p' docs/NAVIGATION-LOG.md)
since=$(git rev-list --count "$reviewed..HEAD" 2>/dev/null || echo "?")
echo "navigation log: $since commits since its last review$( [ "$since" != "?" ] && [ "$since" -ge 10 ] && echo ': review due (docs/NAVIGATION-LOG.md)')"

echo "precommit: passed; fast loop ${fast_loop}s, slow ${slow}s, mutants ${killed}/${total} killed, the rest explained, ${full_check} min"
