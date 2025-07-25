import functools
import os
import re
import sys
import threading
import warnings

import _pytest.doctest
import _pytest.outcomes
import pytest

from pytest_run_parallel.thread_comparator import ThreadComparator
from pytest_run_parallel.thread_unsafe_detection import (
    construct_thread_unsafe_fixtures,
    identify_thread_unsafe_nodes,
)
from pytest_run_parallel.utils import (
    get_configured_num_workers,
    get_num_iterations,
    get_num_workers,
)

GIL_WARNING_MESSAGE_CONTENT = re.compile(
    r"The global interpreter lock \(GIL\) has been enabled to load module '(?P<module>[^']*)'"
)

GIL_ENABLED_ERROR_TEXT = (
    "GIL was dynamically re-enabled during test {stage_test} to load module '{module}'. "
    "When running under a free-threaded interpreter with the GIL initially disabled, "
    "the test suite must not cause the GIL to be re-enabled at runtime. Check "
    "for compiled extension modules that do not use the 'Py_mod_gil' slot or the "
    "'PyUnstable_Module_SetGIL' API."
)


def wrap_function_parallel(fn, n_workers, n_iterations):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        errors = []
        skip = None
        failed = None
        barrier = threading.Barrier(n_workers)
        original_switch = sys.getswitchinterval()
        new_switch = 1e-6
        for _ in range(3):
            try:
                sys.setswitchinterval(new_switch)
                break
            except ValueError:
                new_switch *= 10
        else:
            sys.setswitchinterval(original_switch)

        try:

            def closure(*args, **kwargs):
                for _ in range(n_iterations):
                    barrier.wait()
                    try:
                        fn(*args, **kwargs)
                    except Warning:
                        pass
                    except Exception as e:
                        errors.append(e)
                    except _pytest.outcomes.Skipped as s:
                        nonlocal skip
                        skip = s.msg
                    except _pytest.outcomes.Failed as f:
                        nonlocal failed
                        failed = f

            workers = []
            for _ in range(0, n_workers):
                worker_kwargs = kwargs
                workers.append(
                    threading.Thread(target=closure, args=args, kwargs=worker_kwargs)
                )

            num_completed = 0
            try:
                for worker in workers:
                    worker.start()
                    num_completed += 1
            finally:
                if num_completed < len(workers):
                    barrier.abort()

            for worker in workers:
                worker.join()

        finally:
            sys.setswitchinterval(original_switch)

        if skip is not None:
            pytest.skip(skip)
        elif failed is not None:
            raise failed
        elif errors:
            raise errors[0]

    return inner


