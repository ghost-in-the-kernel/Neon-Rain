"""Shared fixtures: the repository root the doc tests read."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def root() -> Path:
    """The repository root, e.g. /home/user/neon-rain."""
    return ROOT
