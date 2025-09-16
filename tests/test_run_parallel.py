import os

import pytest

try:
    import hypothesis
except ImportError:
    hypothesis = None


def test_default_threads(pytester):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest
        from threading import Lock

        class Counter:
            def __init__(self):
                self._count = 0
                self._lock = Lock()

            def increase(self):
                with self._lock:
                    self._count += 1

        @pytest.fixture(scope='session')
        def counter():
            return Counter()

        @pytest.mark.order(1)
        def test_thread_increase(counter):
            counter.increase()

        @pytest.mark.order(2)
        @pytest.mark.parallel_threads(1)
        def test_check_thread_count(counter):
            assert counter._count == 10
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_check_thread_count PASSED*",
        ]
    )

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_marker(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest
        from threading import Lock

        class Counter:
            def __init__(self):
                self._count = 0
                self._lock = Lock()

            def increase(self):
                with self._lock:
                    self._count += 1

        @pytest.fixture(scope='session')
        def counter():
            return Counter()

        @pytest.fixture(scope='session')
        def counter2():
            return Counter()

        @pytest.mark.order(1)
        def test_thread_increase(counter):
            counter.increase()

        @pytest.mark.order(1)
        @pytest.mark.parallel_threads(5)
        def test_thread_increase_five(counter2):
            counter2.increase()

        @pytest.mark.order(2)
        @pytest.mark.parallel_threads(1)
        def test_check_thread_count(counter):
            assert counter._count == 10

        @pytest.mark.order(2)
        @pytest.mark.parallel_threads(1)
        def test_check_thread_count2(counter2):
            assert counter2._count == 5
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_check_thread_count PASSED*",
            "*::test_check_thread_count2 PASSED*",
        ]
    )

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_unittest_compat(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest
        import unittest
        from threading import Lock

        class Counter:
            def __init__(self):
                self._count = 0
                self._lock = Lock()

            def increase(self):
                with self._lock:
                    self._count += 1

        class TestExample(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                cls.counter = Counter()
                cls.counter2 = Counter()

            @pytest.mark.order(1)
            def test_example_1(self):
                self.counter.increase()

            @pytest.mark.order(1)
            @pytest.mark.parallel_threads(5)
            def test_example_2(self):
                self.counter2.increase()

            @pytest.mark.order(2)
            @pytest.mark.parallel_threads(1)
            def test_check_thread_count(self):
                assert self.counter._count == 10

            @pytest.mark.order(2)
            @pytest.mark.parallel_threads(1)
            def test_check_thread_count2(self):
                assert self.counter2._count == 5
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_check_thread_count PASSED*",
            "*::test_check_thread_count2 PASSED*",
        ]
    )

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_help_message(pytester):
    result = pytester.runpytest(
        "--help",
    )
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "run-parallel:",
            "  --parallel-threads=PARALLEL_THREADS",
            "  --iterations=ITERATIONS",
        ]
    )


def test_skip(pytester):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest

        def test_skipped():
            pytest.skip('Skip propagation')
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_skipped SKIPPED*",
        ]
    )

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_fail(pytester):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest

        def test_should_fail():
            pytest.fail()
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_should_fail PARALLEL FAILED*",
        ]
    )

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret != 0


def test_exception(pytester):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest

        def test_should_fail():
            raise ValueError('Should raise')
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_should_fail PARALLEL FAILED*",
        ]
    )

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret != 0


def test_num_parallel_threads_fixture(pytester):
    """Test that the num_parallel_threads fixture works as expected."""

    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest

        def test_should_yield_global_threads(num_parallel_threads):
            assert num_parallel_threads == 10

        @pytest.mark.parallel_threads(2)
        def test_should_yield_marker_threads(num_parallel_threads):
            assert num_parallel_threads == 2

        @pytest.mark.parallel_threads(1)
        def test_single_threaded(num_parallel_threads):
            assert num_parallel_threads == 1
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_should_yield_global_threads PARALLEL PASSED*",
            "*::test_should_yield_marker_threads PARALLEL PASSED*",
            "*::test_single_threaded PASSED*",
            "*1 test was not run in parallel because of use of "
            "thread-unsafe functionality, to list the tests that "
            "were not run in parallel, re-run while setting PYTEST_RUN_PARALLEL_VERBOSE=1"
            " in your shell environment",
        ]
    )

    # Re-run with verbose output
    orig = os.environ.get("PYTEST_RUN_PARALLEL_VERBOSE", "0")
    os.environ["PYTEST_RUN_PARALLEL_VERBOSE"] = "1"

    result = pytester.runpytest("--parallel-threads=10", "-v")
    os.environ["PYTEST_RUN_PARALLEL_VERBOSE"] = orig

    result.stdout.fnmatch_lines(
        ["*pytest-run-parallel report*", "*::test_single_threaded*"],
        consecutive=True,
    )


