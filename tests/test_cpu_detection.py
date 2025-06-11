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

    monkeypatch.delattr(psutil.Process, "cpu_affinity", raising=False)
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

        monkeypatch.delattr(psutil.Process, "cpu_affinity", raising=False)
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

        monkeypatch.delattr(psutil.Process, "cpu_affinity", raising=False)
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

        monkeypatch.delattr(psutil.Process, "cpu_affinity", raising=False)
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
