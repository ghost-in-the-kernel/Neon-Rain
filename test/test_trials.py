"""HAR-01's config hash and HAR-09's trials file, written to temporary files only: the real harness/trials.tsv is
an append-only record and a test line in it would falsify the trial count."""
import hashlib
import re
from datetime import date
from pathlib import Path

import pytest

from neonrain.harness import trials
from neonrain.harness.dispersion import Axis, Dispersion

HEADER_REFUSED = "harness/trials.tsv's header is not HAR-09's"
BREAK_REFUSED = "harness/trials.tsv does not end with a line break"
DAY = date(2026, 11, 1)
BOTH = Dispersion(Axis(0.5, 0.25, 0.25, 0.75, 3), Axis(0.5, None, 0.5, 0.5, 1), 2, True)
CONFIG = {
    "feature_columns": ["b", "a"], "target": {"min_tickers": 20}, "split": {"seed": 1},
    "cost": {"bps": 10}, "model_name": "zero", "hyperparameters": {}, "data_manifest": {"prices": "ff"},
}


def append(path: Path, run: str = "ab12", horizon: int | None = 5, metric: str = "IC", mean: float | None = 0.02,
           dispersion: Dispersion | None = BOTH, note: str = "") -> int:
    """One line with defaults for what a test does not care about."""
    return trials.append_trial(path, run=run, day=DAY, horizon=horizon, metric=metric, mean=mean,
                               dispersion=dispersion, note=note)


def refused(message: str) -> "pytest.RaisesExc[ValueError]":
    """pytest.raises for a ValueError whose whole text is `message`."""
    return pytest.raises(ValueError, match="^" + re.escape(message) + "$")


def lines(path: Path) -> list[str]:
    return path.read_text().split("\n")


def test_the_header_is_har_09s(root: Path) -> None:
    assert trials.TRIALS_COLUMNS == ["config_hash", "date", "horizon", "metric", "mean", "dispersion", "trials_so_far", "note"]
    assert (root / "harness" / "trials.tsv").read_text().partition("\n")[0] == trials.HEADER == "\t".join(trials.TRIALS_COLUMNS)


def test_the_config_hash_is_the_first_16_hex_digits_of_the_canonical_json() -> None:
    text = ('{"cost":{"bps":10},"data_manifest":{"prices":"ff"},"feature_columns":["a","b"],'
            '"harness_version":"1","model":{"hyperparameters":{},"name":"zero"},"split":{"seed":1},'
            '"target":{"min_tickers":20}}')
    assert trials.config_hash(**CONFIG) == hashlib.sha256(text.encode()).hexdigest()[:16]  # type: ignore[arg-type]
    assert trials.HARNESS_VERSION == "1"


def test_the_config_hash_ignores_the_order_of_columns_and_keys() -> None:
    other = CONFIG | {"feature_columns": ["a", "b"], "split": {"seed": 1}, "target": {"min_tickers": 20}}
    assert trials.config_hash(**other) == trials.config_hash(**CONFIG)  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["feature_columns", "target", "split", "cost", "model_name", "hyperparameters",
                                  "data_manifest"])
def test_the_config_hash_changes_with_each_part(name: str) -> None:
    changed = {"feature_columns": ["a"], "target": {"min_tickers": 21}, "split": {"seed": 2}, "cost": {"bps": 11},
               "model_name": "one", "hyperparameters": {"depth": 2}, "data_manifest": {"prices": "00"}}
    assert trials.config_hash(**(CONFIG | {name: changed[name]})) != trials.config_hash(**CONFIG)  # type: ignore[arg-type]


def test_the_config_hash_tells_one_from_one_point_zero_and_escapes_non_ascii() -> None:
    whole = trials.config_hash(**(CONFIG | {"cost": {"bps": 1}}))  # type: ignore[arg-type]
    assert whole != trials.config_hash(**(CONFIG | {"cost": {"bps": 1.0}}))  # type: ignore[arg-type]
    accented = CONFIG | {"feature_columns": ["é"]}
    text = ('{"cost":{"bps":10},"data_manifest":{"prices":"ff"},"feature_columns":["\\u00e9"],'
            '"harness_version":"1","model":{"hyperparameters":{},"name":"zero"},"split":{"seed":1},'
            '"target":{"min_tickers":20}}')
    assert trials.config_hash(**accented) == hashlib.sha256(text.encode()).hexdigest()[:16]  # type: ignore[arg-type]


def test_the_config_hash_refuses_a_column_named_twice_and_a_nan() -> None:
    with refused("a feature column is named twice (HAR-01)"):
        trials.config_hash(**(CONFIG | {"feature_columns": ["a", "a"]}))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        trials.config_hash(**(CONFIG | {"cost": {"bps": float("nan")}}))  # type: ignore[arg-type]


