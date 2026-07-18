import pytest


@pytest.hookspec
def pytest_run_parallel_get_wrap_fixtures(n_workers):
    """Return None, or a dict mapping fixture names to transform callables.

    Called once per session to build the global wrap-fixtures map.
    ``n_workers`` is the configured ``--parallel-threads`` value.

    Each callable has the signature::

        transform(fixturevalue, *, thread_index) -> fixturevalue

    A transform may also be a generator function (or otherwise return a
    generator): the first yielded value is used as the fixture value, and after
    the test body finishes the generator is resumed for teardown. When several
    generator transforms run, teardowns execute in reverse setup order.

    Returning None skips this implementation. Non-None dicts from all hook
    implementations are merged by appending transforms per fixture name (same
    name registered twice means both run, in registration order).

    Per test, only transforms for fixtures requested directly by that test are
    applied. pytest-run-parallel shallow-copies kwargs, then applies those
    transforms in order, chaining values.
    """
