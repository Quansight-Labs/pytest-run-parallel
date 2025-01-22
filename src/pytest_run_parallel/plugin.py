import functools
import threading

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

        for worker in workers:
            worker.start()

        for worker in workers:
            worker.join()

        if skip is not None:
            pytest.skip(skip)
        elif failed is not None:
            raise failed
        elif errors:
            raise errors[0]

    return inner


@pytest.hookimpl(trylast=True)
def pytest_itemcollected(item):
    n_workers = get_num_workers(item.config, item)

    n_iterations = item.config.option.iterations
    m = item.get_closest_marker("iterations")
    if m is not None:
        n_iterations = int(m.args[0])

    m = item.get_closest_marker("thread_unsafe")
    if m is not None:
        n_workers = 1
        item.add_marker(pytest.mark.parallel_threads(1))

    if identify_warnings_handling(item.obj):
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
