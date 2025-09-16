import ast
import functools
import inspect
import sys
import traceback
import warnings

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


try:
    from hypothesis import __version_info__ as hypothesis_version
except ImportError:
    hypothesis_version = (0, 0, 0)

HYPOTHESIS_THREADSAFE_VERSION = (6, 136, 3)

WARNINGS_IS_THREADSAFE = bool(
    getattr(sys.flags, "context_aware_warnings", 0)
    and getattr(sys.flags, "thread_inherit_context", 0)
)

CTYPES_IS_THREADSAFE = sys.version_info > (3, 13)


def construct_base_blocklist(unsafe_warnings, unsafe_ctypes):
    safe_warnings = not unsafe_warnings and WARNINGS_IS_THREADSAFE
    safe_ctypes = not unsafe_ctypes and CTYPES_IS_THREADSAFE
    return {
        ("pytest", "warns", safe_warnings),
        ("pytest", "deprecated_call", safe_warnings),
        ("_pytest.recwarn", "warns", safe_warnings),
        ("_pytest.recwarn", "deprecated_call", safe_warnings),
        ("warnings", "catch_warnings", safe_warnings),
        ("unittest.mock", "*", False),
        ("mock", "*", False),
        ("ctypes", "*", safe_ctypes),
    }


THREAD_UNSAFE_FIXTURES = {
    "capsys": False,
    "monkeypatch": False,
    "recwarn": WARNINGS_IS_THREADSAFE,
}


