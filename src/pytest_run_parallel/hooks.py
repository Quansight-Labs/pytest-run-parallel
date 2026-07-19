import pytest


@pytest.hookspec
def pytest_run_parallel_get_thread_setups(n_workers):
    """Return None, or a dict mapping fixture names to transform callables.

    Called at collection time to build the thread-setups map. ``n_workers``
    is the number of threads that a wrapped test will actually use, which
    markers such as ``force_parallel_threads`` may set to a different value
    than the ``--parallel-threads`` option. Results are cached per distinct
    thread count, so the hook runs once per count and not once per test.

    Each callable has the signature::

        transform(fixturevalue, *, thread_index) -> fixturevalue

    Transforms run in every worker thread, once per iteration, before the
    barrier that synchronises the start of the test. A transform may also be
    a generator function (or otherwise return a generator): the first yielded
    value is used as the fixture value, and after the test body finishes the
    generator is resumed for teardown. When several generator transforms run,
    teardowns execute in reverse setup order. An exception raised by a
    transform fails the test in every thread.

    Returning None skips this implementation. Non-None dicts from all hook
    implementations are merged per fixture name, and the same name registered
    twice means both transforms run, chained. Transforms from more specific
    hookimpls (which pluggy calls first, such as a nested conftest) are
    applied last, so they can wrap or override the others.

    Per test, only transforms for fixtures requested directly by that test
    are applied. pytest-run-parallel shallow-copies kwargs, then applies
    those transforms in order, chaining values. Note that a wrapped test
    always runs in freshly spawned threads, even when ``n_workers`` is 1 and
    only ``--iterations`` caused the wrapping.
    """
