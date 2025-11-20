import warnings

from pytest_run_parallel.cpu_detection import get_logical_cpus


def get_configured_num_workers(config):
    n_workers = config.option.parallel_threads
    if n_workers == "auto":
        logical_cpus = get_logical_cpus()
        n_workers = logical_cpus if logical_cpus is not None else 1
    else:
        n_workers = int(n_workers)
    return n_workers


def auto_or_int(val):
    if val == "auto":
        logical_cpus = get_logical_cpus()
        return logical_cpus if logical_cpus is not None else 1
    return int(val)


def get_num_workers(item):
    n_workers = get_configured_num_workers(item.config)
    # TODO: deprecate in favor of parallel_threads_limit
    marker_used = False
    marker = item.get_closest_marker("parallel_threads")
    if marker is not None:
        marker_used = True
        n_workers = auto_or_int(marker.args[0])
        if n_workers > 1:
            warnings.warn(
                "Using the parallel_threads marker with a value greater than 1 is deprecated. Use parallel_threads_limit instead.",
                DeprecationWarning,
                stacklevel=2,
            )
    limit_marker = item.get_closest_marker("parallel_threads_limit")
    if limit_marker is not None:
        val = auto_or_int(limit_marker.args[0])
        if val == 1:
            marker_used = True
        if n_workers > val:
            n_workers = val

    return n_workers, marker_used


def get_num_iterations(item):
    n_iterations = item.config.option.iterations
    marker = item.get_closest_marker("iterations")
    if marker is not None:
        n_iterations = int(marker.args[0])
    return n_iterations, marker is not None
