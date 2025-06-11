import functools
import sys
import threading

import _pytest.outcomes
import pytest


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
