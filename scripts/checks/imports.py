"""What a Python file imports, read from its syntax: shared by the module and supply-chain checks."""
import ast
from pathlib import Path


def module_of(path: Path, package: Path) -> str:
    """The neonrain module a file belongs to: neonrain/features/a.py and neonrain/features.py give "features"."""
    first = path.relative_to(package).parts[0]
    return first.removesuffix(".py")


def ours(node: ast.Import | ast.ImportFrom, current: str) -> list[str]:
    """The neonrain modules one import statement reaches, e.g. `from neonrain.ledger import cut` gives ["ledger"]."""
    if isinstance(node, ast.Import):
        return [alias.name.split(".")[1] for alias in node.names if alias.name.startswith("neonrain.")]
    if node.level == 1:
        return [current]
    if node.level >= 2:
        return [node.module.split(".")[0]] if node.module else [alias.name for alias in node.names]
    if node.module == "neonrain":
        return [alias.name for alias in node.names]
    if node.module and node.module.startswith("neonrain."):
        return [node.module.split(".")[1]]
    return []


def external(node: ast.Import | ast.ImportFrom) -> list[str]:
    """The top-level outside packages one import reaches: `import scipy.stats` gives ["scipy"]."""
    if isinstance(node, ast.Import):
        return [alias.name.split(".")[0] for alias in node.names if alias.name.split(".")[0] != "neonrain"]
    if node.level == 0 and node.module and node.module.split(".")[0] != "neonrain":
        return [node.module.split(".")[0]]
    return []


def statements(source: str) -> list[ast.Import | ast.ImportFrom]:
    """Every import statement in a file, at any depth."""
    return [node for node in ast.walk(ast.parse(source)) if isinstance(node, (ast.Import, ast.ImportFrom))]
