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
    recorded = {name: value for name, value in values.items() if name not in metrics.AT_TITHE}
    stale = {name: (rows[name]["measured"], agent_table.shown(value)) for name, value in recorded.items()
             if value is not None and agent_table.number(rows[name]["measured"]) != value}
    assert stale == {}, "run .venv/bin/python scripts/metrics.py --write and review the diff"


def test_a_metric_recorded_at_tithe_is_still_judged_against_its_target() -> None:
    assert metrics.AT_TITHE == ("Largest source file (lines)",)
    assert agent_table.verdict("< 400", "150", 401) == "regressed"


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
    other = "| Name | Files |\n| --- | --- |\n| x | `1`, `2`, `3`, `4` |\n\n"
    claude = other + "| Task | Start here | Contract | Tests |\n| --- | --- | --- | --- |\n| A | `a.md`, `b/` | `c.md` | |\n| B | `d.md` | | |\n"
    assert metrics.routing_files(claude) == 2


def test_no_routing_table_opens_nothing() -> None:
    assert metrics.routing_files("# CLAUDE.md\n") == 0


def plant(tmp_path: Path) -> Path:
    """A root whose every metric is known: two result rows without a trials line, one without dispersion, one decision
    without See also, thirteen lines of .md (root and docs/) over two of neonrain/."""
    files = {
        "CLAUDE.md": "one two three\n",
        "README.md": "a\n",
        "docs/A.md": "b\n",
        "theGhost.md": "### R-001: a\n- **See also:** R-002\n### R-002: b\n- **Status:** x\n",
        "docs/RESULTS.md": "| Run | Folds | Groups | Findings |\n| --- | --- | --- | --- |\n| zz | 1 | 1 | NR-F-01 |\n"
        + "| ab | 1 ± 1 [0, 2] | 1 ± 1 [0, 2] | NR-F-01 |\n| cd | 1 ± 1 [0, 2] | 1 ± 1 [0, 2] | NR-F-01 |\n"
        + "| ef | 1 ± 1 [0, 2] | 1 ± 1 [0, 2] | NR-F-01 |\n",
        "harness/trials.tsv": "config_hash\tdate\nab\tx\nzz\tx\n",
        "data/MANIFEST.md": "| Dataset | Hash |\n| --- | --- |\n",
        "neonrain/a.py": "x = 1\ny = 2\n",
        "test/t.py": "z = 1\n",
    }
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    return tmp_path


def test_every_metric_is_measured_on_a_planted_root(tmp_path: Path) -> None:
    assert metrics.measure(plant(tmp_path), 1.5, None) == {
        "Mandatory context (words)": 3,
        "Fast loop (s)": 1.5,
        "Full check, `precommit.sh` (min)": None,
        "Largest source file (lines)": 2,
        "Files a routing row opens": 0,
        "Decisions without `See also`": 1,
        "Results without a trials line": 2,
        "Results without dispersion": 1,
        "Datasets without a manifest line": 0,
        "Docs lines per source line": 6.5,
    }


def test_two_decisions_without_see_also_count_two() -> None:
    assert metrics.without_see_also("### R-001: a\n- **Why:** w\n### R-002: b\n- **See also:**\n") == 2


def test_nothing_to_measure_is_zero_lines(tmp_path: Path) -> None:
    assert metrics.largest(tmp_path) == 0
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "a.py").write_text("1\n2\n3\n")
    (tmp_path / "scripts" / "b.txt").write_text("1\n2\n3\n4\n")
    assert metrics.largest(tmp_path) == 3


def test_a_dataset_without_a_manifest_line_is_counted(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "MANIFEST.md").write_text("| Dataset | Hash |\n| --- | --- |\n| daily prices | ab |\n")
    (tmp_path / "data" / "daily prices.parquet").write_text("")
    assert metrics.unlisted_datasets(tmp_path) == 0
    (tmp_path / "data" / "news.parquet").write_text("")
    assert metrics.unlisted_datasets(tmp_path) == 1


def test_docs_per_source_waits_for_source(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("a\nb\nc\n")
    assert metrics.docs_per_source(tmp_path) is None
    (tmp_path / "neonrain").mkdir()
    (tmp_path / "neonrain" / "a.py").write_text("x = 1\ny = 2\n")
    assert metrics.docs_per_source(tmp_path) == 1.5
    (tmp_path / "neonrain" / "b.py").write_text("z = 3\n")
    assert metrics.docs_per_source(tmp_path) == 1.0
    (tmp_path / "neonrain" / "c.py").write_text("w = 4\n" * 5)
    assert metrics.docs_per_source(tmp_path) == 0.38


def test_shown_values() -> None:
    assert [agent_table.shown(v) for v in (None, 785.0, 0.375, 3)] == ["—", "785", "0.38", "3"]


def test_a_zero_target_recorded_at_zero_is_armed() -> None:
    assert agent_table.verdict("0", "0", 1) == "regressed"