class RunParallelPlugin:
    def __init__(self, config):
        self.verbose = bool(int(os.environ.get("PYTEST_RUN_PARALLEL_VERBOSE", "0")))
        self.skip_thread_unsafe = config.option.skip_thread_unsafe
        self.mark_warnings_as_unsafe = config.option.mark_warnings_as_unsafe
        self.mark_ctypes_as_unsafe = config.option.mark_ctypes_as_unsafe
        self.mark_hypothesis_as_unsafe = config.option.mark_hypothesis_as_unsafe
        self.ignore_gil_enabled = config.option.ignore_gil_enabled

        skipped_functions = [
            x.split(".") for x in config.getini("thread_unsafe_functions")
        ]
        self.skipped_functions = frozenset(
            (".".join(x[:-1]), x[-1]) for x in skipped_functions
        )

        self.unsafe_fixtures = construct_thread_unsafe_fixtures(config)
        self.thread_unsafe = {}
        self.run_in_parallel = {}

    def skipped_or_not_parallel(self, *, plural):
        if plural:
            skipped = "were skipped"
            parallel = "were not run in parallel"
        else:
            skipped = "was skipped"
            parallel = "was not run in parallel"
        return skipped if self.skip_thread_unsafe else parallel

    def _mark_test_thread_unsafe(self, item, reason):
        if self.skip_thread_unsafe:
            item.add_marker(pytest.mark.skip(reason=reason))
        else:
            item.add_marker(pytest.mark.parallel_threads(1))
        self.thread_unsafe[item.nodeid] = reason

    def _is_thread_unsafe(self, item):
        m = item.get_closest_marker("thread_unsafe")
        if m is not None:
            reason = m.kwargs.get("reason", None)
            if reason is None:
                reason = "uses the thread_unsafe marker"
            return True, reason

        fixtures = getattr(item, "fixturenames", ())
        if any(fixture in fixtures for fixture in self.unsafe_fixtures):
            used_unsafe_fixtures = self.unsafe_fixtures & set(fixtures)
            return True, f"uses thread-unsafe fixture(s): {used_unsafe_fixtures}"

        return identify_thread_unsafe_nodes(
            item.obj,
            self.skipped_functions,
            self.mark_warnings_as_unsafe,
            self.mark_ctypes_as_unsafe,
            self.mark_hypothesis_as_unsafe,
        )

    @pytest.hookimpl(trylast=True)
    def pytest_itemcollected(self, item):
        if not hasattr(item, "obj"):
            if not hasattr(item, "_parallel_custom_item"):
                warnings.warn(
                    f"Encountered pytest item with type {type(item)} with no 'obj' "
                    "attribute, which is incompatible with pytest-run-parallel. "
                    f"Tests using {type(item)} will not run in a thread pool.\n"
                    "The pytest-run-parallel plugin only supports custom collection "
                    "tree objects that wrap Python functions stored in an attribute "
                    "named 'obj'.\n"
                    "Define a '_parallel_custom_item' attribute on the pytest item"
                    "instance or class to silence this warning.\n"
                    "If you do not want to use pytest-run-parallel, uninstall it from "
                    "your environment."
                )
            self._mark_test_thread_unsafe(
                item, "is incompatible with pytest-run-parallel"
            )
            return

        if isinstance(item, _pytest.doctest.DoctestItem):
            self._mark_test_thread_unsafe(
                item, "is a doctest (pytest-run-parallel does not support doctests)"
            )
            return

        n_workers, parallel_threads_marker_used = get_num_workers(item)
        if n_workers < 0:
            raise ValueError("parallel-threads cannot be negative")

        n_iterations, _ = get_num_iterations(item)
        if n_iterations < 0:
            raise ValueError("parallel-threads cannot be negative")

        if n_workers == 1 and parallel_threads_marker_used:
            self._mark_test_thread_unsafe(item, "uses the parallel_threads(1) marker")

        if n_workers > 1:
            thread_unsafe, reason = self._is_thread_unsafe(item)
            if thread_unsafe:
                n_workers = 1
                self._mark_test_thread_unsafe(item, reason)
            else:
                self.run_in_parallel[item.nodeid] = n_workers

        if n_workers > 1 or n_iterations > 1:
            original_globals = item.obj.__globals__
            item.obj = wrap_function_parallel(item.obj, n_workers, n_iterations)
            for name in original_globals:
                if name not in item.obj.__globals__:
                    item.obj.__globals__[name] = original_globals[name]

    @pytest.hookimpl(trylast=True)
    def pytest_report_collectionfinish(self, config, start_path, items):
        return f"Collected {len(self.run_in_parallel)} items to run in parallel"

    @pytest.hookimpl(tryfirst=True, wrapper=True)
    def pytest_report_teststatus(self, report, config):
        outcome = yield
        if getattr(report, "when", None) != "call":
            return outcome

        if report.nodeid in self.run_in_parallel:
            if report.outcome == "passed":
                return "passed", "·", "PARALLEL PASSED"
            if report.outcome == "failed":
                return "error", "e", "PARALLEL FAILED"
        else:
            reason = self.thread_unsafe.get(report.nodeid)
            if reason is not None:
                if report.outcome == "passed":
                    return (
                        "passed",
                        ".",
                        f"PASSED [thread-unsafe]: {reason}",
                    )
                if report.outcome == "failed":
                    return (
                        "failed",
                        "x",
                        f"FAILED ([thread-unsafe]: {reason})",
                    )
        return outcome

    def _write_reasons_summary(self, terminalreporter):
        for nodeid, reason in self.thread_unsafe.items():
            if reason is not None:
                terminalreporter.line(
                    f"{nodeid} {self.skipped_or_not_parallel(plural=False)} because it {reason}"
                )
            else:
                terminalreporter.line(nodeid)

    @pytest.hookimpl(trylast=True)
    def pytest_terminal_summary(self, terminalreporter, exitstatus, config):
        enabled = get_configured_num_workers(config) > 1
        if not enabled:
            return

        terminalreporter.section("pytest-run-parallel report", "*")

        if self.verbose and self.thread_unsafe:
            self._write_reasons_summary(terminalreporter)
        elif self.thread_unsafe:
            num = len(self.thread_unsafe)
            if num > 1:
                test = "tests"
            else:
                test = "test"
            terminalreporter.line(
                f"{num} {test} {self.skipped_or_not_parallel(plural=num > 1)}"
                " because of use of thread-unsafe functionality, "
                f"to list the tests that {self.skipped_or_not_parallel(plural=True)}, re-run "
                "while setting PYTEST_RUN_PARALLEL_VERBOSE=1 "
                "in your shell environment"
            )
        else:
            terminalreporter.line("All tests were run in parallel! 🎉")

    @pytest.hookimpl(tryfirst=True)
    def pytest_warning_recorded(
        self, warning_message: warnings.WarningMessage, when, nodeid, location
    ):
        mo = re.match(GIL_WARNING_MESSAGE_CONTENT, str(warning_message.message))
        if mo is None or self.ignore_gil_enabled:
            return

        if when == "collect":
            stage = "collection"
        elif when == "runtest":
            stage = "execution"
        else:
            stage = "configuration"
        stage_test = stage
        if nodeid:
            stage_test += f" of '{nodeid}'"
        pytest.exit(
            reason=GIL_ENABLED_ERROR_TEXT.format(
                stage_test=stage_test, module=mo.group("module")
            ),
            returncode=1,
        )


