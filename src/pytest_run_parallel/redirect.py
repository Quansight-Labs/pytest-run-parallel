import contextlib
import sys
import threading
from dataclasses import dataclass
from types import SimpleNamespace
from typing import TextIO


# eq=False so that remove_entry removes based on identity, not equality. Otherwise
# we would mistakenly remove the wrong entry if their streams compared equal.
@dataclass(eq=False)
class _Entry:
    stream: TextIO
    # None means per_thread=False
    thread_id: int | None


class PerThreadStream:
    def __init__(self, default_stream: TextIO):
        self.default_stream = default_stream
        self._stack: list[_Entry] = []

    @property
    def _current_stream(self) -> TextIO:
        thread_id = threading.get_ident()

        # look for the most recent redirect which was either:
        # * per_thread=False
        # * per_thread=True, and in our thread
        #
        # If none match, fall back to the default stream.
        for entry in reversed(self._stack):
            if entry.thread_id is None or entry.thread_id == thread_id:
                return entry.stream

        return self.default_stream

    def add_entry(self, entry: _Entry) -> None:
        self._stack.append(entry)

    def remove_entry(self, entry: _Entry) -> None:
        self._stack.remove(entry)

    def __getattr__(self, name):
        return getattr(self._current_stream, name)


_stdout_lock = threading.Lock()
_stdout_stream_ref = SimpleNamespace(value=None)

_stderr_lock = threading.Lock()
_stderr_stream_ref = SimpleNamespace(value=None)


def _make_redirect(attr, stream_ref, lock):
    @contextlib.contextmanager
    def redirect(new_target: TextIO, *, per_thread: bool = False):
        with lock:
            if stream_ref.value is None:
                stream_ref.value = PerThreadStream(getattr(sys, attr))
                setattr(sys, attr, stream_ref.value)
            entry = _Entry(
                stream=new_target,
                thread_id=threading.get_ident() if per_thread else None,
            )
            stream_ref.value.add_entry(entry)

        try:
            yield new_target
        finally:
            with lock:
                stream_ref.value.remove_entry(entry)
                if len(stream_ref.value._stack) == 0:
                    setattr(sys, attr, stream_ref.value.default_stream)
                    stream_ref.value = None

    return redirect


redirect_stdout = _make_redirect("stdout", _stdout_stream_ref, _stdout_lock)
redirect_stderr = _make_redirect("stderr", _stderr_stream_ref, _stderr_lock)
