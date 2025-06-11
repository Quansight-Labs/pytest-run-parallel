import threading
import types

try:
    import numpy as np

    numpy_available = True
except ImportError:
    numpy_available = False


class ThreadComparator:
    def __init__(self, n_threads):
        self._barrier = threading.Barrier(n_threads)
        self._reset_evt = threading.Event()
        self._entry_barrier = threading.Barrier(n_threads)

        self._thread_ids = []
        self._values = {}
        self._entry_lock = threading.Lock()
        self._entry_counter = 0

    def __call__(self, **values):
        """
        Compares a set of values across threads.

        For each value, type equality as well as comparison takes place. If any
        of the values is a function, then address comparison is performed.
        Also, if any of the values is a `numpy.ndarray`, then approximate
        numerical comparison is performed.
        """
        tid = id(threading.current_thread())
        self._entry_barrier.wait()
        with self._entry_lock:
            if self._entry_counter == 0:
                # Reset state before comparison
                self._barrier.reset()
                self._reset_evt.clear()
                self._thread_ids = []
                self._values = {}
                self._entry_barrier.reset()
            self._entry_counter += 1

        self._values[tid] = values
        self._thread_ids.append(tid)
        self._barrier.wait()

        if tid == self._thread_ids[0]:
            thread_ids = list(self._values)
            try:
                for value_name in values:
                    for i in range(1, len(thread_ids)):
                        tid_a = thread_ids[i - 1]
                        tid_b = thread_ids[i]
                        value_a = self._values[tid_a][value_name]
                        value_b = self._values[tid_b][value_name]
                        assert type(value_a) is type(value_b)
                        if numpy_available and isinstance(value_a, np.ndarray):
                            if len(value_a.shape) == 0:
                                assert value_a == value_b
                            else:
                                assert np.allclose(value_a, value_b, equal_nan=True)
                        elif isinstance(value_a, types.FunctionType):
                            assert id(value_a) == id(value_b)
                        elif value_a != value_a:
                            assert value_b != value_b
                        else:
                            assert value_a == value_b
            finally:
                self._entry_counter = 0
                self._reset_evt.set()
        else:
            self._reset_evt.wait()
