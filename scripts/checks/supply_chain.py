"""docs/SUPPLY-CHAIN.md's rules a file can show (test/test_supply_chain.py): no workflow, no hook, no worm,
and every outside import under neonrain/ is in requirements.lock or the standard library."""
import json
import re
import sys
from importlib.metadata import packages_distributions
from pathlib import Path

from scripts.checks import imports, modules

WORM_FILES: frozenset[str] = frozenset({"setup_bun.js", "bun_environment.js", "Math_Symbol.js", "gh-token-monitor"})
SKIPPED_DIRS: frozenset[str] = frozenset({".git", ".venv", "mutants", "__pycache__", ".pytest_cache", ".ruff_cache"})


def ours(root: Path) -> list[Path]:
    """Every file under root but the ones git, the venv and the tools make."""
    return [path for path in root.rglob("*") if path.is_file() and not SKIPPED_DIRS & set(path.relative_to(root).parts)]


def worm_problems(root: Path) -> list[str]:
    """The named worm artefacts, anywhere; setup.mjs only inside .claude/ or .vscode/ (rule 7)."""
    found = []
    for path in ours(root):
        where = path.relative_to(root)
        in_editor_dir = where.parts[0] in (".claude", ".vscode")
        if path.name in WORM_FILES or (path.name == "setup.mjs" and in_editor_dir):
            found.append(f"{where} is a known worm artefact: stop, change nothing, report it")
    return found


# Decision: R-003 (no workflow); docs/SUPPLY-CHAIN.md rule 4 (no hooks)
def hook_problems(root: Path) -> list[str]:
    """A workflow, a Claude Code hook, a folder-open task, or a git hook."""
    found = [f"{p.relative_to(root)} is a workflow (R-003)" for p in (root / ".github" / "workflows").rglob("*") if p.is_file()]
    for name in ("settings.json", "settings.local.json"):
        path = root / ".claude" / name
        if path.is_file() and "hooks" in json.loads(path.read_text()):
            found.append(f".claude/{name} has hooks")
    tasks = root / ".vscode" / "tasks.json"
    if tasks.is_file() and "folderOpen" in tasks.read_text():
        found.append(".vscode/tasks.json runs a task on folder open")
    git = root / ".git"
    if git.is_dir():
        found += [f".git/hooks/{p.name} is a git hook" for p in (git / "hooks").glob("*") if not p.name.endswith(".sample")]
        if "hookspath" in (git / "config").read_text().lower():
            found.append(".git/config sets core.hooksPath")
    return found


def locked(lock: str) -> set[str]:
    """The distributions a lock pins, normalised: "Typing_Extensions==4.1 \\" gives {"typing-extensions"}."""
    return {re.sub(r"[-_.]+", "-", m).lower() for m in re.findall(r"^([A-Za-z0-9_.-]+)==", lock, re.MULTILINE)}


def unlocked(name: str, pinned: set[str], providers: dict[str, list[str]]) -> bool:
    """Whether an imported top-level name is neither standard library nor provided by a pinned distribution."""
    if name in sys.stdlib_module_names:
        return False
    return not {re.sub(r"[-_.]+", "-", d).lower() for d in providers.get(name, [])} & pinned


def import_problems(root: Path) -> list[str]:
    """Outside imports under neonrain/ the lock does not pin, and brokers anywhere in our code (MOD-03)."""
    pinned = locked((root / "requirements.lock").read_text())
    providers = packages_distributions()
    found = []
    for path in sorted(root.glob("neonrain/**/*.py")):
        for node in imports.statements(path.read_text()):
            names = [n for n in imports.external(node) if unlocked(n, pinned, providers)]
            found += [f"{path.relative_to(root)} imports {n}, which requirements.lock does not pin" for n in names]
    for path in sorted(root.glob("scripts/**/*.py")) + sorted(root.glob("test/**/*.py")):
        for node in imports.statements(path.read_text()):
            found += modules.external_problems(str(path.relative_to(root)), False, imports.external(node))
    return found


def problems(root: Path) -> list[str]:
    """Everything docs/SUPPLY-CHAIN.md forbids that a file under root shows."""
    return worm_problems(root) + hook_problems(root) + import_problems(root)
