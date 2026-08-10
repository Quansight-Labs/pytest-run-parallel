import sys
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Barrier, Event, Thread

import pytest

from pytest_run_parallel import redirect_stderr, redirect_stdout

# inherently messing with global state
pytestmark = pytest.mark.parallel_threads(1)


@pytest.mark.parametrize(
    "redirect, stream_attr, print_",
    [
        pytest.param(redirect_stdout, "stdout", print, id="stdout"),
        pytest.param(
            redirect_stderr,
            "stderr",
            lambda *args, **kwargs: print(*args, file=sys.stderr, **kwargs),
            id="stderr",
        ),
    ],
)
def test_basic_redirect(redirect, stream_attr, print_):
    buf = StringIO()
    with redirect(buf, per_thread=True):
        print_("foo")
    assert buf.getvalue() == "foo\n"

    original = getattr(sys, stream_attr)
    assert getattr(sys, stream_attr) is original


def test_stdout_and_stderr_are_independent():
    stdout_buf = StringIO()
    stderr_buf = StringIO()

    with (
        redirect_stdout(stdout_buf, per_thread=True),
        redirect_stderr(stderr_buf, per_thread=True),
    ):
        print("to stdout")
        print("to stderr", file=sys.stderr)

    assert stdout_buf.getvalue() == "to stdout\n"
    assert stderr_buf.getvalue() == "to stderr\n"


def test_single_thread():
    buf = StringIO()
    with redirect_stdout(buf, per_thread=True):
        print("foo")
    assert buf.getvalue() == "foo\n"


def test_delegates_explicit_writes():
    buf = StringIO()
    with redirect_stdout(buf, per_thread=True):
        sys.stdout.write("line1\n")
        sys.stdout.writelines(["line2\n", "line3\n"])
    assert buf.getvalue() == "line1\nline2\nline3\n"


def test_redirect_to_file():
    with (
        NamedTemporaryFile(mode="w", delete=False) as f,
        redirect_stdout(f, per_thread=True),
    ):
        print("foo")
    assert Path(f.name).read_text() == "foo\n"
    Path(f.name).unlink()


def test_no_per_thread():
    buf = StringIO()
    with redirect_stdout(buf):
        print("foo")
    assert buf.getvalue() == "foo\n"


def test_restores_sys_stdout():
    original_stdout = sys.stdout
    with redirect_stdout(StringIO(), per_thread=True):
        print("foo")
    assert sys.stdout is original_stdout


def test_per_thread_doesnt_affect_main_thread():
    main_buf = StringIO()
    thread_buf = StringIO()
    entered = Event()
    done = Event()

    def thread1():
        with redirect_stdout(thread_buf, per_thread=True):
            entered.set()
            done.wait()

    original_stdout = sys.stdout
    sys.stdout = main_buf
    try:
        t = Thread(target=thread1)
        t.start()
        entered.wait()
        # the thread's redirect is set, but it shouldn't affect us.
        print("from main")
        done.set()
        t.join()
    finally:
        sys.stdout = original_stdout

    assert thread_buf.getvalue() == ""
    assert main_buf.getvalue() == "from main\n"


def test_cleans_up_on_exception():
    original_stdout = sys.stdout
    buf = StringIO()

    with (
        pytest.raises(ValueError, match="bar"),
        redirect_stdout(buf, per_thread=True),
    ):
        print("foo")
        raise ValueError("bar")

    assert "foo" in buf.getvalue()
    assert sys.stdout is original_stdout


def test_stress_test():
    original_stdout = sys.stdout

    for i in range(50):
        buf = StringIO()
        with redirect_stdout(buf, per_thread=True):
            print(f"iteration {i}")
        assert buf.getvalue() == f"iteration {i}\n"

    assert sys.stdout is original_stdout


def test_mixing_per_thread_true_and_false():
    stream1 = StringIO()
    stream2 = StringIO()

    with redirect_stdout(stream1, per_thread=True):
        print("per_thread true")
        with redirect_stdout(stream2, per_thread=False):
            print("per_thread false")
        print("back to true")

    assert stream1.getvalue() == "per_thread true\nback to true\n"
    assert stream2.getvalue() == "per_thread false\n"


def test_nested_single_thread():
    s1 = StringIO()
    s2 = StringIO()
    s3 = StringIO()

    with redirect_stdout(s1, per_thread=True):
        print("start1")
        with redirect_stdout(s2, per_thread=True):
            print("start2")
            with redirect_stdout(s3, per_thread=True):
                print("start3")
                print("end3")
            print("end2")
        print("end1")

    assert s1.getvalue() == "start1\nend1\n"
    assert s2.getvalue() == "start2\nend2\n"
    assert s3.getvalue() == "start3\nend3\n"


