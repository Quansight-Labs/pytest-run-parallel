import pytest
from _helpers import passing_status


def test_wrap_fixtures_hook_can_transform_fixture(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(
        """
        import pytest

        @pytest.hookimpl
        def pytest_run_parallel_get_wrap_fixtures(n_workers):
            def transform_marker(value, *, thread_index):
                return f"{thread_index}:{value}"

            return {"marker": transform_marker}
        """
    )
    pytester.makepyfile(
        """
        import pytest

        @pytest.fixture
        def marker():
            return "base"

        def test_marker(marker, thread_comp):
            assert marker.startswith(("0:", "1:"))
            thread_index, value = marker.split(":", 1)
            assert value == "base"
            thread_comp(value=value)
            assert int(thread_index) >= 0
        """
    )
    result = pytester.runpytest("--parallel-threads=2", "-v")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines([f"*::test_marker {passing_status(2)}*"])


def test_wrap_fixtures_hook_none_is_skipped(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(
        """
        import pytest

        @pytest.hookimpl
        def pytest_run_parallel_get_wrap_fixtures(n_workers):
            return None
        """
    )
    pytester.makepyfile(
        """
        def test_thread_index(thread_index, num_parallel_threads):
            assert thread_index < num_parallel_threads
        """
    )
    result = pytester.runpytest("--parallel-threads=2", "-v")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines([f"*::test_thread_index {passing_status(2)}*"])


def test_wrap_fixtures_hook_chains_duplicate_fixture_transforms(
    pytester: pytest.Pytester,
) -> None:
    pytester.makeconftest(
        """
        import pytest

        class FirstPlugin:
            @pytest.hookimpl(tryfirst=True)
            def pytest_run_parallel_get_wrap_fixtures(self, n_workers):
                def first(value, *, thread_index):
                    return value + ["first"]

                return {"steps": first}

        class SecondPlugin:
            @pytest.hookimpl(trylast=True)
            def pytest_run_parallel_get_wrap_fixtures(self, n_workers):
                def second(value, *, thread_index):
                    return value + ["second"]

                return {"steps": second}

        def pytest_configure(config):
            config.pluginmanager.register(FirstPlugin(), "first-prepare")
            config.pluginmanager.register(SecondPlugin(), "second-prepare")
        """
    )
    pytester.makepyfile(
        """
        import pytest

        @pytest.fixture
        def steps():
            return []

        def test_steps(steps):
            # Later hookimpls are inserted first (most-specific runs first).
            assert steps == ["second", "first"]
        """
    )
    result = pytester.runpytest("--parallel-threads=2", "-v")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines([f"*::test_steps {passing_status(2)}*"])


def test_wrap_fixtures_hook_generator_teardown_reverse_order(
    pytester: pytest.Pytester,
) -> None:
    pytester.makeconftest(
        """
        import pytest

        log = []

        class OuterPlugin:
            @pytest.hookimpl(tryfirst=True)
            def pytest_run_parallel_get_wrap_fixtures(self, n_workers):
                def outer(value, *, thread_index):
                    log.append(f"setup-outer-{thread_index}")
                    yield value
                    log.append(f"teardown-outer-{thread_index}")

                return {"marker": outer}

        class InnerPlugin:
            @pytest.hookimpl(trylast=True)
            def pytest_run_parallel_get_wrap_fixtures(self, n_workers):
                def inner(value, *, thread_index):
                    log.append(f"setup-inner-{thread_index}")
                    yield f"{value}:{thread_index}"
                    log.append(f"teardown-inner-{thread_index}")

                return {"marker": inner}

        def pytest_configure(config):
            config.pluginmanager.register(OuterPlugin(), "outer-prepare")
            config.pluginmanager.register(InnerPlugin(), "inner-prepare")
        """
    )
    pytester.makepyfile(
        """
        import pytest

        @pytest.fixture
        def marker():
            return "base"

        def test_marker(marker, thread_index):
            assert marker == f"base:{thread_index}"

        def test_teardown_order():
            from conftest import log

            # Later hookimpls run first; teardowns still reverse of setup.
            for thread_index in (0, 1):
                setup_inner = log.index(f"setup-inner-{thread_index}")
                setup_outer = log.index(f"setup-outer-{thread_index}")
                teardown_outer = log.index(f"teardown-outer-{thread_index}")
                teardown_inner = log.index(f"teardown-inner-{thread_index}")
                assert setup_inner < setup_outer < teardown_outer < teardown_inner
        """
    )
    result = pytester.runpytest("--parallel-threads=2", "-v")
    result.assert_outcomes(passed=2)
    result.stdout.fnmatch_lines(
        [
            f"*::test_marker {passing_status(2)}*",
            f"*::test_teardown_order {passing_status(2)}*",
        ]
    )


def test_wrap_fixtures_only_applies_to_direct_test_fixtures(
    pytester: pytest.Pytester,
) -> None:
    """Transforms for fixtures not requested by the test must not run."""
    pytester.makeconftest(
        """
        import pytest

        calls = []

        @pytest.hookimpl
        def pytest_run_parallel_get_wrap_fixtures(n_workers):
            def transform_unused(value, *, thread_index):
                calls.append("unused")
                return value

            return {"unused": transform_unused}
        """
    )
    pytester.makepyfile(
        """
        import pytest

        @pytest.fixture
        def unused():
            return "x"

        def test_no_unused(thread_index):
            from conftest import calls

            assert calls == []
            assert thread_index >= 0
        """
    )
    result = pytester.runpytest("--parallel-threads=2", "-v")
    result.assert_outcomes(passed=1)


def test_wrap_fixtures_skipped_when_configured_workers_is_one(
    pytester: pytest.Pytester,
) -> None:
    """Built-in returns None when configured n_workers <= 1."""
    pytester.makepyfile(
        """
        def test_thread_index(thread_index):
            assert thread_index == 0
        """
    )
    result = pytester.runpytest("--parallel-threads=1", "--iterations=2", "-v")
    result.assert_outcomes(passed=1)
