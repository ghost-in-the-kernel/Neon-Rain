"""How imports.py reads each form of import statement (shared by test_modules and test_supply_chain)."""
import ast

from scripts.checks import imports


def read(statement: str, current: str = "harness") -> tuple[list[str], list[str]]:
    """The neonrain modules and the outside packages one statement reaches: ("from neonrain import a", ...)."""
    node = ast.parse(statement).body[0]
    assert isinstance(node, (ast.Import, ast.ImportFrom))
    return imports.ours(node, current), imports.external(node)


def test_import_of_a_neonrain_submodule() -> None:
    assert read("import neonrain.ledger.cut") == (["ledger"], [])


def test_import_of_the_package_alone_reaches_no_module() -> None:
    assert read("import neonrain") == ([], [])


def test_import_of_several_names() -> None:
    assert read("import scipy.stats, neonrain.universe, numpy") == (["universe"], ["scipy", "numpy"])


def test_from_a_neonrain_submodule() -> None:
    assert read("from neonrain.ledger.cut import reader") == (["ledger"], [])


def test_from_the_package() -> None:
    assert read("from neonrain import ledger, universe") == (["ledger", "universe"], [])


def test_from_an_outside_submodule() -> None:
    assert read("from scipy.stats import spearmanr") == ([], ["scipy"])


def test_relative_within_the_module() -> None:
    assert read("from . import folds", current="harness") == (["harness"], [])
    assert read("from .folds import split", current="harness") == (["harness"], [])


def test_relative_to_a_sibling_module() -> None:
    assert read("from ..features.price import returns") == (["features"], [])
    assert read("from .. import features, targets") == (["features", "targets"], [])


def test_module_of_a_file_and_of_a_package() -> None:
    from pathlib import Path

    package = Path("/r/neonrain")
    assert imports.module_of(package / "features" / "price.py", package) == "features"
    assert imports.module_of(package / "targets.py", package) == "targets"
