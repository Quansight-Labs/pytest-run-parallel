from setuptools import Extension, setup

ext_modules = [
    Extension(
        "gil_test.gil_enable",
        sources=["gil_test.c"],
        define_macros=[("ENABLE_GIL", "1")],
    ),
    Extension(
        "gil_test.gil_disable",
        sources=["gil_test.c"],
    ),
]

setup(
    name="gil_test",
    ext_modules=ext_modules,
)
