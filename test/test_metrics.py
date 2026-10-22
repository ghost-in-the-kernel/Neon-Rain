"""docs/AGENT.md's table matches what scripts/checks/metrics.py measures, and no armed metric regressed."""
from pathlib import Path

from scripts.checks import agent_table, metrics

TABLE = "| Metric | Target | Measured | Why |\n| --- | --- | --- | --- |\n| Fast loop (s) | < 30 | 12 | run often |\n"


def real(root: Path) -> tuple[dict[str, dict[str, str]], dict[str, float | None]]:
    """AGENT.md's rows and the measurements now (the timings left unmeasured: they belong to precommit.sh)."""
    values = metrics.measure(root, None, None)
    if root.name == "mutants":  # mutmut's copy rewrites the source, so its line counts are mutmut's, not ours
        values["Largest source file (lines)"] = None
    return agent_table.table((root / "docs" / "AGENT.md").read_text()), values


def test_every_metric_measured_is_in_the_table_and_back(root: Path) -> None:
    rows, values = real(root)
    assert sorted(rows) == sorted(values)


def test_the_table_is_not_stale(root: Path) -> None:
    rows, values = real(root)
    stale = {name: (rows[name]["measured"], agent_table.shown(value)) for name, value in values.items()
             if value is not None and agent_table.number(rows[name]["measured"]) != value}
    assert stale == {}, "run .venv/bin/python scripts/metrics.py --write and review the diff"


def test_no_armed_metric_regressed(root: Path) -> None:
    rows, values = real(root)
    states = {name: agent_table.verdict(rows[name]["target"], rows[name]["measured"], v) for name, v in values.items()}
    assert [name for name, state in states.items() if state == "regressed"] == []


def test_numbers_are_read_from_cells() -> None:
    assert [agent_table.number(c) for c in ("0 (no results)", "— (0.5)", "1,200", "0.37", "")] == [0, None, 1200, 0.37, None]


def test_targets_are_judged() -> None:
    assert agent_table.within("< 30", 29.9) and not agent_table.within("< 30", 30)
    assert agent_table.within("≤ 5", 5) and not agent_table.within("≤ 5", 6)
    assert agent_table.within("0", 0) and not agent_table.within("0", 1)
    assert agent_table.within("< 1,200", 1199) and not agent_table.within("< 1,200", 1200)


def test_a_metric_worse_than_its_armed_target_is_caught() -> None:
    assert agent_table.verdict("< 30", "12", 31) == "regressed"


def test_a_metric_never_within_target_is_not_armed() -> None:
    assert agent_table.verdict("< 0.35", "—", 20.0) == "not armed"
    assert agent_table.verdict("< 0.35", "0.5", 0.6) == "not armed"


def test_a_metric_within_target_moves_freely() -> None:
    assert agent_table.verdict("< 30", "12", 29) == "within"
    assert agent_table.verdict("< 30", "12", None) == "not measured"


def test_the_table_is_rewritten_in_place() -> None:
    assert agent_table.rewritten(TABLE, {"Fast loop (s)": 8.5}) == TABLE.replace("| 12 |", "| 8.50 |")
    assert agent_table.rewritten(TABLE, {"Fast loop (s)": None}) == TABLE


def test_routing_rows_count_their_files() -> None:
    claude = "| Task | Start here | Contract | Tests |\n| A | `a.md`, `b/` | `c.md` | |\n| B | `d.md` | | |\n"
    assert metrics.routing_files(claude) == 2


def test_a_dataset_without_a_manifest_line_is_counted(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "MANIFEST.md").write_text("| Dataset | Hash |\n| --- | --- |\n| prices | ab |\n")
    (tmp_path / "data" / "prices.parquet").write_text("")
    assert metrics.unlisted_datasets(tmp_path) == 0
    (tmp_path / "data" / "news.parquet").write_text("")
    assert metrics.unlisted_datasets(tmp_path) == 1


def test_docs_per_source_waits_for_source(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("a\nb\nc\n")
    assert metrics.docs_per_source(tmp_path) is None
    (tmp_path / "neonrain").mkdir()
    (tmp_path / "neonrain" / "a.py").write_text("x = 1\ny = 2\n")
    assert metrics.docs_per_source(tmp_path) == 1.5