def test_iterations_marker_one_thread(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest
        from threading import Lock

        class Counter:
            def __init__(self):
                self._count = 0
                self._lock = Lock()

            def increase(self):
                with self._lock:
                    self._count += 1

        @pytest.fixture(scope='session')
        def counter():
            return Counter()

        @pytest.mark.order(1)
        @pytest.mark.parallel_threads(1)
        @pytest.mark.iterations(10)
        def test_thread_increase(counter):
            counter.increase()

        @pytest.mark.order(2)
        @pytest.mark.parallel_threads(1)
        @pytest.mark.iterations(1)
        def test_check_thread_count(counter):
            assert counter._count == 10
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_check_thread_count PASSED*",
        ]
    )

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_iterations_config_one_thread(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest
        from threading import Lock

        class Counter:
            def __init__(self):
                self._count = 0
                self._lock = Lock()

            def increase(self):
                with self._lock:
                    self._count += 1

        @pytest.fixture(scope='session')
        def counter():
            return Counter()

        @pytest.mark.order(1)
        @pytest.mark.parallel_threads(1)
        def test_thread_increase(counter):
            counter.increase()

        @pytest.mark.order(2)
        @pytest.mark.parallel_threads(1)
        @pytest.mark.iterations(1)
        def test_check_thread_count(counter):
            assert counter._count == 10
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--iterations=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_check_thread_count PASSED*",
        ]
    )

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_multiple_iterations_multiple_threads(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest
        from threading import Lock

        class Counter:
            def __init__(self):
                self._count = 0
                self._lock = Lock()

            def increase(self):
                with self._lock:
                    self._count += 1

        @pytest.fixture(scope='session')
        def counter():
            return Counter()

        @pytest.mark.order(1)
        @pytest.mark.parallel_threads(10)
        @pytest.mark.iterations(10)
        def test_thread_increase(counter):
            counter.increase()

        @pytest.mark.order(2)
        @pytest.mark.parallel_threads(1)
        @pytest.mark.iterations(1)
        def test_check_thread_count(counter):
            assert counter._count == 10 * 10
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_check_thread_count PASSED*",
        ]
    )

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_num_iterations_fixture(pytester):
    """Test that the num_iterations fixture works as expected."""

    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest

        def test_should_yield_global_threads(num_iterations):
            assert num_iterations == 10

        @pytest.mark.iterations(2)
        def test_should_yield_marker_threads(num_iterations):
            assert num_iterations == 2
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--iterations=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_should_yield_global_threads PASSED*",
            "*::test_should_yield_marker_threads PASSED*",
        ]
    )


def test_skipif_marker_works(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest

        VAR = 1

        @pytest.mark.skipif('VAR == 1', reason='VAR is 1')
        def test_should_skip():
            pass
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_should_skip SKIPPED*",
        ]
    )


def test_incompatible_test_item(pytester):
    pytester.makeconftest("""
    import inspect
    import pytest

    class CustomItem(pytest.Item):
        def __init__(self, name, parent=None, config=None, session=None, nodeid=None, function=None, **kwargs):
            super().__init__(name, parent, config, session, nodeid, **kwargs)
            self.function = function

        def runtest(self):
            self.function()

    @pytest.hookimpl(wrapper=True, trylast=True)
    def pytest_pycollect_makeitem(collector, name: str, obj: object):
        result = yield
        if not inspect.isfunction(obj):
            return result
        return CustomItem.from_parent(name=name, parent=collector, function=obj)
    """)

    pytester.makepyfile("""
    import pytest

    def test_incompatible_item():
        assert True
    """)
    result = pytester.runpytest("--parallel-threads=10", "-v", "-W", "default")
    result.stdout.fnmatch_lines(
        [
            "*::test_incompatible_item PASSED*",
        ]
    )
    assert result.parseoutcomes()["warnings"] == 1