def test_a_missing_file_is_created_with_its_header_and_one_line(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    assert append(path) == 0
    assert lines(path) == [
        trials.HEADER,
        "ab12\t2026-11-01\t5\tIC\t0.02\tfolds: 0.5 ± 0.25 [0.25, 0.75] n=3; groups: 0.5 ± undefined [0.5, 0.5] n=1;"
        " undefined_cells=2; fits names\t0\t",
        "",
    ]


def test_trials_so_far_counts_the_lines_before_that_share_the_metric(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    counts = [append(path, run="a1", metric="IC"), append(path, run="b2", metric="Sharpe"),
              append(path, run="c3", metric="IC", horizon=21), append(path, run="a1", metric="IC", horizon=21),
              append(path, run="d4", metric="IC", mean=None, note="crashed")]
    assert counts == [0, 0, 1, 2, 3]
    assert [row.split("\t")[6] for row in lines(path)[1:-1]] == ["0", "0", "1", "2", "3"]


def test_a_failed_run_has_empty_numbers_and_says_why(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    append(path, horizon=None, mean=None, dispersion=None, note="crashed in fold 2")
    assert lines(path)[1] == "ab12\t2026-11-01\t\tIC\t\t\t0\tcrashed in fold 2"
    with refused("a line with no mean says why in its note (HAR-09)"):
        append(path, mean=None)
    assert len(lines(path)) == 3


def test_an_undefined_axis_is_written_undefined(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    append(path, dispersion=Dispersion(None, None, 0, False))
    assert lines(path)[1].split("\t")[5] == "folds: undefined; groups: undefined; undefined_cells=0"


def test_a_tab_or_line_break_in_a_note_becomes_a_space(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    append(path, note="a\tb\r\nc")
    assert lines(path)[1].split("\t")[7] == "a b  c"
    assert len(lines(path)) == 3


@pytest.mark.parametrize("field", ["run", "metric"])
def test_a_tab_or_line_break_in_another_field_is_refused(tmp_path: Path, field: str) -> None:
    path = tmp_path / "trials.tsv"
    for bad in ("x\ty", "x\ny", "x\ry"):
        with refused(f"{field} holds a tab or a line break (HAR-09)"):
            append(path, run=bad) if field == "run" else append(path, metric=bad)
    assert not path.exists()


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_a_mean_that_is_not_finite_is_refused(tmp_path: Path, bad: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        append(tmp_path / "trials.tsv", mean=bad)


def test_a_horizon_below_one_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="horizon"):
        append(tmp_path / "trials.tsv", horizon=0)
    append(tmp_path / "trials.tsv", horizon=1)


def test_a_file_with_another_header_or_no_final_line_break_is_refused_and_left_alone(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    for text, message in (("hash\tmean\n", HEADER_REFUSED), (trials.HEADER, BREAK_REFUSED), ("", HEADER_REFUSED)):
        path.write_text(text)
        with refused(message):
            append(path)
        assert path.read_text() == text


def test_a_repeat_with_other_numbers_is_appended_and_raised(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    append(path)
    append(path, mean=0.02)
    with pytest.raises(trials.TrialConflict) as caught:
        append(path, mean=0.03, note="rerun")
    assert str(caught.value) == "ab12 5 IC: numbers differ from an earlier line with this config hash"
    assert lines(path)[3].split("\t")[6:] == ["2", "CONFLICT: numbers differ from an earlier line with this hash; rerun"]
    with pytest.raises(trials.TrialConflict):
        append(path, dispersion=None)


def test_a_repeat_with_other_numbers_but_another_horizon_metric_or_hash_is_no_conflict(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    append(path)
    append(path, mean=0.03, horizon=21)
    append(path, mean=0.03, metric="Sharpe")
    append(path, mean=0.03, run="cd34")
    append(path, mean=None, dispersion=None, note="crashed")
    assert len(lines(path)) == 7


def test_a_dsr_line_under_the_same_hash_is_appended_unmarked_while_another_metric_still_conflicts(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    append(path, metric=trials.DEFLATED)
    assert trials.DEFLATED == "DSR"
    assert append(path, metric=trials.DEFLATED, mean=0.03) == 1  # N and V come from the file: no conflict
    append(path, metric="Sharpe")
    with pytest.raises(trials.TrialConflict):
        append(path, metric="Sharpe", mean=0.03)
    assert ["CONFLICT" in row for row in lines(path)[1:5]] == [False, False, False, True]
    assert lines(path)[2].split("\t")[4] == "0.03"


def test_a_failed_earlier_line_is_no_conflict(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    append(path, mean=None, dispersion=None, note="crashed")
    append(path)
    assert len(lines(path)) == 4


def test_a_repeat_conflicts_with_an_earlier_line_that_has_a_mean_and_no_dispersion(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    append(path, dispersion=None)
    with pytest.raises(trials.TrialConflict):
        append(path, mean=0.03, dispersion=None)


def test_a_line_without_a_note_has_an_empty_one(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    trials.append_trial(path, run="ab12", day=DAY, horizon=5, metric="IC", mean=0.02, dispersion=None)
    assert path.read_bytes().endswith(b"\t0\t\n")


def test_the_file_is_utf_8_with_plain_line_breaks(tmp_path: Path) -> None:
    path = tmp_path / "trials.tsv"
    append(path, note="é")
    append(path, note="x")
    raw = path.read_bytes()
    assert raw.count(b"\r") == 0 and raw.count(b"\n") == 3
    assert "±".encode() in raw and "é".encode() in raw