@pytest.fixture
def num_parallel_threads(request):
    return get_num_workers(request.node)[0]


@pytest.fixture
def num_iterations(request):
    return get_num_iterations(request.node)[0]


@pytest.fixture
def thread_comp(num_parallel_threads):
    return ThreadComparator(num_parallel_threads)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "parallel_threads(n): run the given test function in parallel "
        "using `n` threads.",
    )
    config.addinivalue_line(
        "markers",
        "iterations(n): run the given test function `n` times in each thread",
    )
    config.addinivalue_line(
        "markers",
        "thread_unsafe: mark the test function as single-threaded",
    )
    config.pluginmanager.register(RunParallelPlugin(config), "_run-parallel")


def pytest_addoption(parser):
    group = parser.getgroup("run-parallel")
    group.addoption(
        "--parallel-threads",
        action="store",
        dest="parallel_threads",
        default=1,
        help="Set the number of threads used to execute each test concurrently.",
    )
    group.addoption(
        "--iterations",
        action="store",
        dest="iterations",
        default=1,
        type=int,
        help="Set the number of threads used to execute each test concurrently.",
    )
    parser.addoption(
        "--skip-thread-unsafe",
        action="store",
        dest="skip_thread_unsafe",
        help="Whether to skip running thread-unsafe tests",
        type=bool,
        default=False,
    )
    parser.addoption(
        "--mark-warnings-as-unsafe",
        action="store_true",
        dest="mark_warnings_as_unsafe",
        default=False,
    )
    parser.addoption(
        "--mark-ctypes-as-unsafe",
        action="store_true",
        dest="mark_ctypes_as_unsafe",
        default=False,
    )
    parser.addoption(
        "--mark-hypothesis-as-unsafe",
        action="store_true",
        dest="mark_hypothesis_as_unsafe",
        default=False,
    )
    parser.addoption(
        "--ignore-gil-enabled",
        action="store_true",
        dest="ignore_gil_enabled",
        default=False,
    )
    parser.addini(
        "thread_unsafe_fixtures",
        "list of thread-unsafe fixture names that cause a test to "
        "be run sequentially",
        type="linelist",
        default=[],
    )
    parser.addini(
        "thread_unsafe_functions",
        "list of thread-unsafe fully-qualified named functions that cause "
        "a test to run on one thread",
        type="linelist",
        default=[],
    )
