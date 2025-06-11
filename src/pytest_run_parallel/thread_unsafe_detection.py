import ast
import functools
import inspect
from textwrap import dedent

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


THREAD_UNSAFE_FIXTURES = {
    "capsys",
    "monkeypatch",
    "recwarn",
}


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
            ("mock", "patch"),  # unittest.mock
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
                        "calls thread-unsafe function: " f"{real_mod}.{node.func.attr}"
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
            else:
                self.generic_visit(node)


def _identify_thread_unsafe_nodes(fn, skip_set, level=0):
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


cached_thread_unsafe_identify = functools.lru_cache(_identify_thread_unsafe_nodes)


def identify_thread_unsafe_nodes(fn, skip_set, level=0):
    try:
        return cached_thread_unsafe_identify(fn, skip_set, level=level)
    except TypeError:
        return _identify_thread_unsafe_nodes(fn, skip_set, level=level)
