"""Measure docs/AGENT.md's metrics, print the table, exit 1 if an armed metric passed its target.

    .venv/bin/python scripts/metrics.py [--fast-loop SECONDS] [--full-check MINUTES] [--write]

--write records the measurements in AGENT.md's Measured column, and refuses while a metric has regressed.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checks import agent_table, metrics  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "docs" / "AGENT.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="docs/AGENT.md's metrics")
    parser.add_argument("--fast-loop", type=float, default=None)
    parser.add_argument("--full-check", type=float, default=None)
    parser.add_argument("--write", action="store_true")
    options = parser.parse_args()
    values = metrics.measure(ROOT, options.fast_loop, options.full_check)
    rows = agent_table.table(AGENT.read_text())
    regressed = 0
    for name, value in values.items():
        state = agent_table.verdict(rows[name]["target"], rows[name]["measured"], value)
        regressed += state == "regressed"
        print(f"{name:40} {agent_table.shown(value):>8}  {rows[name]['target']:>8}  {state}")
    if options.write and not regressed:
        AGENT.write_text(agent_table.rewritten(AGENT.read_text(), values))
    measured = sum(1 for value in values.values() if value is not None)
    written = ", written" if options.write and not regressed else ""
    print(f"metrics: {measured} of {len(values)} measured, {regressed} regressed{written}")
    return 1 if regressed else 0


if __name__ == "__main__":
    sys.exit(main())
