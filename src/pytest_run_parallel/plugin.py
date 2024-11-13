import functools
import threading
import types

import _pytest.outcomes
import pytest

try:
    import numpy as np

    numpy_available = True
except ImportError:
    numpy_available = False


def pytest_addoption(parser):
    group = parser.getgroup("run-parallel")
    group.addoption(
        "--parallel-threads",
        action="store",
        dest="parallel_threads",
        default=1,
        type=int,
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
    n_workers = item.config.option.parallel_threads
    n_iterations = item.config.option.iterations

    m = item.get_closest_marker("parallel_threads")
    if m is not None:
        n_workers = int(m.args[0])

    m = item.get_closest_marker("iterations")
    if m is not None:
        n_iterations = int(m.args[0])

    m = item.get_closest_marker("thread_unsafe")
    if m is not None:
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
    node = request.node
    n_workers = request.config.option.parallel_threads
    m = node.get_closest_marker("parallel_threads")
    if m is not None:
        n_workers = int(m.args[0])
    return n_workers


@pytest.fixture
def num_iterations(request):
    node = request.node
    n_iterations = request.config.option.iterations
    m = node.get_closest_marker("iterations")
    if m is not None:
        n_iterations = int(m.args[0])
    return n_iterations


class ThreadComparator:
    def __init__(self, n_threads):
        self._barrier = threading.Barrier(n_threads)
        self._reset_evt = threading.Event()
        self._entry_barrier = threading.Barrier(n_threads)

        self._thread_ids = []
        self._values = {}
        self._entry_lock = threading.Lock()
        self._entry_counter = 0

    def __call__(self, **values):
        """
        Compares a set of values across threads.

        For each value, type equality as well as comparison takes place. If any
        of the values is a function, then address comparison is performed.
        Also, if any of the values is a `numpy.ndarray`, then approximate
        numerical comparison is performed.
        """
        tid = id(threading.current_thread())
        self._entry_barrier.wait()
        with self._entry_lock:
            if self._entry_counter == 0:
                # Reset state before comparison
                self._barrier.reset()
                self._reset_evt.clear()
                self._thread_ids = []
                self._values = {}
                self._entry_barrier.reset()
            self._entry_counter += 1

        self._values[tid] = values
        self._thread_ids.append(tid)
        self._barrier.wait()

        if tid == self._thread_ids[0]:
            thread_ids = list(self._values)
            try:
                for value_name in values:
                    for i in range(1, len(thread_ids)):
                        tid_a = thread_ids[i - 1]
                        tid_b = thread_ids[i]
                        value_a = self._values[tid_a][value_name]
                        value_b = self._values[tid_b][value_name]
                        assert type(value_a) is type(value_b)
                        if numpy_available and isinstance(value_a, np.ndarray):
                            if len(value_a.shape) == 0:
                                assert value_a == value_b
                            else:
                                assert np.allclose(value_a, value_b, equal_nan=True)
                        elif isinstance(value_a, types.FunctionType):
                            assert id(value_a) == id(value_b)
                        elif value_a != value_a:
                            assert value_b != value_b
                        else:
                            assert value_a == value_b
            finally:
                self._entry_counter = 0
                self._reset_evt.set()
        else:
            self._reset_evt.wait()


@pytest.fixture
def thread_comp(num_parallel_threads):
    return ThreadComparator(num_parallel_threads)
