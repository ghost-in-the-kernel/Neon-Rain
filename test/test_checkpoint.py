"""A run's horizons saved one by one and taken up again (TODO 3.2 b, `neonrain.baselines.checkpoint`) on the synthetic
market, never real data: a horizon reads back exactly, a run cut after one horizon and resumed writes the lines an
uninterrupted run writes, another run's file is never picked up, and a cut mid-write leaves no half file."""
import io
from datetime import date
from functools import partial
from pathlib import Path

import numpy as np
import pytest

from neonrain import targets
from neonrain.baselines import checkpoint, record, runner
from neonrain.harness import synthetic

GEOMETRY = {"embargo": 63, "step": 40, "min_train": 40, "window": None}
CONFIG = synthetic.MarketConfig(tickers=15, days=250, rho=0.1, delist_below=0.5, seed=3)
HORIZONS = (3, 5)
DAY = date(2026, 10, 29)


class CountingFit:
    """A model that scores a squashed `edge` (so the cells hold real numbers) and counts how many models were fitted."""

    def __init__(self) -> None:
        self.fitted = 0

    def __call__(self, features: object, direction: np.ndarray) -> runner.Scorer:
        self.fitted += 1
        return lambda rows: 1 / (1 + np.exp(-rows["edge"].to_numpy()))


def run_of(hyperparameters: dict[str, object] | None = None, manifest: str = "seed-3") -> runner.Run:
    return runner.Run("tree", ["edge"], {"synthetic": manifest}, GEOMETRY, min_tickers=5, horizons=HORIZONS,  # type: ignore[arg-type]
                      groups=2, hyperparameters=hyperparameters or {"rounds": 1})


@pytest.fixture(scope="module")
def market() -> synthetic.Market:
    """Built in a fixture, not at import (J-074)."""
    return synthetic.generate(CONFIG)


def labels_for(market: synthetic.Market, run: runner.Run) -> partial:  # type: ignore[type-arg]
    return partial(targets.labels, market.prices, market.universe, market.calendar, min_tickers=run.min_tickers)


@pytest.fixture(scope="module")
def whole(market: synthetic.Market) -> tuple[dict[int, runner.Horizon], int]:
    """The uninterrupted run, and how many models it fitted."""
    fit = CountingFit()
    return runner.evaluate(market, labels_for(market, run_of()), run_of(), fit), fit.fitted


def same(a: runner.Horizon, b: runner.Horizon) -> None:
    """Every number of two horizons equal, floats bit for bit (repr and raw bytes, which == and allclose would blur)."""
    assert a.horizon == b.horizon and a.found.frame.equals(b.found.frame) and a.found.frame.schema == b.found.frame.schema
    assert tuple(a.found[1:]) == tuple(b.found[1:])
    assert list(a.cells) == list(b.cells)
    for period in a.cells:
        assert len(a.cells[period]) == len(b.cells[period])
        for one, two in zip(a.cells[period], b.cells[period]):
            assert repr(one._replace(nets={})) == repr(two._replace(nets={}))
            assert list(one.nets) == list(two.nets)
            assert all(one.nets[k].tobytes() == two.nets[k].tobytes() and one.nets[k].dtype == two.nets[k].dtype
                       for k in one.nets)


def test_a_horizon_reads_back_exactly(whole: tuple, tmp_path: Path) -> None:
    for part in whole[0].values():
        assert sum(len(c.nets) for cells in part.cells.values() for c in cells) > 0
        saved = checkpoint.save(tmp_path, run_of(), part)
        assert saved.parent == tmp_path and saved.name.startswith("tree-") and saved.name.endswith("-h%d.checkpoint.zip" % part.horizon)
        same(part, checkpoint.load(tmp_path, run_of(), part.horizon))  # type: ignore[arg-type]
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(checkpoint.path_of(tmp_path, run_of(), h).name for h in HORIZONS)


def test_a_float_that_is_nan_or_none_or_inf_reads_back(whole: tuple, tmp_path: Path) -> None:
    part = whole[0][3]
    cell = next(iter(part.cells.values()))[0]
    odd = cell._replace(accuracy=float("nan"), balanced_accuracy=None, ic=cell.ic._replace(mean=float("inf"), t=None),
                        nets={k: np.array([0.1 + 0.2, float("nan"), -0.0]) for k in cell.nets})
    changed = part._replace(cells={**part.cells, next(iter(part.cells)): [odd]})
    checkpoint.save(tmp_path, run_of(), changed)
    same(changed, checkpoint.load(tmp_path, run_of(), 3))  # type: ignore[arg-type]


