"""TODO 3.3: the baselines' goldens and RESULTS.md's baseline table, both read off the lines of harness/trials.tsv.

A baseline's golden (`harness/goldens/baseline_<name>.json`) holds one run per period: the lines of the run that
trials.tsv gives for a config hash and a date (HAR-09), parsed and nothing else: each line's number, its mean, both
axes' dispersion (HAR-08), the three cost levels as three Sharpe metrics (HAR-06) and the dropped counts of its
horizon (HAR-02). No number is computed or rounded here: a float is the text of the line read back, so its repr is
the text again. The golden is held by its hash, never recomputed from the market (AGT-01, HAR-14); `golden_problems`
only shows that it is what the trials lines say, and `table_problems` that RESULTS.md's table is what the goldens say.
"""
import json
import re

from neonrain.harness.trials import TRIALS_COLUMNS
from neonrain.universe.periods import FROM_BOUNDARY, SURVIVOR_ONLY
from scripts.checks.tables import TABLE

SOURCE = "harness/trials.tsv"
# Each baseline's run per period: (config hash, date). The date pins the latest run of the hash (a repeat, J-073 and
# J-074, is a later date), so lines appended after it change nothing here.
BASELINES: dict[str, dict[str, tuple[str, str]]] = {
    "zero": {SURVIVOR_ONLY: ("6acabef659847218", "2026-10-28"), FROM_BOUNDARY: ("9afd94d3fdb8ad15", "2026-10-28")},
    "momentum": {SURVIVOR_ONLY: ("31a422f89dec8cc2", "2026-10-29"), FROM_BOUNDARY: ("af693527c767abd1", "2026-10-29")},
    "reversal": {SURVIVOR_ONLY: ("32ed3e4db9e20df5", "2026-10-29"), FROM_BOUNDARY: ("e90d08648b073002", "2026-10-29")},
    "tree": {SURVIVOR_ONLY: ("45f153bc220ad445", "2026-10-29"), FROM_BOUNDARY: ("a5605f1cbb823b80", "2026-10-29")},
}
PERIODS = (SURVIVOR_ONLY, FROM_BOUNDARY)
METRICS = ("accuracy", "balanced_accuracy", "IC", "Sharpe_0bps", "Sharpe_10bps", "Sharpe_25bps", "DSR")
COUNTS = ("period", "cells", "test_rows", "dropped_missing", "dropped_ties", "dropped_thin_dates", "delisting_ends")
COSTS = {"Sharpe_0bps": "0 bps", "Sharpe_10bps": "10 bps", "Sharpe_25bps": "25 bps", "DSR": "10 bps"}
FINDINGS = {SURVIVOR_ONLY: ["NR-F-03"], FROM_BOUNDARY: ["NR-F-04"]}
MODEL_FINDINGS = {"zero": ["NR-F-10"], "momentum": ["NR-F-09"], "reversal": ["NR-F-09"], "tree": []}
DSR_BAR = 0.95
HEADER = ("| Run | Model | Horizon | Period | Metric | Folds: mean ± sd [min, max] | Groups: mean ± sd [min, max] "
          "| DSR | Costs | Findings |")
RULE = "|" + " --- |" * (HEADER.count("|") - 1)
NUMBER = r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?"
AXIS = re.compile(rf"({NUMBER}) ± ({NUMBER}|undefined) \[({NUMBER}), ({NUMBER})\] n=(\d+)")


def parse_axis(text: str) -> dict[str, float | int | None] | None:
    """One axis of a dispersion column, `folds: 0.5 ± 0.1 [0.4, 0.6] n=3`, as plain data; None where it is undefined."""
    found = AXIS.search(text)
    if found is None:
        return None
    mean, sd, low, high, count = found.groups()
    return {"mean": float(mean), "sd": None if sd == "undefined" else float(sd), "low": float(low),
            "high": float(high), "n": int(count)}


def parse_dispersion(text: str) -> dict[str, object]:
    """The dispersion column: both axes, the undefined cells and R-014's `fits names` flag."""
    parts = text.split("; ")
    if not (parts[0].startswith("folds: ") and parts[1].startswith("groups: ") and parts[2].startswith("undefined_cells=")):
        raise ValueError(f"not HAR-09's dispersion column: {text!r}")
    return {"folds": parse_axis(parts[0]), "groups": parse_axis(parts[1]),
            "undefined_cells": int(parts[2].removeprefix("undefined_cells=")), "fits_names": "fits names" in parts[3:]}


