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
