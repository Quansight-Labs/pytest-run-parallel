import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest_plugins = "pytester"

TESTPKG_DIR = Path(__file__).parent / "testpkg"


@pytest.fixture(scope="session", autouse=True)
def build_gil_test_extension():
    """Build the gil_test extension module for testing."""

    env = os.environ.copy()
    kwargs = dict(cwd=TESTPKG_DIR, env=env, capture_output=True, text=True)

    use_uv = False
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "."],
        **kwargs,
    )

    # If pip is not installed, try uv
    if result.returncode != 0 and "No module named pip" in result.stderr:
        use_uv = True
        result = subprocess.run(
            ["uv", "pip", "install", "."],
            **kwargs,
        )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to build extension: {result.stderr}")

    yield

    if use_uv:
        cmd = ["uv", "pip", "uninstall", "gil_test"]
    else:
        cmd = [sys.executable, "-m", "pip", "uninstall", "gil_test"]
    subprocess.run(cmd, **kwargs)


@pytest.fixture
def pytester_subprocess(pytester: pytest.Pytester):
    # Needed cause otherwise the GIL will only be enabled once
    old_method = pytester._method
    pytester._method = "subprocess"
    yield pytester
    pytester._method = old_method