def typed(value: str) -> int | float | str:
    """A note's value as the number it spells, or the text: `686` gives 686, `0.5` gives 0.5, `survivor-only` itself."""
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            continue
    return value


def parse_note(text: str) -> dict[str, int | float | str]:
    """The note column: `key=value` items by their keys (`IC dates` as `IC_dates`; `686 (whole sample)` as 686), and
    the reason of a line with no number as `no_number`."""
    found: dict[str, int | float | str] = {}
    for item in text.split("; "):
        key, equals, value = item.partition("=")
        if equals:
            found[key.replace(" ", "_")] = typed(value.split(" ")[0])
        else:
            found["no_number"] = item.removeprefix("no number: ")
    return found


def parse_line(number: int, line: str) -> dict[str, object]:
    """One trials line (HAR-09) as plain data, with its line number in the file (the header is line 1)."""
    values = line.split("\t")
    if len(values) != len(TRIALS_COLUMNS):
        raise ValueError(f"{SOURCE} line {number} has {len(values)} columns, not {len(TRIALS_COLUMNS)}")
    fields = dict(zip(TRIALS_COLUMNS, values))
    return {"line": number, "config_hash": fields["config_hash"], "date": fields["date"],
            "horizon": int(fields["horizon"]), "metric": fields["metric"],
            "mean": float(fields["mean"]) if fields["mean"] else None, "trials_so_far": int(fields["trials_so_far"]),
            **parse_dispersion(fields["dispersion"]), "note": parse_note(fields["note"])}


def run_lines(trials: str, config_hash: str, date: str) -> list[dict[str, object]]:
    """The parsed lines of one run: those of a config hash on a date; an empty run is refused."""
    parsed = [parse_line(number, line) for number, line in enumerate(trials.splitlines(), start=1)
              if number > 1 and line.startswith(f"{config_hash}\t{date}\t")]
    if not parsed:
        raise ValueError(f"{SOURCE} has no line of {config_hash} on {date}")
    return parsed


def metric_entry(line: dict[str, object]) -> dict[str, object]:
    """One line as a metric of a horizon: everything but its horizon, and the note's counts moved out."""
    note: dict[str, object] = line["note"]  # type: ignore[assignment]
    return {"line": line["line"], "mean": line["mean"], "folds": line["folds"], "groups": line["groups"],
            "undefined_cells": line["undefined_cells"], "fits_names": line["fits_names"],
            "trials_so_far": line["trials_so_far"], "extra": {k: v for k, v in note.items() if k not in COUNTS}}


def horizon_entry(horizon: int, lines: list[dict[str, object]]) -> dict[str, object]:
    """One horizon's dropped counts (HAR-02), which every one of its lines states alike, and its metrics by name."""
    counts = [{key: line["note"][key] for key in COUNTS} for line in lines]  # type: ignore[index]
    if any(found != counts[0] for found in counts):
        raise ValueError(f"the lines of horizon {horizon} disagree on the counts")
    metrics = {str(line["metric"]): metric_entry(line) for line in lines}
    if len(metrics) != len(lines):
        raise ValueError(f"horizon {horizon} has a metric twice")
    return {"counts": counts[0], "metrics": metrics}


def run_entry(trials: str, period: str, config_hash: str, date: str) -> dict[str, object]:
    """One run of one period: its hash, its date and its horizons; the period each line states must be `period`."""
    lines = run_lines(trials, config_hash, date)
    horizons = {str(h): horizon_entry(h, [line for line in lines if line["horizon"] == h])
                for h in sorted({int(line["horizon"]) for line in lines})}  # type: ignore[call-overload]
    if any(entry["counts"]["period"] != period for entry in horizons.values()):  # type: ignore[index]
        raise ValueError(f"{config_hash} on {date} is not a run of the {period} period")
    return {"config_hash": config_hash, "date": date, "horizons": horizons}


def dumped(value: object) -> str:
    """A golden's text: sorted keys, one-space indent, a final line break; floats exactly as read, NaN refused."""
    return json.dumps(value, indent=1, sort_keys=True, allow_nan=False) + "\n"


