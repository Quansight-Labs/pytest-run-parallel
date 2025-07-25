# pytest-run-parallel

[![PyPI version](https://img.shields.io/pypi/v/pytest-run-parallel.svg)](https://pypi.org/project/pytest-run-parallel)
[![Python versions](https://img.shields.io/pypi/pyversions/pytest-run-parallel.svg)](https://pypi.org/project/pytest-run-parallel)
[![See Build Status on GitHub Actions](https://github.com/Quansight-Labs/pytest-run-parallel/actions/workflows/main.yml/badge.svg)](https://github.com/Quansight-Labs/pytest-run-parallel/actions/workflows/main.yml)

A simple pytest plugin to run tests concurrently

------------------------------------------------------------------------

This [pytest](https://github.com/pytest-dev/pytest) plugin takes a set
of tests that would be normally be run serially and execute them in
parallel.

The main goal of `pytest-run-parallel` is to discover thread-safety
issues that could exist when using C libraries, this is of vital
importance after [PEP703](https://peps.python.org/pep-0703/), which
provides a path for a CPython implementation without depending on the
Global Interpreter Lock (GIL), thus allowing for proper parallelism in
programs that make use of the CPython interpreter.

For more information about C thread-safety issues, please visit the
free-threaded community guide at <https://py-free-threading.github.io/>

## How it works

This plugin is *not* an alternative to
[pytest-xdist](https://pytest-xdist.readthedocs.io/) and does not run
all of the tests in a test suite simultaneously in a thread pool.
Instead, it runs many instances of the same test in a thread pool. It is
only useful as a tool to do multithreaded stress tests using an existing
test suite and is not useful to speed up the execution of a test suite
via multithreaded parallelism.

Given an existing test taking arguments `*args` and keyword arguments
`**kwargs`, this plugin creates a new test that is equivalent to the
following Python code:

```python
import threading
from concurrent.futures import ThreadPoolExecutor

def run_test(b, *args, **kwargs):
    for _ in range(num_iterations):
        b.wait()
        execute_pytest_test(*args, **kwargs)


with ThreadPoolExecutor(max_workers=num_parallel_threads) as tpe:
    b = threading.Barrier(num_parallel_threads)
    for _ in range(num_parallel_threads):
        tpe.submit(run_test, b, *args, **kwargs)
```

The `execute_pytest_test` function hides some magic to ensure errors and
failures get propagated correctly to the main testing thread. Using this
plugin avoids the boilerplate of rewriting existing tests to run in
parallel in a thread pool. Note that `args` and `kwargs` might include
pytest marks and fixtures, and the way this plugin is currently written,
those fixtures are shared between threads.

## Features

- Six global CLI flags:
    - `--parallel-threads` to run a test suite in parallel
    - `--iterations` to run multiple times in each thread
    - `--skip-thread-unsafe` to skip running tests marked as or
      detected to be thread-unsafe.
    - `--mark-warnings-as-unsafe` and `--mark-ctypes-as-unsafe`
       to always skip running tests that use the `warnings` or
       `ctypes` modules, respectively. These are useful if you are
       adding support for Python 3.14 to a library that already
       runs tests under pytest-run-parallel on Python 3.13 or
       older.
    - `--mark-hypothesis-as-unsafe`, to always skip runing tests that
      use [hypothesis](https://github.com/hypothesisworks/hypothesis).
      While newer version of Hypothesis are thread-safe, and versions
      which are not are automatically skipped by `pytest-run-parallel`,
      this flag is an escape hatch in case you run into thread-safety
      problems caused by Hypothesis, or in tests that happen to use
      hypothesis and were skipped in older versions of pytest-run-parallel.


- Three corresponding markers:
    - `pytest.mark.parallel_threads(n)` to mark a single test to run
        in parallel in `n` threads
    - `pytest.mark.thread_unsafe` to mark a single test to run in a
        single thread. It is equivalent to using
        `pytest.mark.parallel_threads(1)`
    - `pytest.mark.iterations(n)` to mark a single test to run `n`
        times in each thread

- And the corresponding fixtures:
    - `num_parallel_threads`: The number of threads the test will run in
    - `num_iterations`: The number of iterations the test will run in
        each thread

**Note**: It's possible to specify `--parallel-threads=auto` or
`pytest.mark.parallel_threads("auto")` which will let
`pytest-run-parallel` choose the number of logical CPU cores available
to the testing process. If that cannot be determined, the number of
physical CPU cores will be used. If that fails as well, it will fall
back to running all tests single-threaded.

## Requirements

`pytest-run-parallel` depends exclusively on `pytest`. Optionally
intalling `psutil` will help with identifying the number of logical
cores available to the testing process in systems where that's not
possible with the Python stdlib.

## Installation

You can install "pytest-run-parallel" via
[pip](https://pypi.org/project/pip/) from
[PyPI](https://pypi.org/project):

    $ pip install pytest-run-parallel

If you want to additionally install `psutil` you can run:

    $ pip install pytest-run-parallel[psutil]

## Caveats

Pytest itself is not thread-safe and it is not safe to share stateful
pytest fixtures or marks between threads. Existing tests relying on
setting up mutable state via a fixture will see the state shared between
threads. Tests that dynamically set marks or share marks will also
likely not be thread-safe. See the pytest documentation [for more
detail](https://docs.pytest.org/en/stable/explanation/flaky.html#thread-safety)
and the community-maintained [free threaded Python porting
guide](https://py-free-threading.github.io/porting/#pytest-is-not-thread-safe)
for more detail about using pytest in a multithreaded context on the
free-threaded build of Python.

We suggest marking tests that are incompatible with this plugin's
current design with `@pytest.mark.thread_unsafe` or
`@pytest.mark.thread_unsafe(reason="...")`.

The following functions and modules are known to be thread-unsafe and
pytest-run-parallel will automatically skip running tests using them in
parallel:

- The pytest `capsys` fixture
- The pytest `monkeypath` fixture

The following fixtures are known to be thread-unsafe on Python 3.13 and older,
or on 3.14 and newer if Python isn't configured correctly:

- `pytest.warns`
- `pytest.deprecated_call`
- The pytest `recwarn` fixture
- `warnings.catch_warnings`
- `unittest.mock`
- `ctypes`

If an older version of `hypothesis` that is known to be thread-unsafe is
installed, tests using `hypothesis` are skipped.

Additionally, if a set of fixtures is known to be thread unsafe, tests
that use them can be automatically marked as thread unsafe by declaring
them under the <span class="title-ref">thread_unsafe_fixtures</span>
option under pytest INI configuration file:

```ini
[pytest]
thread_unsafe_fixtures =
    fixture_1
    fixture_2
    ...
```

Or under the section `tool.pytest.ini_options` if using `pyproject.toml`:

```toml
[tool.pytest.ini_options]
thread_unsafe_fixtures = [
    'fixture_1',
    'fixture_2',
    ...
]
```

Similarly, if a function is known to be thread unsafe and should cause a
test to be marked as thread-unsafe as well, its fully-qualified name can
be registered through the `thread_unsafe_functions` option in the INI file
(or under `tool.pytest.ini_options` when using `pyproject.toml`):

```ini
[pytest]
thread_unsafe_functions =
    module.submodule.func1
    module.submodule2.func2
    ...
```

You can also blocklist entire modules by using an asterisk:

```ini
[pytest]
thread_unsafe_functions =
    module1.*
    module2.submodule.*
    ...
```

Also, if you define a `__thread_safe__ = False` attribute on a function
that is called by a test and is up to two levels below in the call stack,
then pytest-run-parallel will automatically detect that a thread-unsafe
function is being used and will mark the test as thread-unsafe.

## Usage

This plugin has two modes of operation, one via the `--parallel-threads`
and `--iterations` pytest CLI flags, which allows a whole test suite to
be run in parallel:

    $ pytest --parallel-threads=10 --iterations=10 tests

By default, the value for both flags will be 1, thus not modifying the
usual behaviour of pytest except when the flag is set.

Note that using `pytest-xdist` and setting `iterations` to a number
greater than one might cause tests to run even more times than intended.

The other mode of operation occurs at the individual test level, via the
`pytest.mark.parallel_threads` and `pytest.mark.iterations` markers:

```python
# test_file.py
import pytest

@pytest.fixture
def my_fixture():
    ...

@pytest.mark.parallel_threads(2)
@pytest.mark.iterations(10)
def test_something_1():
    # This test will be run in parallel using two concurrent threads
    # and 10 times in each thread
    ...

@pytest.mark.parametrize('arg', [1, 2, 3])
@pytest.mark.parallel_threads(3)
def test_fixture(my_fixture, arg):
    # pytest markers and fixtures are supported as well
    ...
```

Both modes of operations are supported simultaneously, i.e.,

```bash
# test_something_1 and test_fixture will be run using their set number of
# threads; other tests will be run using 5 threads.
$ pytest -x -v --parallel-threads=5 test_file.py
```

You can skip tests marked as or detected to be thread-unsafe by passing
`--skip-thread-unsafe` in your pytest invocation. This is useful when running
pytest-run-parallel under [Thread
Sanitizer](https://clang.llvm.org/docs/ThreadSanitizer.html). Setting
`--skip-thread-unsafe=True` will avoid unnecessarily running tests where thread
sanitizer cannot detect races because the test is not parallelized.

Older versions of pytest-run-parallel always marked tests using the `warnings`
and `ctypes` modules as thread-unsafe, since both were not thread-safe until
Python 3.14. If you are adding support for Python 3.14 and would like to
continue marking tests that use `warnings` or `ctypes`, pass
`--mark-warnings-as-unsafe` or `--mark-ctypes-as-unsafe`, respectively, in your
`pytest` invocation.

Additionally, `pytest-run-parallel` exposes the `num_parallel_threads`
and `num_iterations` fixtures which enable a test to be aware of the
number of threads that are being spawned and the number of iterations
each test will run:

```python
# test_file.py
import pytest

def test_skip_if_parallel(num_parallel_threads):
    if num_parallel_threads > 1:
        pytest.skip(reason='does not work in parallel')
    ...
```

Finally, the `thread_comp` fixture allows for parallel test debugging,
by providing an instance of `ThreadComparator`, whose `__call__` method
allows to check if all the values produced by all threads during an
specific execution step are the same:

``` python
# test_file.py
def test_same_execution_values(thread_comp):
    a = 2
    b = [3, 4, 5]
    c = None
    # Check that the values for a, b, c are the same across tests
    thread_comp(a=a, b=b, c=c)
```

## Tracing

If you run pytest with verbose output (e.g. by passing `-v` in your
pytest invocation), you will see that tests are annotated to either
"PASS" or "PARALLEL PASS". A "PASS" indicates the test was run on a
single thread, whereas "PARALLEL PASS" indicates the test passed and was
run in a thread pool. If a test was not run in a thread pool because
pytest-run-parallel detected use of thread-unsafe functionality, the
reason will be printed as well.

If you are running pytest in the default configuration without `-v`,
then tests that pass in a thread pool will be annotated with a slightly
different dot character, allowing you to visually pick out when tests
are not run in parallel.

For example in the output for this file:

```
tests/test_kx.py ·....·
```

Only the first and last tests are run in parallel.

In order to list the tests that were marked as thread-unsafe and were
not executed in parallel, you can set the `PYTEST_RUN_PARALLEL_VERBOSE`
environment variable to 1.

## Contributing

Contributions are very welcome. Tests can be run with
[tox](https://tox.readthedocs.io/en/latest/), please ensure the coverage
at least stays the same before you submit a pull request.

## License

Distributed under the terms of the
[MIT](https://opensource.org/licenses/MIT) license,
"pytest-run-parallel" is free and open source software

## Issues

If you encounter any problems, please [file an
issue](https://github.com/Quansight-Labs/pytest-run-parallel/issues)
along with a detailed description.
