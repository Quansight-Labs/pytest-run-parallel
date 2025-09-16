import os
import sys
import textwrap

import pytest

from pytest_run_parallel.thread_unsafe_detection import identify_thread_unsafe_nodes

try:
    import hypothesis
except ImportError:
    hypothesis = None


WARNINGS_IS_THREADSAFE = bool(
    getattr(sys.flags, "context_aware_warnings", 0)
    and getattr(sys.flags, "thread_inherit_context", 0)
)
WARNINGS_PASS = "PARALLEL " if WARNINGS_IS_THREADSAFE else ""
CTYPES_PASS = "PARALLEL " if sys.version_info > (3, 13) else ""


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
            "*2 tests were not run in parallel*",
        ]
    )

    # check that skipping works too
    result = pytester.runpytest(
        "--parallel-threads=10", "--skip-thread-unsafe=True", "-v"
    )

    result.stdout.fnmatch_lines(
        [
            "*::test_should_run_single SKIPPED*",
            "*::test_should_run_single_2 SKIPPED*",
            "*2 tests were skipped*",
        ]
    )

    result.stdout.no_fnmatch_line("*All tests were run in parallel*")


def test_pytest_warns_detection(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest
        import warnings
        import pytest as pyt
        import warnings as w
        import sys
        from pytest import warns, deprecated_call
        from warnings import catch_warnings

        warns_alias = warns

        WARNINGS_IS_THREADSAFE = (
            getattr(sys.flags, "context_aware_warnings", 0) and
            getattr(sys.flags, "thread_inherit_context", 0))

        def test_single_thread_warns_1(num_parallel_threads):
            with pytest.warns(UserWarning):
                warnings.warn('example', UserWarning)
            if WARNINGS_IS_THREADSAFE:
                assert num_parallel_threads == 10
            else:
                assert num_parallel_threads == 1

        def test_single_thread_warns_2(num_parallel_threads):
            with warns(UserWarning):
                warnings.warn('example', UserWarning)
            if WARNINGS_IS_THREADSAFE:
                assert num_parallel_threads == 10
            else:
                assert num_parallel_threads == 1

        def test_single_thread_warns_3(num_parallel_threads):
            with pyt.warns(UserWarning):
                warnings.warn('example', UserWarning)
            if WARNINGS_IS_THREADSAFE:
                assert num_parallel_threads == 10
            else:
                assert num_parallel_threads == 1

        def test_single_thread_warns_4(num_parallel_threads):
            with warns_alias(UserWarning):
                warnings.warn('example', UserWarning)
            if WARNINGS_IS_THREADSAFE:
                assert num_parallel_threads == 10
            else:
                assert num_parallel_threads == 1
    """)

    # run pytest with the following cmd args
    result = pytester.runpytest("--parallel-threads=10", "-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            f"*::test_single_thread_warns_1 {WARNINGS_PASS}PASSED*",
            f"*::test_single_thread_warns_2 {WARNINGS_PASS}PASSED*",
            f"*::test_single_thread_warns_3 {WARNINGS_PASS}PASSED*",
            f"*::test_single_thread_warns_4 {WARNINGS_PASS}PASSED*",
        ]
    )

    if not (
        getattr(sys.flags, "context_aware_warnings", 0)
        or getattr(sys.flags, "thread_inherit_context", 0)
    ):
        # check that skipping works too
        result = pytester.runpytest(
            "--parallel-threads=10", "--skip-thread-unsafe=True", "-v"
        )

        result.stdout.fnmatch_lines(
            [
                "*::test_single_thread_warns_1 SKIPPED*",
                "*::test_single_thread_warns_2 SKIPPED*",
                "*::test_single_thread_warns_3 SKIPPED*",
                "*::test_single_thread_warns_4 SKIPPED*",
            ]
        )


def test_warns_detection_config_option(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import pytest
        import warnings
        import pytest as pyt
        import warnings as w
        import sys
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
    result = pytester.runpytest(
        "--parallel-threads=10", "-v", "--mark-warnings-as-unsafe"
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "*::test_single_thread_warns_1 PASSED*",
            "*::test_single_thread_warns_2 PASSED*",
            "*::test_single_thread_warns_3 PASSED*",
            "*::test_single_thread_warns_4 PASSED*",
        ]
    )

    # check that skipping works too
    result = pytester.runpytest(
        "--parallel-threads=10",
        "--skip-thread-unsafe=True",
        "-v",
        "--mark-warnings-as-unsafe",
    )

    result.stdout.fnmatch_lines(
        [
            "*::test_single_thread_warns_1 SKIPPED*",
            "*::test_single_thread_warns_2 SKIPPED*",
            "*::test_single_thread_warns_3 SKIPPED*",
            "*::test_single_thread_warns_4 SKIPPED*",
        ]
    )


def test_thread_unsafe_fixtures(pytester):
    # create a temporary pytest test module
    pytester.makepyfile("""
        import sys

        import pytest

        @pytest.fixture
        def my_unsafe_fixture():
            pass

        @pytest.fixture
        def my_unsafe_fixture_2():
            pass

        WARNINGS_IS_THREADSAFE = (
            getattr(sys.flags, "context_aware_warnings", 0) and
            getattr(sys.flags, "thread_inherit_context", 0))

        def test_capsys(capsys, num_parallel_threads):
            assert num_parallel_threads == 1

        def test_monkeypatch(monkeypatch, num_parallel_threads):
            assert num_parallel_threads == 1

        def test_recwarn(recwarn, num_parallel_threads):
            if WARNINGS_IS_THREADSAFE:
                assert num_parallel_threads == 10
            else:
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
            f"*::test_recwarn {WARNINGS_PASS}PASSED*",
            "*::test_custom_fixture_skip PASSED *thread-unsafe*: uses thread-unsafe fixture*",
            "*::test_custom_fixture_skip_2 PASSED *thread-unsafe*: uses thread-unsafe fixture*",
        ]
    )


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
            "functionality, to list the tests that were not run in parallel, "
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


