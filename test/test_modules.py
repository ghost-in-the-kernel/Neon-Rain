"""Every import under neonrain/ is one docs/modules.json allows; each rule, broken in a planted file, is caught."""
import ast
import shutil
from pathlib import Path

from scripts.checks import modules


def plant(tmp_path: Path, root: Path, files: dict[str, str]) -> Path:
    """A root with the real docs/modules.json and the given neonrain/ files, e.g. {"features/a.py": "x = 1"}."""
    (tmp_path / "docs").mkdir()
    shutil.copy(root / "docs" / "modules.json", tmp_path / "docs" / "modules.json")
    for name, source in files.items():
        path = tmp_path / "neonrain" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    return tmp_path


def test_the_real_code_holds(root: Path) -> None:
    assert modules.problems(root) == []


def test_allowed_imports_hold(tmp_path: Path, root: Path) -> None:
    files = {
        "features/a.py": "from neonrain.ledger import cut\nimport neonrain.universe\nfrom . import b\nimport numpy\n",
        "harness/split.py": "from neonrain import targets, features\nfrom ..features import a\n",
        "scorer/score.py": "import anthropic\n",
        "targets.py": "from neonrain.universe import tickers\n",
    }
    assert modules.problems(plant(tmp_path, root, files)) == []


def test_a_model_client_outside_scorer_is_caught(tmp_path: Path, root: Path) -> None:
    found = modules.problems(plant(tmp_path, root, {"features/news.py": "import anthropic\n"}))
    assert found == ["neonrain/features/news.py imports anthropic: only scorer imports a model client (MOD-01)"]


def test_the_harness_reading_a_player_is_caught(tmp_path: Path, root: Path) -> None:
    found = modules.problems(plant(tmp_path, root, {"harness/run.py": "from neonrain.models import net\n"}))
    assert found == ["neonrain/harness/run.py imports models: harness may import only ['features', 'targets']"]


def test_a_relative_import_of_a_player_is_caught(tmp_path: Path, root: Path) -> None:
    found = modules.problems(plant(tmp_path, root, {"harness/run.py": "from ..baselines import tree\n"}))
    assert found == ["neonrain/harness/run.py imports baselines: harness may import only ['features', 'targets']"]


def test_a_broker_anywhere_is_caught(tmp_path: Path, root: Path) -> None:
    found = modules.problems(plant(tmp_path, root, {"scorer/x.py": "from alpaca_trade_api import REST\n"}))
    assert found == ["neonrain/scorer/x.py imports alpaca_trade_api: no broker or order client, ever (MOD-03)"]


def test_features_naming_the_ledger_files_is_caught(tmp_path: Path, root: Path) -> None:
    found = modules.problems(plant(tmp_path, root, {"features/n.py": "PATH = 'ledger/news.parquet'\n"}))
    assert found == ["neonrain/features/n.py:1 names the ledger's files; read it through ledger (MOD-04)"]


def test_reading_the_clock_is_caught(tmp_path: Path, root: Path) -> None:
    source = "import datetime\nimport time\nfrom time import time_ns\na = datetime.date.today()\nb = time.time()\n"
    found = modules.problems(plant(tmp_path, root, {"targets.py": source}))
    assert found == [f"neonrain/targets.py:{line} reads the clock (MOD-05)" for line in (3, 4, 5)]


def test_importing_a_clock_function_among_others_is_the_clock_and_importing_others_alone_is_not() -> None:
    assert modules.reads_clock(ast.parse("from time import sleep, time").body[0])
    assert not modules.reads_clock(ast.parse("from time import sleep").body[0])


def test_a_module_modules_json_does_not_name_is_caught(tmp_path: Path, root: Path) -> None:
    found = modules.problems(plant(tmp_path, root, {"trading/x.py": "x = 1\n"}))
    assert found == ["neonrain/trading/x.py is in module 'trading', which docs/modules.json does not name"]


def test_the_package_init_is_held_too(tmp_path: Path, root: Path) -> None:
    found = modules.problems(plant(tmp_path, root, {"__init__.py": "import anthropic\nfrom neonrain import models\n"}))
    assert found == [
        "neonrain/__init__.py imports anthropic: only scorer imports a model client (MOD-01)",
        "neonrain/__init__.py imports models: __init__ may import only []",
    ]


def test_every_problem_in_every_file_is_reported(tmp_path: Path, root: Path) -> None:
    files = {"harness/a.py": "import neonrain.models\nimport neonrain.baselines\n", "ledger/b.py": "import neonrain.universe\n"}
    assert modules.problems(plant(tmp_path, root, files)) == [
        "neonrain/harness/a.py imports models: harness may import only ['features', 'targets']",
        "neonrain/harness/a.py imports baselines: harness may import only ['features', 'targets']",
        "neonrain/ledger/b.py imports universe: ledger may import only []",
    ]


def test_the_network_reads_nothing_of_ours_and_only_training_reads_it(root: Path) -> None:
    spec = modules.json.loads((root / "docs" / "modules.json").read_text())["modules"]
    assert spec["models"]["mayImport"] == []
    assert [name for name, entry in spec.items() if "models" in entry["mayImport"]] == ["training"]


def test_the_network_importing_the_harness_is_caught(tmp_path: Path, root: Path) -> None:
    found = modules.problems(plant(tmp_path, root, {"models/net.py": "from neonrain.harness import split\n"}))
    assert found == ["neonrain/models/net.py imports harness: models may import only []"]
