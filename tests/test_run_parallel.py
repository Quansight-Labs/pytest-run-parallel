
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
    result = pytester.runpytest(
        '--parallel-threads=10',
        '-v'
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_check_thread_count PASSED*',
    ])

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
        def test_check_thread_count(counter2):
            assert counter2._count == 5
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest(
        '--parallel-threads=10',
        '-v'
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_check_thread_count PASSED*',
    ])

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_help_message(pytester):
    result = pytester.runpytest(
        '--help',
    )
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'run-parallel:',
        '  --parallel-threads=PARALLEL_THREADS'
        # '             Set the number of threads used to execute each test concurrently.',
    ])