def test_detect_unittest_mock(pytester):
    pytester.makepyfile("""
    import sys
    from unittest import mock

    @mock.patch("sys.platform", "VAX")
    def test_uses_mock(num_parallel_threads):
        assert sys.platform == "VAX"
        assert num_parallel_threads == 1
    """)
    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            r"*::test_uses_mock PASSED*" r"calls thread-unsafe function: mock.patch*",
        ]
    )


def test_recurse_assign(pytester):
    pytester.makepyfile("""
    import pytest

    def unsafe():
        __thread_safe__ = False

    def test_function_recurse_on_assign(num_parallel_threads):
        w = unsafe()
        assert num_parallel_threads == 1
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            "*::test_function_recurse_on_assign PASSED*",
        ]
    )


def test_failed_thread_unsafe(pytester):
    pytester.makepyfile("""
    import pytest

    @pytest.mark.thread_unsafe
    def test1():
        assert False
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    assert result.ret == 1
    print(result.stdout)
    result.stdout.fnmatch_lines(
        [
            "*::test1 FAILED *thread-unsafe*: uses the thread_unsafe marker*",
            "* FAILURES *",
            "*1 failed*",
        ]
    )


def test_chained_attribute_import(pytester):
    pytester.makepyfile("""
    import _pytest.recwarn
    import sys

    WARNINGS_IS_THREADSAFE = (
        getattr(sys.flags, "context_aware_warnings", 0) and
        getattr(sys.flags, "thread_inherit_context", 0))

    def test_chained_attribute_thread_unsafe_detection(num_parallel_threads):
        _pytest.recwarn.warns()
        if WARNINGS_IS_THREADSAFE:
            assert num_parallel_threads == 10
        else:
            assert num_parallel_threads == 1
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            f"*::test_chained_attribute_thread_unsafe_detection {WARNINGS_PASS}PASSED*",
        ]
    )


def test_chained_attribute_thread_safe_assignment(pytester):
    pytester.mkpydir("mod")
    file = pytester.path / "mod" / "submod.py"
    file.write_text(
        textwrap.dedent("""
    def to_skip():
        __thread_safe__ = False
    """)
    )
    pytester.makepyfile("""
    import mod.submod

    def test_chained_attribute_thread_safe_assignment(num_parallel_threads):
        mod.submod.to_skip()
        assert num_parallel_threads == 1
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            "*::test_chained_attribute_thread_safe_assignment PASSED*",
        ]
    )


