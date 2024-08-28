import pytest
import threading
import functools

from _pytest.outcomes import Skipped, Failed


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
