import os
from contextlib import suppress

import pytest

try:
    import psutil
except ImportError:
    psutil = None

try:
    from os import process_cpu_count
except ImportError:
    process_cpu_count = None

try:
    from os import sched_getaffinity
except ImportError:
    sched_getaffinity = None


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
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_should_yield_global_threads PARALLEL PASSED*",
            "*::test_should_yield_marker_threads PARALLEL PASSED*",
        ]
    )


def test_thread_comp_fixture(pytester):
    """Test that ThreadComparator works as expected."""

    # create a temporary pytest test module
    pytester.makepyfile("""
        import threading
        import pytest

        class Counter:
            def __init__(self):
                self._value = 0
                self._lock = threading.Lock()

            def get_value_and_increment(self):
                with self._lock:
                    value = int(self._value)
                    self._value += 1
                return value

        def test_value_comparison(num_parallel_threads, thread_comp):
            assert num_parallel_threads == 10
            a = 1
            b = [2, 'string', 1.0]
            c = {'a': -4, 'b': 'str'}
            d = float('nan')
            e = float('inf')
            f = {'a', 'b', '#'}
            thread_comp(a=a, b=b, c=c, d=d, e=e, f=f)

            # Ensure that the comparator can be used again
            thread_comp(g=4)

        @pytest.fixture
        def counter(num_parallel_threads):
            return Counter()

        def test_comparison_fail(thread_comp, counter):
            a = 4
            pos = counter.get_value_and_increment()
            if pos % 2 == 0:
                a = -1
            thread_comp(a=a)
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_value_comparison PARALLEL PASSED*",
            "*::test_comparison_fail PARALLEL FAILED*",
        ]
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


def test_thread_unsafe_marker(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest

        @pytest.mark.thread_unsafe
        def test_should_run_single(num_parallel_threads):
            assert num_parallel_threads == 1

        @pytest.mark.thread_unsafe(reason='this is thread-unsafe')
        def test_should_run_single_2(num_parallel_threads):
            assert num_parallel_threads == 1
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_should_run_single PASSED*",
            "*::test_should_run_single_2 PASSED *thread-unsafe*: this is thread-unsafe*",
        ]
    )


def test_pytest_warns_detection(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest
        import warnings
        import pytest as pyt
        import warnings as w
        from pytest import warns, deprecated_call
        from warnings import catch_warnings

        warns_alias = warns

        def test_single_thread_warns_1(num_parallel_threads):
            with pytest.warns(UserWarning):
                warnings.warn('example', UserWarning)
            assert num_parallel_threads == 1

        def test_single_thread_warns_2(num_parallel_threads):
            with warns(UserWarning):
                warnings.warn('example', UserWarning)
            assert num_parallel_threads == 1

        def test_single_thread_warns_3(num_parallel_threads):
            with pyt.warns(UserWarning):
                warnings.warn('example', UserWarning)
            assert num_parallel_threads == 1

        def test_single_thread_warns_4(num_parallel_threads):
            with warns_alias(UserWarning):
                warnings.warn('example', UserWarning)
            assert num_parallel_threads == 1
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_single_thread_warns_1 PASSED*",
            "*::test_single_thread_warns_2 PASSED*",
            "*::test_single_thread_warns_3 PASSED*",
            "*::test_single_thread_warns_4 PASSED*",
        ]
    )


@pytest.mark.skipif(psutil is None, reason="psutil needs to be installed")
def test_auto_detect_cpus_psutil_affinity(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    import psutil

    monkeypatch.setattr(
        psutil.Process, "cpu_affinity", lambda self: list(range(10)), raising=False
    )

    pytester.makepyfile("""
        def test_auto_detect_cpus(num_parallel_threads):
            assert num_parallel_threads == 10
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=auto", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_auto_detect_cpus PARALLEL PASSED*",
        ]
    )


@pytest.mark.skipif(psutil is None, reason="psutil needs to be installed")
def test_auto_detect_cpus_psutil_cpu_count(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    import psutil

    monkeypatch.setattr(
        psutil.Process, "cpu_affinity", lambda self: None, raising=False
    )
    monkeypatch.setattr(psutil, "cpu_count", lambda: 10)

    pytester.makepyfile("""
        def test_auto_detect_cpus(num_parallel_threads):
            assert num_parallel_threads == 10
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=auto", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_auto_detect_cpus PARALLEL PASSED*",
        ]
    )


@pytest.mark.skipif(
    process_cpu_count is None, reason="process_cpu_count is available in >=3.13"
)
def test_auto_detect_process_cpu_count(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    with suppress(ImportError):
        import psutil

        monkeypatch.setattr(
            psutil.Process, "cpu_affinity", lambda self: None, raising=False
        )
        monkeypatch.setattr(psutil, "cpu_count", lambda: None)

    monkeypatch.setattr("os.process_cpu_count", lambda: 10)

    pytester.makepyfile("""
        def test_auto_detect_cpus(num_parallel_threads):
            assert num_parallel_threads == 10
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=auto", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_auto_detect_cpus PARALLEL PASSED*",
        ]
    )


