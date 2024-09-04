import pytest
import threading
import functools
import types

from _pytest.outcomes import Skipped, Failed

try:
    import numpy as np
    numpy_available = True
except ImportError:
    numpy_available = False


def pytest_addoption(parser):
    group = parser.getgroup('run-parallel')
    group.addoption(
        '--parallel-threads',
        action='store',
        dest='parallel_threads',
        default=1,
        type=int,
        help='Set the number of threads used to execute each test concurrently.'
    )


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'parallel_threads(n): run the given test function in parallel '
        'using `n` threads.')


def wrap_function_parallel(fn, n_workers=10):
    barrier = threading.Barrier(n_workers)
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        errors = []
        skip = None
        failed = None
        def closure(*args, **kwargs):
            barrier.wait()
            try:
                fn(*args, **kwargs)
            except Warning as w:
                pass
            except Exception as e:
                errors.append(e)
            except Skipped as s:
                nonlocal skip
                skip = s.msg
            except Failed as f:
                nonlocal failed
                failed = f

        workers = []
        for _ in range(0, n_workers):
            worker_kwargs = kwargs
            workers.append(threading.Thread(
                target=closure,
                args=args, kwargs=worker_kwargs))

        for worker in workers:
            worker.start()

        for worker in workers:
            worker.join()

        if skip is not None:
            pytest.skip(skip)
        elif failed is not None:
            raise failed
        elif len(errors) > 0:
            raise errors[0]

    return inner


@pytest.hookimpl(trylast=True)
def pytest_itemcollected(item):
    n_workers = item.config.option.parallel_threads
    m = item.get_closest_marker('parallel_threads')
    if m is not None:
        n_workers = int(m.args[0])
    if n_workers is not None and n_workers > 1:
        item.obj = wrap_function_parallel(item.obj, n_workers)


@pytest.fixture
def num_parallel_threads(request):
    node = request.node
    n_workers = request.config.option.parallel_threads
    m = node.get_closest_marker('parallel_threads')
    if m is not None:
        n_workers = int(m.args[0])
    return n_workers


class ThreadComparator:

    def __init__(self, n_threads):
        self._barrier = threading.Barrier(n_threads)
        self._reset_evt = threading.Event()
        self._thread_ids = []
        self._values = {}

    def compare(self, values):
        tid = threading.get_ident()
        self._values[tid] = values
        self._thread_ids.append(tid)
        self._barrier.wait()

        if tid == self._thread_ids[0]:
            thread_ids = list(self._values)
            for value_name in values:
                for i in range(1, len(thread_ids)):
                    tid_a = thread_ids[i - 1]
                    tid_b = thread_ids[i]
                    value_a = self._values[tid_a][value_name]
                    value_b = self._values[tid_b][value_name]
                    try:
                        assert type(value_a) is type(value_b)
                        if numpy_available and isinstance(value_a, np.ndarray):
                            if len(value_a.shape) == 0:
                                assert value_a == value_b
                            else:
                                assert np.allclose(value_a, value_b)
                        elif isinstance(value_a, types.FunctionType):
                            assert id(value_a) == id(value_b)
                        else:
                            assert value_a == value_b
                    finally:
                        self._reset_evt.set()

            self._thread_ids = []
            self._values = {}
            self._barrier.reset()
            self._reset_evt.set()
        else:
            self._reset_evt.wait()


@pytest.fixture
def thread_comp(num_parallel_threads):
    return ThreadComparator(num_parallel_threads)