def test_wrapped_function_call(pytester):
    pytester.makepyfile("""
    def unsafe(x):
        __thread_safe__ = False
        return x

    def wrapper(x):
        return x

    def test_wrapped_function_call(num_parallel_threads):
        wrapper(unsafe(1))
        assert num_parallel_threads == 1
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            "*::test_wrapped_function_call PASSED*",
        ]
    )


def test_thread_unsafe_function_call_in_assignment(pytester):
    pytester.makepyfile("""
    def unsafe():
        __thread_safe__ = False
        return 1

    def test_thread_unsafe_function_call_in_assignment(num_parallel_threads):
        x = y = unsafe()
        assert num_parallel_threads == 1
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            "*::test_thread_unsafe_function_call_in_assignment PASSED*",
        ]
    )


def test_thread_unsafe_unittest_mock_patch_object(pytester):
    pytester.makepyfile("""
    import sys
    import unittest.mock

    @unittest.mock.patch.object(sys, "platform", "VAX")
    def test_thread_unsafe_unittest_mock_patch_object(num_parallel_threads):
        assert sys.platform == "VAX"
        assert num_parallel_threads == 1
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            "*::test_thread_unsafe_unittest_mock_patch_object PASSED*",
        ]
    )


def test_thread_unsafe_ctypes(pytester):
    pytester.makepyfile("""
    import ctypes.util
    import sys

    CTYPES_IS_THREADSAFE = sys.version_info > (3, 13)

    def test_thread_unsafe_ctypes(num_parallel_threads):
        ctypes.util.find_library("m")
        if CTYPES_IS_THREADSAFE:
            assert num_parallel_threads == 10
        else:
            assert num_parallel_threads == 1
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            f"*::test_thread_unsafe_ctypes {CTYPES_PASS}PASSED*",
        ]
    )


def test_thread_unsafe_ctypes_config_option(pytester):
    pytester.makepyfile("""
    import ctypes.util
    import sys

    def test_thread_unsafe_ctypes(num_parallel_threads):
        ctypes.util.find_library("m")
        assert num_parallel_threads == 1
    """)

    result = pytester.runpytest(
        "--parallel-threads=10", "-v", "--mark-ctypes-as-unsafe"
    )
    result.stdout.fnmatch_lines(
        [
            "*::test_thread_unsafe_ctypes PASSED*",
        ]
    )


def test_thread_unsafe_ctypes_import_from(pytester):
    pytester.makepyfile("""
    import sys
    from ctypes.util import find_library

    CTYPES_IS_THREADSAFE = sys.version_info > (3, 13)

    def test_thread_unsafe_ctypes(num_parallel_threads):
        find_library("m")
        if CTYPES_IS_THREADSAFE:
            assert num_parallel_threads == 10
        else:
            assert num_parallel_threads == 1

    def test_thread_unsafe_not_using_ctypes(num_parallel_threads):
        assert num_parallel_threads == 10
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            f"*::test_thread_unsafe_ctypes {CTYPES_PASS}PASSED*",
            "*::test_thread_unsafe_not_using_ctypes PARALLEL PASSED*",
        ]
    )


def test_thread_unsafe_ctypes_import_from_config_option(pytester):
    pytester.makepyfile("""
    import sys
    from ctypes.util import find_library

    def test_thread_unsafe_ctypes(num_parallel_threads):
        find_library("m")
        assert num_parallel_threads == 1

    def test_thread_unsafe_not_using_ctypes(num_parallel_threads):
        assert num_parallel_threads == 10
    """)

    result = pytester.runpytest(
        "--parallel-threads=10", "-v", "--mark-ctypes-as-unsafe"
    )
    result.stdout.fnmatch_lines(
        [
            "*::test_thread_unsafe_ctypes PASSED*",
            "*::test_thread_unsafe_not_using_ctypes PARALLEL PASSED*",
        ]
    )


def test_thread_unsafe_pytest_warns_multiline_string(pytester):
    pytester.makepyfile("""
import sys
import warnings

import pytest

WARNINGS_IS_THREADSAFE = (
    getattr(sys.flags, "context_aware_warnings", 0) and
    getattr(sys.flags, "thread_inherit_context", 0))

class TestThreadUnsafePytestWarnsMultilineString:
    def test_thread_unsafe_pytest_warns_multiline_string1(self, num_parallel_threads):
        with pytest.warns(UserWarning) as r:
            warnings.warn("foo", UserWarning)
        '''
Hello world'''
        if WARNINGS_IS_THREADSAFE:
            assert num_parallel_threads == 10
        else:
            assert num_parallel_threads == 1

    def test_thread_unsafe_pytest_warns_multiline_string2(self, num_parallel_threads):
        with pytest.warns(UserWarning) as r:
            warnings.warn("foo", UserWarning)
        '''
Hello world'''
        if WARNINGS_IS_THREADSAFE:
            assert num_parallel_threads == 10
        else:
            assert num_parallel_threads == 1
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            f"*::test_thread_unsafe_pytest_warns_multiline_string1 {WARNINGS_PASS}PASSED*",
            f"*::test_thread_unsafe_pytest_warns_multiline_string2 {WARNINGS_PASS}PASSED*",
        ]
    )


