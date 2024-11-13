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
            "*::test_should_fail FAILED*",
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
            "*::test_should_fail FAILED*",
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
            "*::test_should_yield_global_threads PASSED*",
            "*::test_should_yield_marker_threads PASSED*",
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
        ["*::test_value_comparison PASSED*", "*::test_comparison_fail FAILED*"]
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
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_should_run_single PASSED*",
        ]
    )
