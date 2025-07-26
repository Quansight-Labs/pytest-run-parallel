import sys

from setuptools import Extension, setup

enable_gil = "--enable-gil" in sys.argv
if enable_gil:
    sys.argv.remove("--enable-gil")

define_macros = []
if enable_gil:
    define_macros.append(("ENABLE_GIL", "1"))

gil_test_extension = Extension(
    "gil_enable" if enable_gil else "gil_disable",
    sources=["gil_test.c"],
    define_macros=define_macros,
)

setup(
    name="gil_test",
    ext_modules=[gil_test_extension],
)
