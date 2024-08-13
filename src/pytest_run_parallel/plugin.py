import pytest
import threading
import functools


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


@pytest.hookimpl(trylast=True)
def pytest_generate_tests(metafunc):
    n_workers = metafunc.config.option.parallel_threads
    m = metafunc.definition.get_closest_marker('parallel_threads')
    if m is not None:
        n_workers = int(m.args[0])
    setattr(metafunc.function, '_n_workers', n_workers)


def wrap_function_parallel(fn, n_workers=10):
    barrier = threading.Barrier(n_workers)
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        def closure(*args, **kwargs):
            barrier.wait()
            fn(*args, **kwargs)

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
    return inner


@pytest.hookimpl(wrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    n_workers = getattr(pyfuncitem.obj, '_n_workers', None)
    if n_workers is not None and n_workers > 1:
        pyfuncitem.obj = wrap_function_parallel(pyfuncitem.obj, n_workers)
    return (yield)