def test_thread_unsafe_pytest_warns_instance_decorator(pytester):
    pytester.makepyfile("""
import sys
import warnings

import pytest

WARNINGS_IS_THREADSAFE = (
    getattr(sys.flags, "context_aware_warnings", 0) and
    getattr(sys.flags, "thread_inherit_context", 0))


def identity(func):
    # Decorator that does nothing
    return func


class TestThreadUnsafePytestWarnsInstanceDecorator:
    @identity
    def test_thread_unsafe_pytest_warns_instance_decorator(self, num_parallel_threads):
        with pytest.warns(UserWarning) as r:
            warnings.warn("foo", UserWarning)
        if WARNINGS_IS_THREADSAFE:
            assert num_parallel_threads == 10
        else:
            assert num_parallel_threads == 1
    @identity
    def test_thread_unsafe_pytest_warns_instance_decorator_with_multiline(self, num_parallel_threads):
        with pytest.warns(UserWarning) as r:
            warnings.warn("foo", UserWarning)
        '''foo
'''
        if WARNINGS_IS_THREADSAFE:
            assert num_parallel_threads == 10
        else:
            assert num_parallel_threads == 1
    """)

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            f"*::test_thread_unsafe_pytest_warns_instance_decorator {WARNINGS_PASS}PASSED*",
            f"*::test_thread_unsafe_pytest_warns_instance_decorator_with_multiline {WARNINGS_PASS}PASSED*",
        ]
    )


@pytest.mark.skipif(hypothesis is None, reason="hypothesis needs to be installed")
def test_thread_unsafe_hypothesis_config_option(pytester):
    pytester.makepyfile("""
    from hypothesis import given, strategies as st, settings, HealthCheck

    @given(st.integers())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_thread_unsafe_hypothesis(num_parallel_threads, n):
        assert num_parallel_threads == 1
        assert isinstance(n, int)
    """)

    result = pytester.runpytest(
        "--parallel-threads=10", "-v", "--mark-hypothesis-as-unsafe"
    )
    result.stdout.fnmatch_lines(
        [
            "*::test_thread_unsafe_hypothesis PASSED*",
        ]
    )


def test_thread_unsafe_detection_can_handle_none_module(pytester):
    pytester.makepyfile(
        """
    global_lambda = eval("lambda x: x + 1", {})

    def test_has_l_in_globals(num_parallel_threads):
        assert num_parallel_threads == 10

    assert global_lambda.__module__ is None
    assert "global_lambda" in test_has_l_in_globals.__globals__
    """
    )

    result = pytester.runpytest("--parallel-threads=10", "-v")
    result.stdout.fnmatch_lines(
        [
            "*::test_has_l_in_globals PARALLEL PASSED*",
        ]
    )


def test_ast_parsing_error():
    def dummy_test():
        assert True

    class RaisesError:
        def __init__(self, wrapped_test):
            self.wrapped_test = wrapped_test

        def __getattr__(self, name):
            if name == "__globals__":
                raise RuntimeError("Intentionally break AST parsing")
            return self.wrapped_test.__getattribute__(name)

        def __call__(self, *args, **kwargs):
            return self.wrapped_test(*args, **kwargs)

    msg = (
        r"Uncaught exception while checking test[\s\S]*"
        "Intentionally break AST parsing"
    )

    with pytest.warns(RuntimeWarning, match=msg):
        identify_thread_unsafe_nodes(
            RaisesError(dummy_test), frozenset(), False, False, False
        )
