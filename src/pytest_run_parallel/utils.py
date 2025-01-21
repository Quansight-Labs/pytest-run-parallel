import ast
import inspect
import threading
import types
from textwrap import dedent

try:
    import numpy as np

    numpy_available = True
except ImportError:
    numpy_available = False


class WarningNodeVisitor(ast.NodeVisitor):
    def __init__(self, fn):
        self.catches_warns = False
        self.blacklist = {
            ("pytest", "warns"),
            ("pytest", "deprecated_call"),
            ("_pytest.recwarn", "warns"),
            ("_pytest.recwarn", "deprecated_call"),
            ("warnings", "catch_warnings"),
        }
        modules = {mod.split(".")[0] for mod, _ in self.blacklist}
        modules |= {mod for mod, _ in self.blacklist}

        self.modules_aliases = {}
        self.func_aliases = {}
        for var_name in fn.__globals__:
            value = fn.__globals__[var_name]
            if inspect.ismodule(value) and value.__name__ in modules:
                self.modules_aliases[var_name] = value.__name__
            elif inspect.isfunction(value):
                real_name = value.__name__
                for mod in modules:
                    if mod == value.__module__:
                        self.func_aliases[var_name] = (mod, real_name)
                        break

        super().__init__()

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                real_mod = node.func.value.id
                if real_mod in self.modules_aliases:
                    real_mod = self.modules_aliases[real_mod]
                if (real_mod, node.func.attr) in self.blacklist:
                    self.catches_warns = True
        elif isinstance(node.func, ast.Name):
            if node.func.id in self.func_aliases:
                if self.func_aliases[node.func.id] in self.blacklist:
                    self.catches_warns = True


def identify_warnings_handling(fn):
    try:
        src = inspect.getsource(fn)
        tree = ast.parse(dedent(src))
    except Exception:
        return False
    visitor = WarningNodeVisitor(fn)
    visitor.visit(tree)
    return visitor.catches_warns


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


def get_logical_cpus():
    try:
        import psutil
    except ImportError:
        pass
    else:
        process = psutil.Process()
        try:
            cpu_cores = process.cpu_affinity()
            if cpu_cores is not None:
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


def get_num_workers(config, item):
    n_workers = config.option.parallel_threads
    if n_workers == "auto":
        logical_cpus = get_logical_cpus()
        n_workers = logical_cpus if logical_cpus is not None else 1
    else:
        n_workers = int(n_workers)

    marker = item.get_closest_marker("parallel_threads")
    if marker is not None:
        val = marker.args[0]
        if val == "auto":
            logical_cpus = get_logical_cpus()
            n_workers = logical_cpus if logical_cpus is not None else 1
        else:
            n_workers = int(val)

    return n_workers