def test_a_run_cut_after_one_horizon_and_resumed_writes_the_lines_of_an_uninterrupted_one(
        market: synthetic.Market, whole: tuple, tmp_path: Path) -> None:
    run, fit, told = run_of(), CountingFit(), []
    saved = tmp_path / "saved"
    saved.mkdir()
    cut = checkpoint.resume(saved, market, labels_for(market, run), run, fit, None, [3], told.append)
    assert list(cut) == [3] and len(cut) < len(run.horizons)  # the caller writes no line for a part
    assert 0 < fit.fitted < whole[1] and len(list(saved.iterdir())) == 1
    resumed = checkpoint.resume(saved, market, labels_for(market, run), run, fit, None, None, told.append)
    assert list(resumed) == list(run.horizons) and fit.fitted == whole[1]  # horizon 3 was loaded, not fitted again
    assert [t.split(":")[1].split()[0] for t in told] == ["computed,", "loaded", "computed,"]
    record.record(tmp_path / "a.tsv", DAY, run, whole[0])
    record.record(tmp_path / "b.tsv", DAY, run, resumed)
    assert (tmp_path / "a.tsv").read_bytes() == (tmp_path / "b.tsv").read_bytes()
    again = checkpoint.resume(saved, market, labels_for(market, run), run, fit, None, [], told.append)  # all saved
    assert list(again) == list(run.horizons) and fit.fitted == whole[1]


def test_no_horizon_asked_for_and_none_saved_gives_nothing(market: synthetic.Market, tmp_path: Path) -> None:
    run, fit = run_of(), CountingFit()
    assert checkpoint.resume(tmp_path, market, labels_for(market, run), run, fit, None, [], print) == {}
    assert fit.fitted == 0 and not list(tmp_path.iterdir())


def test_another_runs_checkpoint_is_never_picked_up(whole: tuple, tmp_path: Path) -> None:
    checkpoint.save(tmp_path, run_of(), whole[0][3])
    others = [run_of({"rounds": 2}), run_of(manifest="seed-4"), run_of()._replace(name="other"),
              run_of()._replace(feature_columns=["edge", "x"]), run_of()._replace(group_seed=1)]
    names = {checkpoint.path_of(tmp_path, other, 3).name for other in [*others, run_of()]}
    assert len(names) == 1 + len(others)  # each identity has a name of its own
    assert all(checkpoint.load(tmp_path, other, 3) is None for other in others)
    assert checkpoint.load(tmp_path, run_of(), 5) is None and checkpoint.load(tmp_path, run_of(), 3) is not None


def test_a_file_renamed_to_another_identity_or_horizon_is_refused(whole: tuple, tmp_path: Path) -> None:
    saved = checkpoint.save(tmp_path, run_of(), whole[0][3])
    other = run_of({"rounds": 2})
    saved.rename(checkpoint.path_of(tmp_path, other, 3))
    with pytest.raises(ValueError, match="not this run's"):
        checkpoint.load(tmp_path, other, 3)
    checkpoint.path_of(tmp_path, other, 3).rename(checkpoint.path_of(tmp_path, run_of(), 5))
    with pytest.raises(ValueError, match="not this run's"):
        checkpoint.load(tmp_path, run_of(), 5)


