"""A run's horizons saved one by one, so a run of hours can be cut and taken up again (TODO 3.2 b, R-034).

A horizon of the tree takes about 50 minutes and a background task lives at most two hours, so `resume` keeps each
finished `runner.Horizon` in a file of its own and loads it on the next start instead of computing it again. The lines
are written by the caller only when every horizon is present (`record.record`, which reads the DSR's N and V from the
trials file at write time), so a run in pieces writes what an uninterrupted run writes.

**The identity.** A file is named by the run's name, the HAR-01 config hash of its first period (the hash holds the
feature columns, the geometry, the group seed, the horizons, the hyperparameters and both datasets' hashes, so another
baseline, other hyperparameters or other data is another name) and the horizon. The same identity and horizon are
written inside the file and checked on load, so a renamed file is refused. What the hash cannot hold is the code: a
change to the runner or the model's code under unchanged hyperparameters keeps the name; delete the directory then.

**The format** is a zip of three kinds of member and no pickle (a checkpoint read back is data, never code): `meta.json`
(the identity, the horizon, the four label counts and every cell's numbers; Python writes a float's shortest repr,
which reads back to the same bits, NaN and infinity included), `found.parquet` (the labels' frame, dtypes kept) and one
`.npy` for each after-cost series (raw float64, bit for bit). It is written to a temporary file in the same directory
and renamed over its name (`os.replace`, atomic), so a cut mid-write leaves a temporary file and never a half
checkpoint; a temporary file is never read.
"""
import io
import json
import os
import zipfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import IO, Any, NamedTuple

import numpy as np
import polars as pl

from neonrain.baselines import record, runner
from neonrain.harness import metrics

META = "meta.json"
FRAME = "found.parquet"
SUFFIX = ".checkpoint.zip"


class Found(NamedTuple):
    """The labels of a horizon as a checkpoint keeps them: what `runner.Labelled` says (the record reads only these)."""

    frame: pl.DataFrame
    dropped_missing: int
    dropped_ties: int
    dropped_thin_dates: int
    delisting_ends: int


# Decision: HAR-01 (a run is its config hash: a checkpoint of another hash is another run's and is never read)
def identity(run: runner.Run) -> str:
    """The run's name and the config hash of its first period: the part of a file's name every horizon shares."""
    return f"{run.name}-{record.config_hash(run, runner.PERIOD_NAMES[0])}"


def path_of(directory: Path, run: runner.Run, horizon: int) -> Path:
    """Where the horizon's checkpoint of this run lives."""
    return directory / f"{identity(run)}-h{horizon}{SUFFIX}"


def optional_float(value: float | None) -> float | None:
    return None if value is None else float(value)


def cell_meta(cell: runner.Cell, index: str) -> dict[str, Any]:
    """A cell's numbers as JSON, its series named `index`-level in the zip."""
    return {"fold": int(cell.fold), "group": int(cell.group), "test_rows": int(cell.test_rows),
            "accuracy": optional_float(cell.accuracy), "balanced_accuracy": optional_float(cell.balanced_accuracy),
            "ic": [optional_float(cell.ic.mean), optional_float(cell.ic.standard_error), optional_float(cell.ic.t),
                   int(cell.ic.dates), int(cell.ic.dropped_thin), int(cell.ic.dropped_flat)],
            "levels": [float(bps) for bps in cell.nets], "series": [f"{index}-{n}.npy" for n in range(len(cell.nets))]}


def npy(series: np.ndarray) -> bytes:
    """The bytes of a float64 array in .npy form."""
    buffer = io.BytesIO()
    np.save(buffer, np.asarray(series, dtype=np.float64), allow_pickle=False)
    return buffer.getvalue()


def encode(run: runner.Run, part: runner.Horizon, target: IO[bytes]) -> None:
    """Write the horizon as a zip to `target` (a file object)."""
    found = part.found
    meta: dict[str, Any] = {
        "identity": identity(run), "horizon": int(part.horizon),
        "counts": [int(found.dropped_missing), int(found.dropped_ties), int(found.dropped_thin_dates),
                   int(found.delisting_ends)],
        "cells": {period: [cell_meta(cell, f"{p}-{i}") for i, cell in enumerate(part.cells[period])]
                  for p, period in enumerate(runner.PERIOD_NAMES)}}
    frame = io.BytesIO()
    found.frame.write_parquet(frame)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr(META, json.dumps(meta))
        archive.writestr(FRAME, frame.getvalue())
        for period in runner.PERIOD_NAMES:
            for i, cell in enumerate(part.cells[period]):
                for name, series in zip(meta["cells"][period][i]["series"], cell.nets.values()):
                    archive.writestr(name, npy(series))


def save(directory: Path, run: runner.Run, part: runner.Horizon) -> Path:
    """Write the horizon's checkpoint atomically: a temporary file beside it, flushed to disk, then renamed over it."""
    final = path_of(directory, run, part.horizon)
    temporary = final.with_name(f".{final.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as handle:
            encode(run, part, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, final)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return final


def decode_cell(archive: zipfile.ZipFile, cell: dict[str, Any]) -> runner.Cell:
    nets = {level: np.load(io.BytesIO(archive.read(name)), allow_pickle=False)
            for level, name in zip(cell["levels"], cell["series"])}
    return runner.Cell(cell["fold"], cell["group"], cell["test_rows"], cell["accuracy"], cell["balanced_accuracy"],
                       metrics.IC(*cell["ic"]), nets)


def load(directory: Path, run: runner.Run, horizon: int) -> runner.Horizon | None:
    """The horizon's saved result, or None if this run has none. A file whose inside names another identity or
    horizon is refused (ValueError); an unreadable one raises (a cut cannot make one, so it is looked at, not skipped)."""
    path = path_of(directory, run, horizon)
    if not path.exists():
        return None
    with zipfile.ZipFile(path) as archive:
        meta = json.loads(archive.read(META))
        if meta["identity"] != identity(run) or meta["horizon"] != horizon:
            raise ValueError(f"{path} holds {meta['identity']} horizon {meta['horizon']}, not this run's horizon {horizon}")
        frame = pl.read_parquet(io.BytesIO(archive.read(FRAME)))
        cells = {period: [decode_cell(archive, cell) for cell in meta["cells"][period]] for period in runner.PERIOD_NAMES}
    return runner.Horizon(horizon, Found(frame, *meta["counts"]), cells)


def resume(directory: Path, market: runner.Market, labels_for: Callable[[int], runner.Labelled], run: runner.Run,
           fit: runner.Fit | None, progress: runner.Progress | None, wanted: Iterable[int] | None,
           say: Callable[[str], None]) -> dict[int, runner.Horizon]:
    """The horizons of `run` that are present, in the run's order: those with a checkpoint are loaded; each of the others
    in `wanted` (all, if None) is computed as `runner.evaluate` would and saved at once. Horizons neither saved nor
    wanted are absent from the result; the caller writes the lines only when none is."""
    groups = runner.ticker_groups(market, run)
    chosen = set(run.horizons if wanted is None else wanted)
    found: dict[int, runner.Horizon] = {}
    for horizon in run.horizons:
        part = load(directory, run, horizon)
        if part is not None:
            say(f"horizon {horizon}: loaded {path_of(directory, run, horizon).name}")
        elif horizon in chosen:
            part = runner.evaluate_horizon(market, labels_for(horizon), groups, run, horizon, fit, progress)
            say(f"horizon {horizon}: computed, saved {save(directory, run, part).name}")
        if part is not None:
            found[horizon] = part
    return found
