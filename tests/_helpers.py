from pytest_run_parallel.cpu_detection import get_logical_cpus


def passing_status(threads):
    # Pytest reports "PARALLEL PASSED" only when the resolved worker count is
    # greater than 1. On single-CPU systems --parallel-threads=auto resolves
    # to 1, so the status degrades to "PASSED" (issue #177).
    if threads == "auto":
        n = get_logical_cpus() or 1
    else:
        n = int(threads)
    return "PARALLEL PASSED" if n > 1 else "PASSED"
