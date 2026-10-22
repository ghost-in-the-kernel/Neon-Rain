"""docs/AGENT.md's metrics table: read it, judge a measurement against it, write it back (scripts/metrics.py)."""
import re

ROW = re.compile(r"^\| (?P<metric>[^|]+?) \| (?P<target>[^|]+?) \| (?P<measured>[^|]*?) \| (?P<why>[^|]*?) \|$")


def number(text: str) -> float | None:
    """The first number in a cell, or None: "0 (no results)" gives 0.0, "— (0.5)" gives None, "1,200" gives 1200.0."""
    match = re.match(r"^\s*(\d[\d,]*(?:\.\d+)?)", text)
    return float(match.group(1).replace(",", "")) if match else None


def within(target: str, value: float) -> bool:
    """Whether a value meets a target cell: "< 30", "≤ 5" or a bare "0" (meaning at most 0)."""
    limit = number(target.lstrip("<≤ ")) or 0.0
    return value < limit if target.strip().startswith("<") else value <= limit


def table(agent: str) -> dict[str, dict[str, str]]:
    """The table's rows by metric name: {"Fast loop (s)": {"target": "< 30", "measured": "—", ...}}."""
    rows = [ROW.match(line) for line in agent.splitlines()]
    return {m["metric"]: m.groupdict() for m in rows if m and m["metric"] not in ("Metric", "---")}


# Decision: R-012 (a metric is armed once recorded within its target, and an armed metric may not pass it)
def verdict(target: str, recorded: str, value: float | None) -> str:
    """One metric's state: "not measured", "within", "not armed" (past target, never recorded within), "regressed"."""
    if value is None:
        return "not measured"
    if within(target, value):
        return "within"
    armed = number(recorded) is not None and within(target, number(recorded) or 0.0)
    return "regressed" if armed else "not armed"


def shown(value: float | None) -> str:
    """A measurement as the table shows it: None as "—", 785.0 as "785", 0.375 as "0.38"."""
    if value is None:
        return "—"
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}"


def rewritten(agent: str, values: dict[str, float | None]) -> str:
    """AGENT.md with each measured metric's Measured cell replaced; a metric not measured keeps its cell."""
    lines = []
    for line in agent.splitlines():
        match = ROW.match(line)
        if match and values.get(match["metric"]) is not None:
            line = f"| {match['metric']} | {match['target']} | {shown(values[match['metric']])} | {match['why']} |"
        lines.append(line)
    return "\n".join(lines) + "\n"