def test_a_cut_mid_write_leaves_no_half_checkpoint(whole: tuple, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def cut(run: runner.Run, part: runner.Horizon, target: object) -> None:
        target.write(b"PK half a zip")  # type: ignore[attr-defined]
        raise KeyboardInterrupt("cut")
    monkeypatch.setattr(checkpoint, "encode", cut)
    with pytest.raises(KeyboardInterrupt):
        checkpoint.save(tmp_path, run_of(), whole[0][3])
    assert not list(tmp_path.iterdir())  # no final file, and the temporary one is gone
    assert checkpoint.load(tmp_path, run_of(), 3) is None


def test_a_temporary_file_a_kill_left_behind_is_never_read(whole: tuple, tmp_path: Path) -> None:
    final = checkpoint.path_of(tmp_path, run_of(), 3)
    final.with_name(f".{final.name}.123.tmp").write_bytes(b"PK half a zip")
    assert checkpoint.load(tmp_path, run_of(), 3) is None
    checkpoint.save(tmp_path, run_of(), whole[0][3])
    same(whole[0][3], checkpoint.load(tmp_path, run_of(), 3))  # type: ignore[arg-type]


def test_the_file_is_renamed_over_its_name_in_one_step(whole: tuple, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen = []
    real = checkpoint.os.replace

    def spy(source: Path, target: Path) -> None:
        seen.append((Path(source).exists(), not Path(target).exists(), Path(source).parent == Path(target).parent))
        real(source, target)
    monkeypatch.setattr(checkpoint.os, "replace", spy)
    checkpoint.save(tmp_path, run_of(), whole[0][3])
    assert seen == [(True, True, True)]  # the finished temporary file, beside the name, which did not yet exist


def test_the_identity_is_the_name_and_the_first_periods_config_hash(market: synthetic.Market) -> None:
    run = run_of()
    assert checkpoint.identity(run) == f"tree-{record.config_hash(run, runner.PERIOD_NAMES[0])}"
    assert record.config_hash(run, runner.PERIOD_NAMES[0]) != record.config_hash(run, runner.PERIOD_NAMES[1])
    assert checkpoint.path_of(Path("here"), run, 21) == Path("here") / f"{checkpoint.identity(run)}-h21.checkpoint.zip"


def test_a_series_is_kept_as_float64_whatever_it_was_given(tmp_path: Path) -> None:
    loaded = np.load(io.BytesIO(checkpoint.npy(np.array([1, 2, 3], dtype=np.int32))), allow_pickle=False)
    assert loaded.dtype == np.float64 and loaded.tolist() == [1.0, 2.0, 3.0]
    assert np.load(io.BytesIO(checkpoint.npy(np.array([0.5], dtype=np.float32)))).dtype == np.float64


def test_a_failed_save_into_a_missing_directory_raises_its_own_error_only(whole: tuple, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as caught:
        checkpoint.save(tmp_path / "missing", run_of(), whole[0][3])
    assert caught.value.__context__ is None  # the clean-up of a temporary file that never was raised nothing of its own


def test_a_series_that_would_need_a_pickle_is_refused_on_load(whole: tuple, tmp_path: Path) -> None:
    import io
    import zipfile
    saved = checkpoint.save(tmp_path, run_of(), whole[0][3])
    with zipfile.ZipFile(saved) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    name = next(n for n in members if n.endswith(".npy"))
    buffer = io.BytesIO()
    np.save(buffer, np.array([{"a": 1}], dtype=object), allow_pickle=True)
    members[name] = buffer.getvalue()
    with zipfile.ZipFile(saved, "w") as archive:
        for member, data in members.items():
            archive.writestr(member, data)
    with pytest.raises(ValueError, match="pickle"):
        checkpoint.load(tmp_path, run_of(), 3)


def test_resume_says_which_file_it_loaded_and_tells_the_progress_of_what_it_computes(market: synthetic.Market,
                                                                                    tmp_path: Path) -> None:
    run, told, seen = run_of(), [], []
    progress = lambda horizon, fold, folds: seen.append((horizon, fold, folds))  # noqa: E731
    checkpoint.resume(tmp_path, market, labels_for(market, run), run, CountingFit(), progress, [5], told.append)
    assert {h for h, _, _ in seen} == {5} and len(seen) > 0
    checkpoint.resume(tmp_path, market, labels_for(market, run), run, CountingFit(), progress, [3], told.append)
    assert {h for h, _, _ in seen} == {3, 5}
    assert told[0] == f"horizon 5: computed, saved {checkpoint.path_of(tmp_path, run, 5).name}"
    checkpoint.resume(tmp_path, market, labels_for(market, run), run, CountingFit(), progress, None, told.append)
    assert told[-2:] == [f"horizon 3: loaded {checkpoint.path_of(tmp_path, run, 3).name}",
                         f"horizon 5: loaded {checkpoint.path_of(tmp_path, run, 5).name}"]
