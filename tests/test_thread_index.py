import pytest


def test_thread_index_single_thread(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("""
        def test_thread_index(thread_index):
            assert thread_index == 0
    """)

    result = pytester.runpytest("--parallel-threads=1", "-v")

    result.stdout.fnmatch_lines(
        [
            "*::test_thread_index PASSED*",
        ]
    )


def test_thread_index_num_parallel_threads(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("""
        def test_thread_index(thread_index, num_parallel_threads):
            assert thread_index < num_parallel_threads
    """)

    result = pytester.runpytest("--parallel-threads=auto", "-v")

    result.stdout.fnmatch_lines(
        [
            "*::test_thread_index PARALLEL PASSED*",
        ]
    )


def test_thread_index_changes_between_tests(pytester: pytest.Pytester) -> None:
    # thread_comp is checking if the thread_indexes are equal between threads.
    # should fail since thread_indexes should not match.
    # test can be improved, since this cannot check if every thread has a
    # different thread_index
    pytester.makepyfile("""
        def test_thread_index(thread_index, thread_comp):
            thread_comp(thread_index=thread_index)
    """)

    result = pytester.runpytest("--parallel-threads=auto", "-v")

    result.stdout.fnmatch_lines(
        [
            "*::test_thread_index PARALLEL FAILED*",
        ]
    )


def test_iteration_index_single_iteration(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("""
        def test_iteration_index(iteration_index):
            assert iteration_index == 0
    """)

    result = pytester.runpytest("--parallel-threads=auto", "--iterations=1", "-v")

    result.stdout.fnmatch_lines(
        [
            "*::test_iteration_index PARALLEL PASSED*",
        ]
    )


def test_iteration_index_multi_iteration(pytester: pytest.Pytester) -> None:
    pytester.makepyfile("""
        def test_iteration_index(iteration_index, num_iterations):
            assert iteration_index < num_iterations
    """)

    result = pytester.runpytest("--parallel-threads=1", "--iterations=3", "-v")

    result.stdout.fnmatch_lines(
        [
            "*::test_iteration_index PASSED*",
        ]
    )


def test_iteration_index_multi_iteration_mutli_thread(
    pytester: pytest.Pytester,
) -> None:
    pytester.makepyfile("""
        def test_iteration_index(iteration_index, num_iterations):
            assert iteration_index < num_iterations
    """)

    result = pytester.runpytest("--parallel-threads=auto", "--iterations=3", "-v")

    result.stdout.fnmatch_lines(
        [
            "*::test_iteration_index PARALLEL PASSED*",
        ]
    )
