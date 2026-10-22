"""Every import under neonrain/ is one docs/modules.json allows, and MOD-01 to MOD-05 hold (test/test_modules.py)."""
import ast
import json
from pathlib import Path

from scripts.checks import imports

MODEL_CLIENTS: frozenset[str] = frozenset({"anthropic", "openai", "cohere", "mistralai", "groq", "litellm", "langchain"})
BROKERS: frozenset[str] = frozenset({
    "alpaca", "alpaca_trade_api", "ib_insync", "ib_async", "ibapi", "ccxt", "robin_stocks", "tda", "schwab",
    "tastytrade", "oandapyV20", "webull", "etrade", "binance", "coinbase", "kraken", "MetaTrader5",
})
CLOCK_ATTRIBUTES: frozenset[str] = frozenset({"now", "today", "utcnow"})
CLOCK_FUNCTIONS: frozenset[str] = frozenset({"time", "time_ns"})


# Decision: R-008 (MOD-01), R-013 (MOD-03)
def external_problems(where: str, is_scorer: bool, names: list[str]) -> list[str]:
    """MOD-01 and MOD-03 for one file's outside imports; `is_scorer` is whether the file is in neonrain/scorer/."""
    found = [f"{where} imports {name}: only scorer imports a model client (MOD-01)"
             for name in names if name in MODEL_CLIENTS and not is_scorer]
    found += [f"{where} imports {name}: no broker or order client, ever (MOD-03)" for name in names if name in BROKERS]
    return found


def reads_clock(node: ast.AST) -> bool:
    """Whether a node reads the wall clock: datetime.now(), date.today(), time.time(), `from time import time`."""
    if isinstance(node, ast.Attribute) and node.attr in CLOCK_ATTRIBUTES:
        return True
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "time":
        return node.attr in CLOCK_FUNCTIONS
    if isinstance(node, ast.ImportFrom) and node.module == "time":
        return any(alias.name in CLOCK_FUNCTIONS for alias in node.names)
    return False


# Decision: R-008 (MOD-04: features reads the news ledger only through ledger's cut reader)
# Unsure: a string naming the ledger is the only static trace of reading its files directly; a path built
# from parts would pass. The cut reader's own tests (phase 5) are the real defence.
def body_problems(where: str, module: str, source: str) -> list[str]:
    """MOD-04 and MOD-05 for one file's body."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if reads_clock(node):
            found.append(f"{where}:{node.lineno} reads the clock (MOD-05)")
        is_text = isinstance(node, ast.Constant) and isinstance(node.value, str)
        if module == "features" and is_text and "ledger" in node.value.lower():
            found.append(f"{where}:{node.lineno} names the ledger's files; read it through ledger (MOD-04)")
    return found


def file_problems(path: Path, package: Path, allowed: dict[str, list[str]]) -> list[str]:
    """Every module rule one file under neonrain/ breaks."""
    module = imports.module_of(path, package)
    where = str(path.relative_to(package.parent))
    if module not in allowed:
        return [f"{where} is in module {module!r}, which docs/modules.json does not name"]
    source = path.read_text()
    found = []
    for node in imports.statements(source):
        reached = [name for name in imports.ours(node, module) if name not in (module, *allowed[module])]
        found += [f"{where} imports {name}: {module} may import only {allowed[module]}" for name in reached]
        found += external_problems(where, module == "scorer", imports.external(node))
    return found + body_problems(where, module, source)


def problems(root: Path) -> list[str]:
    """Every module rule broken under root/neonrain; [] when there is no neonrain/ yet."""
    spec = json.loads((root / "docs" / "modules.json").read_text())
    # neonrain/__init__.py is held too, as a module that may import nothing of ours.
    allowed = {name: entry["mayImport"] for name, entry in spec["modules"].items()} | {"__init__": []}
    package = root / "neonrain"
    found = []
    for path in sorted(package.rglob("*.py")):
        found += file_problems(path, package, allowed)
    return found
