import functools
import sys
import threading
import warnings

import _pytest.outcomes
import pytest

from pytest_run_parallel.utils import (
    ThreadComparator,
    get_num_workers,
    identify_warnings_handling,
)


def pytest_addoption(parser):
    group = parser.getgroup("run-parallel")
    group.addoption(
        "--parallel-threads",
        action="store",
        dest="parallel_threads",
        default=1,
        help="Set the number of threads used to execute each test concurrently.",
    )
    group.addoption(
        "--iterations",
        action="store",
        dest="iterations",
        default=1,
        type=int,
        help="Set the number of threads used to execute each test concurrently.",
    )
    parser.addini(
        "thread_unsafe_fixtures",
        "list of thread-unsafe fixture names that cause a test to "
        "be run sequentially",
        type="linelist",
        default=[],
    )
    parser.addini(
        "thread_unsafe_functions",
        "list of thread-unsafe fully-qualified named functions that cause "
        "a test to run on one thread",
        type="linelist",
        default=[],
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "parallel_threads(n): run the given test function in parallel "
        "using `n` threads.",
    )
    config.addinivalue_line(
        "markers",
        "iterations(n): run the given test function `n` times in each thread",
    )
    config.addinivalue_line(
        "markers",
        "thread_unsafe: mark the test function as single-threaded",
    )


def wrap_function_parallel(fn, n_workers, n_iterations):
    barrier = threading.Barrier(n_workers)
    original_switch = sys.getswitchinterval()
    sys.setswitchinterval(0.000001)

    @functools.wraps(fn)
    def inner(*args, **kwargs):
        errors = []
        skip = None
        failed = None

        def closure(*args, **kwargs):
            for _ in range(n_iterations):
                barrier.wait()
                try:
                    fn(*args, **kwargs)
                except Warning:
                    pass
                except Exception as e:
                    errors.append(e)
                except _pytest.outcomes.Skipped as s:
                    nonlocal skip
                    skip = s.msg
                except _pytest.outcomes.Failed as f:
                    nonlocal failed
                    failed = f

        workers = []
        for _ in range(0, n_workers):
            worker_kwargs = kwargs
            workers.append(
                threading.Thread(target=closure, args=args, kwargs=worker_kwargs)
            )

        num_completed = 0
        try:
            for worker in workers:
                worker.start()
                num_completed += 1
        finally:
            if num_completed < len(workers):
                barrier.abort()

        for worker in workers:
            worker.join()

        sys.setswitchinterval(original_switch)

        if skip is not None:
            pytest.skip(skip)
        elif failed is not None:
            raise failed
        elif errors:
            raise errors[0]

    return inner


_thread_unsafe_fixtures = {
    "capsys",
    "recwarn",
}


@pytest.hookimpl(trylast=True)
def pytest_itemcollected(item):
    n_workers = get_num_workers(item.config, item)
    fixtures = getattr(item, "fixturenames", ())

    n_iterations = item.config.option.iterations
    m = item.get_closest_marker("iterations")
    if m is not None:
        n_iterations = int(m.args[0])

    m = item.get_closest_marker("thread_unsafe")
    if m is not None:
        n_workers = 1
        item.add_marker(pytest.mark.parallel_threads(1))

    if not hasattr(item, "obj"):
        if hasattr(item, "_parallel_custom_item"):
            return
        warnings.warn(
            f"Encountered pytest item with type {type(item)} with no 'obj' "
            "attribute, which is incompatible with pytest-run-parallel. "
            f"Tests using {type(item)} will not run in a thread pool.\n"
            "The pytest-run-parallel plugin only supports custom collection "
            "tree objects that wrap Python functions stored in an attribute "
            "named 'obj'.\n"
            "Define a '_parallel_custom_item' attribute on the pytest item"
            "instance or class to silence this warning.\n"
            "If you do not want to use pytest-run-parallel, uninstall it from "
            "your environment."
        )
        return

    skipped_functions = [
        x.split(".") for x in item.config.getini("thread_unsafe_functions")
    ]
    skipped_functions = {(".".join(x[:-1]), x[-1]) for x in skipped_functions}

    if identify_warnings_handling(item.obj, skipped_functions):
        n_workers = 1
        item.add_marker(pytest.mark.parallel_threads(1))

    unsafe_fixtures = _thread_unsafe_fixtures | set(
        item.config.getini("thread_unsafe_fixtures")
    )

    if any(fixture in fixtures for fixture in unsafe_fixtures):
        n_workers = 1
        item.add_marker(pytest.mark.parallel_threads(1))

    if n_workers > 1 or n_iterations > 1:
        original_globals = item.obj.__globals__
        item.obj = wrap_function_parallel(item.obj, n_workers, n_iterations)
        for name in original_globals:
            if name not in item.obj.__globals__:
                item.obj.__globals__[name] = original_globals[name]


@pytest.fixture
def num_parallel_threads(request):
    return get_num_workers(request.config, request.node)


@pytest.fixture
def num_iterations(request):
    node = request.node
    n_iterations = request.config.option.iterations
    m = node.get_closest_marker("iterations")
    if m is not None:
        n_iterations = int(m.args[0])
    return n_iterations


@pytest.fixture
def thread_comp(num_parallel_threads):
    return ThreadComparator(num_parallel_threads)