def test_known_incompatible_test_item_doesnt_warn(pytester):
    pytester.makeconftest("""
    import inspect
    import pytest

    class CustomItem(pytest.Item):
        def __init__(self, name, parent=None, config=None, session=None, nodeid=None, function=None, **kwargs):
            super().__init__(name, parent, config, session, nodeid, **kwargs)
            self.function = function
            self._parallel_custom_item = True

        def runtest(self):
            self.function()

    @pytest.hookimpl(wrapper=True, trylast=True)
    def pytest_pycollect_makeitem(collector, name: str, obj: object):
        result = yield
        if not inspect.isfunction(obj):
            return result
        return CustomItem.from_parent(name=name, parent=collector, function=obj)
    """)

    pytester.makepyfile("""
    import pytest

    def test_incompatible_item():
        assert True
    """)
    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            "*::test_incompatible_item PASSED*",
        ]
    )
    result.stderr.no_fnmatch_line(
        "*Encountered pytest item with type <class 'conftest.CustomItem'> "
        "with no 'obj'*"
    )
    assert "warnings" not in result.parseoutcomes().keys()


def test_all_tests_in_parallel(pytester):
    pytester.makepyfile("""
    def test_parallel_1(num_parallel_threads):
        assert num_parallel_threads == 10

    def test_parallel_2(num_parallel_threads):
        assert num_parallel_threads == 10
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            "*All tests were run in parallel! 🎉*",
        ]
    )

    # re-run with PYTEST_RUN_PARALLEL_VERBOSE=1
    orig = os.environ.get("PYTEST_RUN_PARALLEL_VERBOSE", "0")
    os.environ["PYTEST_RUN_PARALLEL_VERBOSE"] = "1"
    result = pytester.runpytest("--parallel-threads=10", "-v")
    os.environ["PYTEST_RUN_PARALLEL_VERBOSE"] = orig

    result.stdout.fnmatch_lines(
        [
            "*All tests were run in parallel! 🎉*",
        ]
    )


def test_doctests_marked_thread_unsafe(pytester):
    pytester.makepyfile("""
    def test_parallel(num_parallel_threads):
        assert num_parallel_threads == 10
    """)

    pytester.makefile(
        ".txt",
        """
    hello this is a doctest
    >>> x = 3
    >>> x
    3
    >>> num_parallel_threads = getfixture("num_parallel_threads")
    >>> num_parallel_threads
    1
    """,
    )

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            "*::test_parallel PARALLEL PASSED*",
            "*::test_doctests_marked_thread_unsafe.txt PASSED*",
        ]
    )


@pytest.mark.skipif(hypothesis is None, reason="hypothesis needs to be installed")
def test_runs_hypothesis_in_parallel(pytester):
    pytester.makepyfile("""
    from hypothesis import given, strategies as st, settings, HealthCheck

    @given(a=st.none())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_uses_hypothesis(a, num_parallel_threads):
        assert num_parallel_threads == 10
    """)
    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            "*::test_uses_hypothesis PARALLEL PASSED*",
        ]
    )


def test_fail_warning_gil_enabled_during_execution(pytester):
    test_name = "test_fail_warning_gil_enabled_during_execution"
    pytester.makepyfile(f"""
    import warnings

    def {test_name}():
        warnings.warn(
            "The global interpreter lock (GIL) has been enabled to load module 'module'",
            RuntimeWarning
        )
    """)
    result = pytester.runpytest("-v", "-W", "default")
    assert result.ret == 1
    result.stdout.fnmatch_lines(
        [
            f"*GIL was dynamically re-enabled during test execution of '{test_name}.py::{test_name}' to load module 'module'*"
        ]
    )


def test_fail_warning_gil_enabled_during_collection(pytester):
    test_name = "test_fail_warning_gil_enabled_during_collection"
    pytester.makepyfile(f"""
    import warnings
    warnings.warn(
        "The global interpreter lock (GIL) has been enabled to load module 'module'",
        RuntimeWarning
    )

    def {test_name}():
        assert True
    """)
    result = pytester.runpytest("-v", "-W", "default")
    assert result.ret == 1
    result.stdout.fnmatch_lines(
        [
            "*GIL was dynamically re-enabled during test collection to load module 'module'*"
        ]
    )


def test_warning_gil_enabled_ignore_option(pytester):
    pytester.makepyfile("""
    import warnings
    warnings.warn(
        "The global interpreter lock (GIL) has been enabled to load module 'module'",
        RuntimeWarning
    )

    def test_warning_gil_enabled_ignore_option():
        assert True
    """)
    result = pytester.runpytest("-v", "--ignore-gil-enabled", "-W", "default")
    assert result.ret == 0
