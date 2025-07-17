from pytest_run_parallel.cpu_detection import get_logical_cpus


def get_configured_num_workers(config):
    n_workers = config.option.parallel_threads
    if n_workers == "auto":
        logical_cpus = get_logical_cpus()
        n_workers = logical_cpus if logical_cpus is not None else 1
    else:
        n_workers = int(n_workers)
    return n_workers


def get_num_workers(item):
    n_workers = get_configured_num_workers(item.config)
    marker = item.get_closest_marker("parallel_threads")
    if marker is not None:
        val = marker.args[0]
        if val == "auto":
            logical_cpus = get_logical_cpus()
            n_workers = logical_cpus if logical_cpus is not None else 1
        else:
            n_workers = int(val)

    return n_workers, marker is not None


def get_num_iterations(item):
    n_iterations = item.config.option.iterations
    marker = item.get_closest_marker("iterations")
    if marker is not None:
        n_iterations = int(marker.args[0])
    return n_iterations, marker is not None