class ThreadUnsafeNodeVisitor(ast.NodeVisitor):
    def __init__(
        self, fn, skip_set, unsafe_warnings, unsafe_ctypes, unsafe_hypothesis, level=0
    ):
        self.thread_unsafe = False
        self.thread_unsafe_reason = None
        blocklist = construct_base_blocklist(unsafe_warnings, unsafe_ctypes)
        self.blocklist = {b[:2] for b in blocklist if not b[-1]} | skip_set
        self.module_blocklist = {mod for mod, func in self.blocklist if func == "*"}
        self.function_blocklist = {
            (mod, func) for mod, func in self.blocklist if func != "*"
        }

        modules = {mod.split(".")[0] for mod, _ in self.blocklist}
        modules |= {mod for mod, _ in self.blocklist}

        self.fn = fn
        self.skip_set = skip_set
        self.unsafe_warnings = unsafe_warnings
        self.unsafe_ctypes = unsafe_ctypes
        self.unsafe_hypothesis = unsafe_hypothesis
        self.level = level
        self.modules_aliases = {}
        self.func_aliases = {}
        self.globals = getattr(fn, "__globals__", {})

        # see issue #121, sometimes __globals__ isn't iterable
        try:
            iter(self.globals)
        except TypeError:
            self.globals = {}

        for var_name in iter(self.globals):
            value = fn.__globals__[var_name]
            if inspect.ismodule(value) and value.__name__ in modules:
                self.modules_aliases[var_name] = value.__name__
            elif inspect.isfunction(value):
                if value.__module__ is None:
                    continue
                if value.__module__ in modules:
                    self.func_aliases[var_name] = (value.__module__, value.__name__)
                    continue

                all_parents = self._create_all_parent_modules(value.__module__)
                for parent in all_parents:
                    if parent in modules:
                        self.func_aliases[var_name] = (parent, value.__name__)
                        break

        super().__init__()

    def _create_all_parent_modules(self, module_name):
        all_parent_modules = set()
        parent, dot, _ = module_name.rpartition(".")
        while dot:
            all_parent_modules.add(parent)
            parent, dot, _ = parent.rpartition(".")
        return all_parent_modules

    def _is_module_blocklisted(self, module_name):
        # fast path
        if module_name in self.module_blocklist:
            return True

        # try parent modules
        all_parents = self._create_all_parent_modules(module_name)
        if any(parent in self.module_blocklist for parent in all_parents):
            return True
        return False

    def _is_function_blocklisted(self, module_name, func_name):
        # Whole module is blocked
        if self._is_module_blocklisted(module_name):
            return True

        # Function is blocked
        if (module_name, func_name) in self.function_blocklist:
            return True

        return False

    def _recursive_analyze_attribute(self, node):
        current = node
        while isinstance(current.value, ast.Attribute):
            current = current.value
        if not isinstance(current.value, ast.Name):
            return
        id = current.value.id

        def _get_child_fn(mod, node):
            if isinstance(node.value, ast.Attribute):
                submod = _get_child_fn(mod, node.value)
                return getattr(submod, node.attr, None)

            if not isinstance(node.value, ast.Name):
                return None
            return getattr(mod, node.attr, None)

        if id in self.globals:
            mod = self.fn.__globals__[id]
            child_fn = _get_child_fn(mod, node)
            if child_fn is not None and callable(child_fn):
                self.thread_unsafe, self.thread_unsafe_reason = (
                    identify_thread_unsafe_nodes(
                        child_fn,
                        self.skip_set,
                        self.unsafe_warnings,
                        self.unsafe_ctypes,
                        self.unsafe_hypothesis,
                        self.level + 1,
                    )
                )

    def _build_attribute_chain(self, node):
        chain = []
        current = node

        while isinstance(current, ast.Attribute):
            chain.insert(0, current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            chain.insert(0, current.id)

        return chain

    def _visit_attribute_call(self, node):
        if isinstance(node.value, ast.Name):
            real_mod = node.value.id
            if real_mod in self.modules_aliases:
                real_mod = self.modules_aliases[real_mod]
            if self._is_function_blocklisted(real_mod, node.attr):
                self.thread_unsafe = True
                self.thread_unsafe_reason = (
                    "calls thread-unsafe function: " f"{real_mod}.{node.attr}"
                )
            elif self.level < 2:
                self._recursive_analyze_attribute(node)
        elif isinstance(node.value, ast.Attribute):
            chain = self._build_attribute_chain(node)
            module_part = ".".join(chain[:-1])
            func_part = chain[-1]
            if self._is_function_blocklisted(module_part, func_part):
                self.thread_unsafe = True
                self.thread_unsafe_reason = (
                    f"calls thread-unsafe function: {'.'.join(chain)}"
                )
            elif self.level < 2:
                self._recursive_analyze_attribute(node)

    def _recursive_analyze_name(self, node):
        if node.id in self.globals:
            child_fn = self.fn.__globals__[node.id]
            if callable(child_fn):
                self.thread_unsafe, self.thread_unsafe_reason = (
                    identify_thread_unsafe_nodes(
                        child_fn,
                        self.skip_set,
                        self.unsafe_warnings,
                        self.unsafe_ctypes,
                        self.unsafe_hypothesis,
                        self.level + 1,
                    )
                )

    def _visit_name_call(self, node):
        if node.id in self.func_aliases:
            if self._is_function_blocklisted(*self.func_aliases[node.id]):
                self.thread_unsafe = True
                self.thread_unsafe_reason = f"calls thread-unsafe function: {node.id}"
                return

        if self.level < 2:
            self._recursive_analyze_name(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            self._visit_attribute_call(node.func)
        elif isinstance(node.func, ast.Name):
            self._visit_name_call(node.func)
        self.generic_visit(node)

    def visit_Assign(self, node):
        if len(node.targets) == 1:
            name_node = node.targets[0]
            value_node = node.value
            if getattr(name_node, "id", None) == "__thread_safe__" and not bool(
                value_node.value
            ):
                self.thread_unsafe = True
                self.thread_unsafe_reason = (
                    f"calls thread-unsafe function: {self.fn.__name__} "
                    "(inferred via func.__thread_safe__ == False)"
                )
                return

        self.generic_visit(node)

    def visit(self, node):
        if self.thread_unsafe:
            return
        return super().visit(node)


def _is_source_indented(src):
    # Find first nonblank line. If one can't be found, use placeholder.
    non_blank_lines = (line for line in src.split("\n") if line.strip() != "")
    first_non_blank_line = next(non_blank_lines, "pass")
    is_indented = first_non_blank_line[0].isspace()
    return is_indented


def _identify_thread_unsafe_nodes(
    fn, skip_set, unsafe_warnings, unsafe_ctypes, unsafe_hypothesis, level=0
):
    if is_hypothesis_test(fn):
        if hypothesis_version < HYPOTHESIS_THREADSAFE_VERSION:
            return (
                True,
                f"uses hypothesis v{'.'.join(map(str, hypothesis_version))}, which "
                "is before the first thread-safe version "
                f"(v{'.'.join(map(str, HYPOTHESIS_THREADSAFE_VERSION))})",
            )
        if unsafe_hypothesis:
            return (
                True,
                "uses Hypothesis, and pytest-run-parallel was run with "
                "--mark-hypothesis-as-unsafe",
            )

    try:
        visitor = ThreadUnsafeNodeVisitor(
            fn, skip_set, unsafe_warnings, unsafe_ctypes, unsafe_hypothesis, level=level
        )
        try:
            src = inspect.getsource(fn)
        except (OSError, TypeError):
            # if we can't get the source code (e.g. builtin function)
            # then give up and don't attempt detection but default to assuming
            # thread safety
            return False, None
        if _is_source_indented(src):
            # This test was extracted from a class or indented area, and Python needs
            # to be told to expect indentation.
            src = "if True:\n" + src
        try:
            tree = ast.parse(src)
        except (SyntaxError, ValueError):
            # AST parsing failed because the AST is invalid. Who knows why but that means
            # we can't run thread safety detection. Bail and assume thread-safe.
            return False, None
        visitor.visit(tree)
    except Exception as e:
        tb = traceback.format_exc()
        msg = (
            f"Uncaught exception while checking test '{fn}' for thread-unsafe "
            "functionality. Please report a bug to pytest-run-parallel at "
            "https://github.com/Quansight-Labs/pytest-run-parallel/issues/new "
            "including this message if thread safety detection should work.\n"
            f"{e}\n{tb}\n"
            "Assuming this test is thread-safe."
        )
        warnings.warn(msg, RuntimeWarning)
        return False, None

    return visitor.thread_unsafe, visitor.thread_unsafe_reason


cached_thread_unsafe_identify = functools.lru_cache(_identify_thread_unsafe_nodes)


def identify_thread_unsafe_nodes(*args, **kwargs):
    try:
        return cached_thread_unsafe_identify(*args, **kwargs)
    except TypeError:
        return _identify_thread_unsafe_nodes(*args, **kwargs)


def construct_thread_unsafe_fixtures(config):
    unsafe_fixtures = THREAD_UNSAFE_FIXTURES.copy()
    for item in config.getini("thread_unsafe_fixtures"):
        unsafe_fixtures[item] = False

    if config.option.mark_warnings_as_unsafe:
        unsafe_fixtures["recwarn"] = False

    return {uf[0] for uf in unsafe_fixtures.items() if not uf[1]}
