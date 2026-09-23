"""
novelcast/db/access_gate.py

Coordinates a live database-engine swap (relocation) against concurrent
repository session usage. Repository sessions register as "readers" for
their whole lifetime via db_access(); a relocation acts as a single
"writer" via db_exclusive_access(), which blocks new readers from
starting and waits for in-flight ones to finish before the caller is
allowed to dispose the old engine and rebind SessionLocal.

This exists specifically to prevent a session captured against the old
engine object being used after the underlying file has been moved away,
which would cause SQLite to silently create a new, empty database file
at the old path.
"""

import threading
from contextlib import contextmanager

_cv = threading.Condition()
_active_sessions = 0
_relocation_in_progress = False


@contextmanager
def db_access():
    """Wrap the full lifetime of a repository session in this. Blocks
    briefly if a relocation is in progress; otherwise near-zero overhead."""
    global _active_sessions
    with _cv:
        while _relocation_in_progress:
            _cv.wait()
        _active_sessions += 1
    try:
        yield
    finally:
        with _cv:
            _active_sessions -= 1
            _cv.notify_all()


@contextmanager
def db_exclusive_access(timeout: float = 30.0):
    """Blocks new sessions, waits for in-flight ones to drain, then yields
    so the caller can safely dispose/rebuild/rebind the engine. Raises
    RuntimeError if a relocation is already running, or TimeoutError if
    sessions don't drain in time (e.g. a stuck long-lived session in a
    background worker)."""
    global _relocation_in_progress

    with _cv:
        if _relocation_in_progress:
            raise RuntimeError("A database relocation is already in progress")
        _relocation_in_progress = True

        if not _cv.wait_for(lambda: _active_sessions == 0, timeout=timeout):
            _relocation_in_progress = False
            _cv.notify_all()
            raise TimeoutError(
                f"Timed out after {timeout}s waiting for in-flight database sessions to finish"
            )

    try:
        yield
    finally:
        with _cv:
            _relocation_in_progress = False
            _cv.notify_all()
            