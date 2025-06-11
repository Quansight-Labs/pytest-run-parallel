def get_logical_cpus():
    try:
        import psutil
    except ImportError:
        pass
    else:
        process = psutil.Process()
        try:
            cpu_cores = process.cpu_affinity()
            return len(cpu_cores)
        except AttributeError:
            cpu_cores = psutil.cpu_count()
            if cpu_cores is not None:
                return cpu_cores

    try:
        from os import process_cpu_count
    except ImportError:
        pass
    else:
        cpu_cores = process_cpu_count()
        if cpu_cores is not None:
            return cpu_cores

    try:
        from os import sched_getaffinity
    except ImportError:
        pass
    else:
        cpu_cores = sched_getaffinity(0)
        if cpu_cores is not None:
            return len(cpu_cores)

    from os import cpu_count

    return cpu_count()
