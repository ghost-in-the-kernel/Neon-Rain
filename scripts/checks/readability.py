"""R-015(b)'s rules a linter cannot say: short functions, small comprehensions, no *args or **kwargs."""
import ast
from pathlib import Path

MAX_FUNCTION_LINES = 40
MAX_COMPREHENSION_CLAUSES = 3
OUR_CODE: tuple[str, ...] = ("neonrain", "scripts", "test")


def clauses(node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp) -> int:
    """The `for` and `if` clauses of a comprehension: [x for x in y if x] has 2."""
    return sum(1 + len(generator.ifs) for generator in node.generators)


def node_problems(node: ast.AST, where: str) -> list[str]:
    """One syntax node against the rules; `where` is "path:line" for the message."""
    found = []
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        length = (node.end_lineno or node.lineno) - node.lineno + 1
        if length >= MAX_FUNCTION_LINES:
            found.append(f"{where} {node.name} is {length} lines, at most {MAX_FUNCTION_LINES - 1}")
        if node.args.vararg is not None or node.args.kwarg is not None:
            found.append(f"{where} {node.name} takes *args or **kwargs")
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        if clauses(node) > MAX_COMPREHENSION_CLAUSES:
            found.append(f"{where} a comprehension has {clauses(node)} clauses, at most {MAX_COMPREHENSION_CLAUSES}")
    return found


def source_problems(source: str, path: str) -> list[str]:
    """Every rule broken in one file's source text."""
    found = []
    for node in ast.walk(ast.parse(source)):
        found += node_problems(node, f"{path}:{getattr(node, 'lineno', 0)}")
    return found


def problems(root: Path) -> list[str]:
    """Every rule broken in our Python under `root` (neonrain/, scripts/, test/)."""
    found = []
    for top in OUR_CODE:
        for path in sorted((root / top).rglob("*.py")):
            found += source_problems(path.read_text(), str(path.relative_to(root)))
    return found
