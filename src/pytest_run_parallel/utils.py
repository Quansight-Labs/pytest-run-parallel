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

try:
    # added in hypothesis 6.131.0
    from hypothesis import is_hypothesis_test
except ImportError:
    try:
        # hypothesis versions < 6.131.0
        from hypothesis.internal.detection import is_hypothesis_test
    except ImportError:
        # hypothesis isn't installed
        def is_hypothesis_test(fn):
            return False


class ThreadUnsafeNodeVisitor(ast.NodeVisitor):
    def __init__(self, fn, skip_set, level=0):
        self.thread_unsafe = False
        self.thread_unsafe_reason = None
        self.blacklist = {
            ("pytest", "warns"),
            ("pytest", "deprecated_call"),
            ("_pytest.recwarn", "warns"),
            ("_pytest.recwarn", "deprecated_call"),
            ("warnings", "catch_warnings"),
        } | set(skip_set)
        modules = {mod.split(".")[0] for mod, _ in self.blacklist}
        modules |= {mod for mod, _ in self.blacklist}

        self.fn = fn
        self.skip_set = skip_set
        self.level = level
        self.modules_aliases = {}
        self.func_aliases = {}
        for var_name in getattr(fn, "__globals__", {}):
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
        if self.thread_unsafe:
            return

        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                real_mod = node.func.value.id
                if real_mod in self.modules_aliases:
                    real_mod = self.modules_aliases[real_mod]
                if (real_mod, node.func.attr) in self.blacklist:
                    self.thread_unsafe = True
                    self.thread_unsafe_reason = (
                        f"calls thread-unsafe function: {node.func.attr}"
                    )
                elif self.level < 2:
                    if node.func.value.id in getattr(self.fn, "__globals__", {}):
                        mod = self.fn.__globals__[node.func.value.id]
                        child_fn = getattr(mod, node.func.attr, None)
                        if child_fn is not None:
                            self.thread_unsafe, self.thread_unsafe_reason = (
                                identify_thread_unsafe_nodes(
                                    child_fn, self.skip_set, self.level + 1
                                )
                            )
        elif isinstance(node.func, ast.Name):
            recurse = True
            if node.func.id in self.func_aliases:
                if self.func_aliases[node.func.id] in self.blacklist:
                    self.thread_unsafe = True
                    self.thread_unsafe_reason = (
                        f"calls thread-unsafe function: {node.func.id}"
                    )
                    recurse = False
            if recurse and self.level < 2:
                if node.func.id in getattr(self.fn, "__globals__", {}):
                    child_fn = self.fn.__globals__[node.func.id]
                    self.thread_unsafe, self.thread_unsafe_reason = (
                        identify_thread_unsafe_nodes(
                            child_fn, self.skip_set, self.level + 1
                        )
                    )

    def visit_Assign(self, node):
        if self.thread_unsafe:
            return

        if len(node.targets) == 1:
            name_node = node.targets[0]
            value_node = node.value
            if getattr(name_node, "id", None) == "__thread_safe__":
                self.thread_unsafe = not bool(value_node.value)
                self.thread_unsafe_reason = (
                    f"calls thread-unsafe function: f{name_node} "
                    "(inferred via func.__thread_safe__ == False)"
                )


def identify_thread_unsafe_nodes(fn, skip_set, level=0):
    if is_hypothesis_test(fn):
        return True, "uses hypothesis"
    try:
        src = inspect.getsource(fn)
        tree = ast.parse(dedent(src))
    except Exception:
        return False, None
    visitor = ThreadUnsafeNodeVisitor(fn, skip_set, level=level)
    visitor.visit(tree)
    return visitor.thread_unsafe, visitor.thread_unsafe_reason


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


def get_configured_num_workers(config):
    n_workers = config.option.parallel_threads
    if n_workers == "auto":
        logical_cpus = get_logical_cpus()
        n_workers = logical_cpus if logical_cpus is not None else 1
    else:
        n_workers = int(n_workers)
    return n_workers


def get_num_workers(config, item):
    n_workers = get_configured_num_workers(config)
    marker = item.get_closest_marker("parallel_threads")
    if marker is not None:
        val = marker.args[0]
        if val == "auto":
            logical_cpus = get_logical_cpus()
            n_workers = logical_cpus if logical_cpus is not None else 1
        else:
            n_workers = int(val)

    return n_workers
