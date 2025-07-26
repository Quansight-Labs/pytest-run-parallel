import functools
import glob
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

pytest_plugins = "pytester"

TESTPKG_DIR = Path(__file__).parent / "testpkg"


def call_once(func):
    func._called_with_args = set()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if (args, kwargs) in func._called_with_args:
            return
        func._called_with_args.add((args, kwargs))
        return func(*args, **kwargs)

    return wrapper


@call_once
def build_gil_test_extension(gil_enable):
    """Build the gil_test extension module for testing."""

    env = os.environ.copy()
    cmd = [sys.executable, "setup.py", "build_ext", "-i"]
    if gil_enable:
        cmd.append("--enable-gil")

    result = subprocess.run(
        cmd, cwd=TESTPKG_DIR, env=env, capture_output=True, text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to build extension: {result.stderr}")


def pytester_with_module(pytester: pytest.Pytester, *, enable_gil):
    if not bool(sysconfig.get_config_var("Py_GIL_DISABLED")):
        pytest.skip(
            "gil enabling functionality only needs to be tested on the free-threaded build"
        )

    path = f"{TESTPKG_DIR!s}/{'gil_enable' if enable_gil else 'gil_disable'}*.so"
    for file in glob.glob(path):
        shutil.copy(file, pytester.path)

    # Needed cause otherwise the GIL will only be enabled once
    old_method = pytester._method
    pytester._method = "subprocess"
    yield pytester
    pytester._method = old_method


@pytest.fixture()
def pytester_with_gil_enabled_module(pytester):
    yield from pytester_with_module(pytester, enable_gil=True)


@pytest.fixture()
def pytester_with_gil_disabled_module(pytester):
    yield from pytester_with_module(pytester, enable_gil=False)
