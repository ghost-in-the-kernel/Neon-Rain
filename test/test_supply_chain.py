"""No workflow, hook or worm artefact, and no import the lock lacks; each, planted, is caught (TODO 0.5)."""
import shutil
from pathlib import Path

from scripts.checks import supply_chain


def plant(tmp_path: Path, root: Path, files: dict[str, str]) -> Path:
    """A root with the real requirements.lock and the given files, e.g. {".github/workflows/ci.yml": ""}."""
    shutil.copy(root / "requirements.lock", tmp_path / "requirements.lock")
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def test_the_real_repository_holds(root: Path) -> None:
    assert supply_chain.problems(root) == []


def test_a_clean_plant_holds(tmp_path: Path, root: Path) -> None:
    files = {"neonrain/harness/m.py": "import json\nimport numpy\nimport scipy.stats\nfrom polars import col\n"}
    assert supply_chain.problems(plant(tmp_path, root, files)) == []


def test_an_empty_workflow_is_caught(tmp_path: Path, root: Path) -> None:
    found = supply_chain.problems(plant(tmp_path, root, {".github/workflows/ci.yml": ""}))
    assert found == [".github/workflows/ci.yml is a workflow (R-003)"]


def test_a_claude_hook_is_caught(tmp_path: Path, root: Path) -> None:
    found = supply_chain.problems(plant(tmp_path, root, {".claude/settings.json": '{"hooks": {}}'}))
    assert found == [".claude/settings.json has hooks"]


def test_claude_settings_without_hooks_hold(tmp_path: Path, root: Path) -> None:
    assert supply_chain.problems(plant(tmp_path, root, {".claude/settings.json": '{"model": "x"}'})) == []


def test_a_folder_open_task_is_caught(tmp_path: Path, root: Path) -> None:
    tasks = '{"tasks": [{"runOptions": {"runOn": "folderOpen"}}]}'
    found = supply_chain.problems(plant(tmp_path, root, {".vscode/tasks.json": tasks}))
    assert found == [".vscode/tasks.json runs a task on folder open"]


def test_a_git_hook_is_caught(tmp_path: Path, root: Path) -> None:
    files = {".git/hooks/pre-commit": "#!/bin/sh\n", ".git/hooks/pre-push.sample": "", ".git/config": "[core]\n"}
    assert supply_chain.problems(plant(tmp_path, root, files)) == [".git/hooks/pre-commit is a git hook"]


def test_a_hooks_path_is_caught(tmp_path: Path, root: Path) -> None:
    found = supply_chain.problems(plant(tmp_path, root, {".git/config": "[core]\n\thooksPath = x\n"}))
    assert found == [".git/config sets core.hooksPath"]


def test_worm_artefacts_are_caught(tmp_path: Path, root: Path) -> None:
    files = {"a/setup_bun.js": "", ".vscode/setup.mjs": "", "tools/setup.mjs": ""}
    found = supply_chain.problems(plant(tmp_path, root, files))
    assert sorted(found) == [
        ".vscode/setup.mjs is a known worm artefact: stop, change nothing, report it",
        "a/setup_bun.js is a known worm artefact: stop, change nothing, report it",
    ]


def test_an_import_the_lock_lacks_is_caught(tmp_path: Path, root: Path) -> None:
    found = supply_chain.problems(plant(tmp_path, root, {"neonrain/models/net.py": "import torch\n"}))
    assert found == ["neonrain/models/net.py imports torch, which requirements.lock does not pin"]


def test_a_broker_in_a_script_is_caught(tmp_path: Path, root: Path) -> None:
    found = supply_chain.problems(plant(tmp_path, root, {"scripts/trade.py": "import ccxt\n"}))
    assert found == ["scripts/trade.py imports ccxt: no broker or order client, ever (MOD-03)"]


def test_lock_names_are_normalised() -> None:
    assert supply_chain.locked("Typing_Extensions==4.1 \\\nnumpy==2.0\n    # via x\n") == {"typing-extensions", "numpy"}


def test_worm_artefacts_inside_the_tools_folders_are_not_ours(tmp_path: Path, root: Path) -> None:
    files = {".venv/lib/setup_bun.js": "", "mutants/Math_Symbol.js": "", ".claude/setup.mjs": ""}
    found = supply_chain.problems(plant(tmp_path, root, files))
    assert found == [".claude/setup.mjs is a known worm artefact: stop, change nothing, report it"]


def test_hooks_in_local_settings_are_caught(tmp_path: Path, root: Path) -> None:
    found = supply_chain.problems(plant(tmp_path, root, {".claude/settings.local.json": '{"hooks": {}}'}))
    assert found == [".claude/settings.local.json has hooks"]


def test_every_hook_and_every_unpinned_import_is_reported(tmp_path: Path, root: Path) -> None:
    files = {
        ".github/workflows/a.yml": "", ".git/hooks/pre-push": "", ".git/config": "[core]\n\thooksPath = x\n",
        "neonrain/models/a.py": "import torch\n", "neonrain/scorer/b.py": "import anthropic\n",
        "test/t.py": "import ccxt\n", "scripts/s.py": "import anthropic\n",
    }
    assert supply_chain.problems(plant(tmp_path, root, files)) == [
        ".github/workflows/a.yml is a workflow (R-003)",
        ".git/hooks/pre-push is a git hook",
        ".git/config sets core.hooksPath",
        "neonrain/models/a.py imports torch, which requirements.lock does not pin",
        "neonrain/scorer/b.py imports anthropic, which requirements.lock does not pin",
        "scripts/s.py imports anthropic: only scorer imports a model client (MOD-01)",
        "test/t.py imports ccxt: no broker or order client, ever (MOD-03)",
    ]


def test_distribution_names_are_normalised_before_matching() -> None:
    assert not supply_chain.unlocked("yaml", {"pyyaml"}, {"yaml": ["PyYAML"]})
    assert not supply_chain.unlocked("typing_extensions", {"typing-extensions"}, {"typing_extensions": ["typing_extensions"]})
    assert not supply_chain.unlocked("zope", {"zope-interface"}, {"zope": ["zope.interface"]})
    assert supply_chain.unlocked("yaml", {"numpy"}, {"yaml": ["PyYAML"]})
    assert not supply_chain.unlocked("json", set(), {})
