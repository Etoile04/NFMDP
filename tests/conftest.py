"""Root conftest for NFM-854 test suite.

Adds the scripts/ directory to sys.path so that test modules can import
evaluation and compatibility scripts without modifying pyproject.toml
or requiring PYTHONPATH configuration in CI.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure scripts/ is importable from test modules
_scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))