def test_simultaneous_threads():
    n_threads = 10
    barrier1 = Barrier(n_threads)
    barrier2 = Barrier(n_threads)
    bufs = [StringIO() for _ in range(n_threads)]

    def f(n, stream):
        barrier1.wait()
        with redirect_stdout(stream, per_thread=True):
            print(f"thread {n}")
            barrier2.wait()

    threads = [Thread(target=f, args=(i, bufs[i])) for i in range(n_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for i in range(n_threads):
        assert bufs[i].getvalue() == f"thread {i}\n"


def test_per_thread_true_then_false():
    # this test sets up two threads:
    #
    #  - A enters per_thread=True
    #  -   B enters per_thread=False
    #  -     A prints
    #  -   A exits (restore to actual sys.stdout)
    #  - B exits (restore to A's PerThreadState)
    #
    # When B enters, the stdlib behavior is to overwrite sys.stdout completely,
    # overwriting the per-thread setup of A.
    #
    # We have a design decision to make here. If you request a per_thread=False
    # overwrite while a per_thread=True overwrite is active, we can either:
    #
    # (1) respect this global overwrite and redirect all per-thread streams to the
    #   new context manager
    # (2) treat this per_thread=False request as if it were per_thread=True
    #
    # We choose (1).

    original_stdout = sys.stdout

    b_start = Event()
    a_start = Event()
    a_end = Event()
    stream_a = StringIO()
    stream_b = StringIO()

    def thread_a():
        with redirect_stdout(stream_a, per_thread=True):
            a_start.set()
            b_start.wait()
            print("from_a")
        a_end.set()

    def thread_b():
        a_start.wait()
        with redirect_stdout(stream_b):
            b_start.set()
            a_end.wait()

    t_a = Thread(target=thread_a)
    t_b = Thread(target=thread_b)

    t_a.start()
    t_b.start()
    t_a.join()
    t_b.join()

    assert stream_a.getvalue() == ""
    assert stream_b.getvalue() == "from_a\n"
    assert sys.stdout is original_stdout


def test_per_thread_false_then_true():
    # this test sets up two threads:
    #
    #  - A enters per_thread=False
    #  -   B enters per_thread=True
    #  -     A exits (restore to actual sys.stdout)
    #  -   B prints
    #  - B exits

    original_stdout = sys.stdout

    b_start = Event()
    a_start = Event()
    a_end = Event()
    stream_a = StringIO()
    stream_b = StringIO()

    def thread_a():
        with redirect_stdout(stream_a):
            a_start.set()
            b_start.wait()
        a_end.set()

    def thread_b():
        a_start.wait()
        with redirect_stdout(stream_b, per_thread=True):
            b_start.set()
            a_end.wait()
            print("from_b")

    t_a = Thread(target=thread_a)
    t_b = Thread(target=thread_b)

    t_a.start()
    t_b.start()
    t_a.join()
    t_b.join()

    assert stream_a.getvalue() == ""
    assert stream_b.getvalue() == "from_b\n"
    assert sys.stdout is original_stdout


def test_stacked_globals_resurface():
    # Thread timeline:
    #   A enters per_thread=True
    #     B enters per_thread=False
    #       C enters per_thread=False
    #         A prints (captured by C global)
    #       C exits
    #       A prints (captured by B global)
    #     B exits
    #     A prints (captured by A per-thread)
    #   A exits

    original_stdout = sys.stdout
    stream_a = StringIO()
    stream_b = StringIO()
    stream_c = StringIO()

    a_entered = Event()
    b_entered = Event()
    c_entered = Event()
    print1_done = Event()
    c_exited = Event()
    print2_done = Event()
    b_exited = Event()

    def thread_a():
        with redirect_stdout(stream_a, per_thread=True):
            a_entered.set()
            c_entered.wait()
            print("to_c")
            print1_done.set()
            c_exited.wait()
            print("to_b")
            print2_done.set()
            b_exited.wait()
            print("to_a")

    def thread_b():
        a_entered.wait()
        with redirect_stdout(stream_b, per_thread=False):
            b_entered.set()
            print2_done.wait()
        b_exited.set()

    def thread_c():
        b_entered.wait()
        with redirect_stdout(stream_c, per_thread=False):
            c_entered.set()
            print1_done.wait()
        c_exited.set()

    threads = [Thread(target=t) for t in [thread_a, thread_b, thread_c]]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert stream_c.getvalue() == "to_c\n"
    assert stream_b.getvalue() == "to_b\n"
    assert stream_a.getvalue() == "to_a\n"
    assert sys.stdout is original_stdout


class NamedStream(StringIO):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __eq__(self, other):
        return isinstance(other, NamedStream) and self.name == other.name


def test_equal_streams_pops_correctly():
    original = sys.stdout

    stream_a = NamedStream("a")
    stream_b = NamedStream("a")
    assert stream_a == stream_b

    a_start = Event()
    b_start = Event()
    b_end = Event()

    def thread_a():
        with redirect_stdout(stream_a, per_thread=False):
            a_start.set()
            b_start.wait()
            b_end.wait()
            print("from_a")

    def thread_b():
        a_start.wait()
        with redirect_stdout(stream_b, per_thread=False):
            b_start.set()
        b_end.set()

    t_a = Thread(target=thread_a)
    t_b = Thread(target=thread_b)
    t_a.start()
    t_b.start()
    t_a.join()
    t_b.join()

    assert stream_a.getvalue() == "from_a\n"
    assert stream_b.getvalue() == ""
    assert sys.stdout is original
