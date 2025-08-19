import pytest


def test_thread_id_single_thread(pytester: pytest.Pytester) -> None:
    # create a temporary pytest test module
    pytester.makepyfile("""
        def test_thread_id(thread_id):
            assert thread_id == 0
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=1", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_thread_id PASSED*",
        ]
    )


def test_thread_id_num_parallel_threads(pytester: pytest.Pytester) -> None:
    # create a temporary pytest test module
    pytester.makepyfile("""
        def test_thread_id(thread_id, num_parallel_threads):
            assert thread_id < num_parallel_threads
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=auto", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_thread_id PARALLEL PASSED*",
        ]
    )


def test_thread_id_changes_between_tests(pytester: pytest.Pytester) -> None:
    # create a temporary pytest test module
    pytester.makepyfile("""
        def test_thread_id(thread_id, thread_comp):
            thread_comp(thread_id=thread_id)
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=auto", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_thread_id PARALLEL FAILED*",
        ]
    )


def test_iteration_id_single_iteration(pytester: pytest.Pytester) -> None:
    # create a temporary pytest test module
    pytester.makepyfile("""
        def test_thread_id(iteration_id):
            assert iteration_id == 0
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=auto", "--iterations=1", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_thread_id PARALLEL PASSED*",
        ]
    )


def test_iteration_id_multi_iteration(pytester: pytest.Pytester) -> None:
    # create a temporary pytest test module
    pytester.makepyfile("""
        def test_thread_id(iteration_id, num_iterations):
            assert iteration_id < num_iterations
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=1", "--iterations=3", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_thread_id PASSED*",
        ]
    )


def test_iteration_id_multi_iteration_mutli_thread(pytester: pytest.Pytester) -> None:
    # create a temporary pytest test module
    pytester.makepyfile("""
        def test_thread_id(iteration_id, num_iterations):
            assert iteration_id < num_iterations
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=auto", "--iterations=3", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_thread_id PARALLEL PASSED*",
        ]
    )
