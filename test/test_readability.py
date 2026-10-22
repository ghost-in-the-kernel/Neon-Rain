"""Our Python reads as R-015(b) asks; and each rule, broken on purpose, is caught (TODO 0.5)."""
from pathlib import Path

from scripts.checks import readability


def test_our_code_holds(root: Path) -> None:
    assert readability.problems(root) == []


def test_a_long_function_is_caught() -> None:
    body = "".join(f"    x{n} = {n}\n" for n in range(40))
    found = readability.source_problems(f"def long() -> None:\n{body}", "f.py")
    assert found == ["f.py:1 long is 41 lines, at most 39"]


def test_a_function_of_thirty_nine_lines_holds() -> None:
    body = "".join(f"    x{n} = {n}\n" for n in range(38))
    assert readability.source_problems(f"def fits() -> None:\n{body}", "f.py") == []


def test_star_args_are_caught() -> None:
    assert readability.source_problems("def f(*a: int) -> None:\n    pass\n", "f.py") == [
        "f.py:1 f takes *args or **kwargs"
    ]
    assert readability.source_problems("def g(**k: int) -> None:\n    pass\n", "f.py") == [
        "f.py:1 g takes *args or **kwargs"
    ]


def test_a_comprehension_of_four_clauses_is_caught() -> None:
    source = "x = [a for a in b if a if c for d in e]\n"
    assert readability.source_problems(source, "f.py") == ["f.py:1 a comprehension has 4 clauses, at most 3"]


def test_a_comprehension_of_three_clauses_holds() -> None:
    assert readability.source_problems("x = {a: d for a in b if a for d in e}\n", "f.py") == []


def test_a_function_of_exactly_forty_lines_is_caught() -> None:
    body = "".join(f"    x{n} = {n}\n" for n in range(39))
    assert readability.source_problems(f"def edge() -> None:\n{body}", "f.py") == ["f.py:1 edge is 40 lines, at most 39"]


def test_every_file_under_every_folder_is_read(tmp_path: Path) -> None:
    for name in ("scripts/a.py", "test/sub/b.py", "neonrain/c.PY", "docs/d.py"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("def f(*a: int) -> None:\n    pass\n")
    assert readability.problems(tmp_path) == [
        "scripts/a.py:1 f takes *args or **kwargs", "test/sub/b.py:1 f takes *args or **kwargs"
    ]