def golden(trials: str, name: str, runs: dict[str, tuple[str, str]]) -> str:
    """`baseline_<name>.json`'s text for trials.tsv's text and the baseline's run (hash, date) of each period."""
    return dumped({"baseline": name, "source": SOURCE,
                   "runs": {period: run_entry(trials, period, *found) for period, found in runs.items()}})


def golden_name(name: str) -> str:
    """The file a baseline's golden is."""
    return f"baseline_{name}.json"


def golden_problems(trials: str, texts: dict[str, str]) -> list[str]:
    """Each golden (file name and text) that is not what the lines of harness/trials.tsv give; [] when all are."""
    return [f"{golden_name(name)} is not what the lines of {SOURCE} give" for name, runs in BASELINES.items()
            if texts.get(golden_name(name)) != golden(trials, name, runs)]


def axis_cell(axis: dict[str, float | int | None] | None) -> str:
    """An axis as a table cell, in the trials column's own digits: `0.5 ± 0.1 [0.4, 0.6] n=3`."""
    if axis is None:
        return "undefined"
    spread = "undefined" if axis["sd"] is None else axis["sd"]
    return f"{axis['mean']} ± {spread} [{axis['low']}, {axis['high']}] n={axis['n']}"


def findings(name: str, period: str) -> str:
    """The findings a row carries: its period's (NR-F-03, NR-F-04) and its baseline's."""
    return ", ".join(FINDINGS[period] + MODEL_FINDINGS[name])


def dsr_cell(metric: str, entry: dict[str, object]) -> str:
    """The deflated Sharpe's N and V and which side of HAR-07's 0.95 its mean falls; empty for the other metrics."""
    if metric != "DSR":
        return ""
    extra: dict[str, object] = entry["extra"]  # type: ignore[assignment]
    side = "below" if entry["mean"] < DSR_BAR else "at or above"  # type: ignore[operator]
    return f"N={extra['N']}, V={extra['V']}; {side} {DSR_BAR}"


def row(name: str, period: str, horizon: str, metric: str, run: dict[str, object]) -> str:
    """One table row: a baseline's metric at a horizon in a period, from the golden's run."""
    entry: dict[str, object] = run["horizons"][horizon]["metrics"][metric]  # type: ignore[index]
    groups = axis_cell(entry["groups"]) + (" *fits names*" if entry["fits_names"] else "")  # type: ignore[arg-type]
    cells = [run["config_hash"], name, horizon, period, metric, axis_cell(entry["folds"]), groups,  # type: ignore[arg-type]
             dsr_cell(metric, entry), COSTS.get(metric, "-"), findings(name, period)]
    return "| " + " | ".join(str(cell) for cell in cells) + " |"


def numbered(run: dict[str, object], horizon: str) -> list[str]:
    """The metrics of one horizon of a golden's run that have a number, in the order of METRICS."""
    metrics: dict[str, dict[str, object]] = run["horizons"][horizon]["metrics"]  # type: ignore[index]
    return sorted((name for name, entry in metrics.items() if entry["mean"] is not None), key=METRICS.index)


def rows(name: str, text: str) -> list[str]:
    """The table rows of one golden: by horizon, then period, then metric; a metric with no number has no row."""
    runs: dict[str, dict[str, object]] = json.loads(text)["runs"]
    horizons = sorted(runs[SURVIVOR_ONLY]["horizons"], key=int)  # type: ignore[arg-type]
    return [row(name, period, horizon, metric, runs[period])
            for horizon in horizons for period in PERIODS for metric in numbered(runs[period], horizon)]


def table(texts: dict[str, str]) -> str:
    """RESULTS.md's baseline table, from the goldens' texts by file name: header, rule, a row per number."""
    body = [line for name in BASELINES for line in rows(name, texts[golden_name(name)])]
    return "\n".join([HEADER, RULE, *body]) + "\n"


def table_problems(results: str, texts: dict[str, str]) -> list[str]:
    """Whether RESULTS.md holds the baseline table exactly as the goldens give it."""
    held = [found for found in TABLE.findall(results) if found.startswith(HEADER + "\n")]
    return [] if held == [table(texts)] else ["docs/RESULTS.md's baseline table is not what the baseline goldens give"]
