"""HAR-01 and HAR-09: a run's config hash, and the append-only line it leaves in harness/trials.tsv."""
import hashlib
import json
import math
from datetime import date
from pathlib import Path

from neonrain.harness.dispersion import Axis, Dispersion

TRIALS_COLUMNS: list[str] = ["config_hash", "date", "horizon", "metric", "mean", "dispersion", "trials_so_far", "note"]
HARNESS_VERSION = "1"  # "0" while phase 1 built the harness; step 1.7 (the freeze) set it to "1" (HAR-01)
HASH_DIGITS = 16
HEADER = "\t".join(TRIALS_COLUMNS)
METRIC = TRIALS_COLUMNS.index("metric")
SEPARATORS = "\t\r\n"


class TrialConflict(Exception):
    """A run whose config hash matches an earlier line, for the same horizon and metric, with different numbers."""


# Decision: HAR-01 (the canonical JSON and the 16 hex digits that identify a run). json.dumps escapes non-ASCII by
# default and str.encode writes UTF-8 by default, so neither is named: a named default is a mutant no test can see.
def config_hash(*, feature_columns: list[str], target: dict, split: dict, cost: dict, model_name: str,
                hyperparameters: dict, data_manifest: dict[str, str]) -> str:
    """HAR-01's config hash of one run: the first 16 hex digits of the SHA-256 of its canonical JSON.

    Two sets of keyword arguments that differ only in the order of the feature columns or of a dict's keys
    hash alike; a repeated feature column is refused.
    """
    if len(set(feature_columns)) != len(feature_columns):
        raise ValueError("a feature column is named twice (HAR-01)")
    config = {"feature_columns": sorted(feature_columns), "target": target, "split": split, "cost": cost,
              "model": {"name": model_name, "hyperparameters": hyperparameters},
              "data_manifest": data_manifest, "harness_version": HARNESS_VERSION}
    text = json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode()).hexdigest()[:HASH_DIGITS]


def number(value: float) -> str:
    """A float as its shortest round-trip text, e.g. 0.1 gives "0.1"; NaN and infinity are refused."""
    if not math.isfinite(value):
        raise ValueError(f"{value} is not a finite number (HAR-09)")
    return repr(float(value))


def axis_text(name: str, found: Axis | None) -> str:
    """One axis of HAR-08 as `folds: 0.5 ± 0.1 [0.4, 0.6] n=3`; undefined where the axis or its sd is."""
    if found is None:
        return f"{name}: undefined"
    spread = "undefined" if found.sd is None else number(found.sd)
    return f"{name}: {number(found.mean)} ± {spread} [{number(found.low)}, {number(found.high)}] n={found.count}"


def dispersion_text(found: Dispersion | None) -> str:
    """The dispersion column: both axes, the undefined cells and R-014's flag; "" when the run has none."""
    if found is None:
        return ""
    text = f"{axis_text('folds', found.folds)}; {axis_text('groups', found.groups)}; undefined_cells={found.undefined_cells}"
    return text + ("; fits names" if found.fits_names else "")


def clean(field: str, name: str) -> str:
    """A field that must hold no tab or line break, since each would split the line."""
    if any(mark in field for mark in SEPARATORS):
        raise ValueError(f"{name} holds a tab or a line break (HAR-09)")
    return field


def fields_of(text: str) -> list[list[str]]:
    """The data lines of a trials file as their tab-separated fields, the header left out."""
    return [line.split("\t") for line in text.splitlines()[1:]]


def check_file(text: str) -> None:
    """Refuse a trials file with another header, or whose last line has no line break (a new line would glue to it)."""
    if text.partition("\n")[0] != HEADER:
        raise ValueError("harness/trials.tsv's header is not HAR-09's")
    if not text.endswith("\n"):
        raise ValueError("harness/trials.tsv does not end with a line break")


def conflicting(earlier: list[list[str]], line: list[str]) -> bool:
    """Whether a line with numbers repeats an earlier line's config hash, horizon and metric with other numbers."""
    key = line[:1] + line[2:4]
    return bool(line[4]) and any(
        row[:1] + row[2:4] == key and row[4] and row[4:6] != line[4:6] for row in earlier)


# Decision: HAR-09 (one append-only line per run, trials_so_far counted from the file itself)
def append_trial(path: Path, *, run: str, day: date, horizon: int | None, metric: str, mean: float | None,
                 dispersion: Dispersion | None, note: str = "") -> int:
    """HAR-09: append one line to the trials file at `path` and return its `trials_so_far`.

    `run` is the config hash and `day` the date, given by the caller since the harness never reads the clock.
    A run with no `mean` (it failed, crashed or was abandoned) must say why in `note`. A missing file is
    created with its header. A line that repeats an earlier line's hash, horizon and metric with other
    numbers is still appended, marked in its note, and then raised as a TrialConflict (HAR-01).
    """
    if mean is None and not note:
        raise ValueError("a line with no mean says why in its note (HAR-09)")
    if horizon is not None and horizon < 1:
        raise ValueError(f"horizon is {horizon}: a positive number of trading days (HAR-09)")
    text = path.read_bytes().decode() if path.exists() else HEADER + "\n"
    check_file(text)
    earlier = fields_of(text)
    so_far = sum(1 for row in earlier if row[METRIC] == metric)
    line = [clean(run, "run"), day.isoformat(), "" if horizon is None else str(horizon), clean(metric, "metric"),
            "" if mean is None else number(mean), dispersion_text(dispersion), str(so_far), note]
    clash = conflicting(earlier, line)
    if clash:
        line[-1] = "; ".join(filter(None, ["CONFLICT: numbers differ from an earlier line with this hash", note]))
    line[-1] = line[-1].translate({ord(mark): " " for mark in SEPARATORS})
    if not path.exists():
        path.write_bytes((HEADER + "\n").encode())
    with path.open("ab") as handle:
        handle.write(("\t".join(line) + "\n").encode())
    if clash:
        raise TrialConflict(f"{run} {horizon} {metric}: numbers differ from an earlier line with this config hash")
    return so_far