@pytest.mark.skipif(
    sched_getaffinity is None,
    reason="sched_getaffinity is available certain platforms only",
)
def test_auto_detect_sched_getaffinity(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    with suppress(ImportError):
        import psutil

        monkeypatch.setattr(
            psutil.Process, "cpu_affinity", lambda self: None, raising=False
        )
        monkeypatch.setattr(psutil, "cpu_count", lambda: None)

    monkeypatch.setattr("os.process_cpu_count", lambda: None, raising=False)
    monkeypatch.setattr("os.sched_getaffinity", lambda pid: list(range(10)))

    pytester.makepyfile("""
        def test_auto_detect_cpus(num_parallel_threads):
            assert num_parallel_threads == 10
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=auto", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_auto_detect_cpus PARALLEL PASSED*",
        ]
    )


def test_auto_detect_cpu_count(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    with suppress(ImportError):
        import psutil

        monkeypatch.setattr(
            psutil.Process, "cpu_affinity", lambda self: None, raising=False
        )
        monkeypatch.setattr(psutil, "cpu_count", lambda: None)

    monkeypatch.setattr("os.process_cpu_count", lambda: None, raising=False)
    monkeypatch.setattr("os.sched_getaffinity", lambda pid: None, raising=False)
    monkeypatch.setattr("os.cpu_count", lambda: 10)

    pytester.makepyfile("""
        def test_auto_detect_cpus(num_parallel_threads):
            assert num_parallel_threads == 10
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=auto", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_auto_detect_cpus PARALLEL PASSED*",
        ]
    )


def test_thread_unsafe_fixtures(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest

        @pytest.fixture
        def my_unsafe_fixture():
            pass

        @pytest.fixture
        def my_unsafe_fixture_2():
            pass

        def test_capsys(capsys, num_parallel_threads):
            assert num_parallel_threads == 1

        def test_recwarn(recwarn, num_parallel_threads):
            assert num_parallel_threads == 1

        def test_custom_fixture_skip(my_unsafe_fixture, num_parallel_threads):
            assert num_parallel_threads == 1

        def test_custom_fixture_skip_2(my_unsafe_fixture_2, num_parallel_threads):
            assert num_parallel_threads == 1
    """)

    pytester.makeini("""
    [pytest]
    thread_unsafe_fixtures =
        my_unsafe_fixture
        my_unsafe_fixture_2
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_capsys PASSED *thread-unsafe*: uses thread-unsafe fixture*",
            "*::test_recwarn PASSED *thread-unsafe*: uses thread-unsafe fixture*",
            "*::test_custom_fixture_skip PASSED *thread-unsafe*: uses thread-unsafe fixture*",
            "*::test_custom_fixture_skip_2 PASSED *thread-unsafe*: uses thread-unsafe fixture*",
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
    result = pytester.runpytest("--parallel-threads=10", "-v")
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


def test_thread_unsafe_function_attr(pytester):
    pytester.makepyfile(
        mod_1="""
        def to_skip():
            __thread_safe__ = False

        def not_to_skip():
            __thread_safe__ = True
    """
    )

    pytester.makepyfile(
        mod_2="""
        import mod_1
        from mod_1 import not_to_skip

        def some_fn_calls_skip():
            mod_1.to_skip()

        def some_fn_should_not_skip():
            not_to_skip()

        def marked_for_skip():
            pass
    """
    )

    pytester.makepyfile("""
        import mod_2
        from mod_2 import some_fn_calls_skip

        def test_should_be_marked_1(num_parallel_threads):
            mod_2.some_fn_calls_skip()
            assert num_parallel_threads == 1

        def test_should_not_be_marked(num_parallel_threads):
            mod_2.some_fn_should_not_skip()
            assert num_parallel_threads == 10

        def test_should_be_marked_2(num_parallel_threads):
            mod_2.marked_for_skip()
            assert num_parallel_threads == 1

        def test_should_be_marked_3(num_parallel_threads):
            some_fn_calls_skip()
            assert num_parallel_threads == 1
    """)

    pytester.makeini("""
    [pytest]
    thread_unsafe_functions =
        mod_2.marked_for_skip
    """)

    # run pytest with the following cmd args
    orig = os.environ.get("PYTEST_RUN_PARALLEL_VERBOSE", "0")
    os.environ["PYTEST_RUN_PARALLEL_VERBOSE"] = "0"
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*Collected 1 items to run in parallel*",
            "*::test_should_be_marked_1 PASSED *thread-unsafe*inferred via func.__thread_safe__*",
            "*::test_should_not_be_marked PARALLEL PASSED*",
            "*::test_should_be_marked_2 PASSED *thread-unsafe*marked_for_skip*",
            "*::test_should_be_marked_3 PASSED *thread-unsafe*inferred via func.__thread_safe__*",
        ]
    )

    result.stdout.fnmatch_lines(
        [
            "*3 tests were not run in parallel because of use of thread-unsafe "
            "functionality, to list the tests that were skipped, "
            "re-run while setting PYTEST_RUN_PARALLEL_VERBOSE=1 in your "
            "shell environment*",
        ]
    )

    # re-run with PYTEST_RUN_PARALLEL_VERBOSE=1
    os.environ["PYTEST_RUN_PARALLEL_VERBOSE"] = "1"
    result = pytester.runpytest("--parallel-threads=10", "-v")
    os.environ["PYTEST_RUN_PARALLEL_VERBOSE"] = orig

    result.stdout.fnmatch_lines(
        [
            "*Collected 1 items to run in parallel*",
            "*::test_should_be_marked_1 PASSED *thread-unsafe*: calls thread-unsafe function*",
            "*::test_should_not_be_marked PARALLEL PASSED*",
            "*::test_should_be_marked_2 PASSED*",
            "*::test_should_be_marked_3 PASSED*",
            "*::test_should_be_marked_1*",
            "*::test_should_be_marked_2*",
            "*::test_should_be_marked_3*",
        ]
    )


def test_detect_hypothesis(pytester):
    pytester.makepyfile("""
    from hypothesis import given, strategies as st, settings, HealthCheck

    @given(a=st.none())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_uses_hypothesis(a, num_parallel_threads):
        assert num_parallel_threads == 1
    """)
    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            "*::test_uses_hypothesis PASSED*",
        ]
    )
