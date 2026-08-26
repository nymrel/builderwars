"""Cross-platform descendant-process custody for local arena entrants.

This is deliberately one narrow control: the fixed runner places each entrant
and its ordinary descendants under one teardown handle. Windows uses a
kill-on-close Job Object; POSIX uses a new session and signals the entire
process group. A deliberately detaching POSIX descendant can escape a process
group, so this does not claim hostile-code containment, CPU, memory,
filesystem, or network isolation.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time


class ProcessTreeError(RuntimeError):
    """The host could not establish or release descendant-process custody."""


class ProcessTree:
    """Own one direct process and the descendants that remain in its custody group."""

    def __init__(self, process: subprocess.Popen, *, job_handle=None):
        self.process = process
        self._job_handle = job_handle
        self._closed = False

    @classmethod
    def spawn(cls, args, **kwargs) -> "ProcessTree":
        """Start a child only when descendant containment can be established."""

        if os.name == "nt":
            return cls._spawn_windows(args, **kwargs)
        if "start_new_session" in kwargs:
            raise ProcessTreeError(
                "caller cannot override process-tree session custody"
            )
        try:
            process = subprocess.Popen(args, start_new_session=True, **kwargs)
        except OSError as error:
            raise ProcessTreeError("contained process could not be started") from error
        return cls(process)

    @classmethod
    def _spawn_windows(cls, args, **kwargs) -> "ProcessTree":
        if "creationflags" in kwargs:
            raise ProcessTreeError("caller cannot override process-tree creation flags")
        job_handle = _create_kill_on_close_job()
        process = None
        try:
            process = subprocess.Popen(
                args,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                **kwargs,
            )
            _assign_process_to_job(job_handle, process)
            return cls(process, job_handle=job_handle)
        except BaseException:
            if process is not None:
                try:
                    process.kill()
                except Exception:
                    pass
                try:
                    process.wait(timeout=2.0)
                except Exception:
                    pass
            _close_windows_handle(job_handle)
            raise

    def terminate(self, grace_s: float = 1.0) -> None:
        """Stop the direct process and all descendants, then reap the parent."""

        if self._closed:
            return
        grace = _grace_seconds(grace_s)
        process = self.process
        if os.name == "nt":
            self._terminate_windows(process, grace)
        else:
            self._terminate_posix(process, grace)

    def close(self, grace_s: float = 1.0) -> None:
        """Release custody, killing any descendant left behind by the parent."""

        if self._closed:
            return
        error = None
        try:
            self.terminate(grace_s=grace_s)
        except BaseException as caught:
            error = caught
        finally:
            if os.name == "nt" and self._job_handle is not None:
                try:
                    _close_windows_handle(self._job_handle)
                except BaseException as caught:
                    if error is None:
                        error = caught
                self._job_handle = None
            self._closed = True
        if error is not None:
            raise error

    def _terminate_windows(self, process: subprocess.Popen, grace: float) -> None:
        if process.poll() is None:
            try:
                process.send_signal(signal.CTRL_BREAK_EVENT)
            except (AttributeError, OSError, ValueError):
                pass
            try:
                process.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                pass
        # Closing the handle below also has kill-on-close semantics. Explicit
        # termination here makes cancellation synchronous and testable.
        if self._job_handle is not None:
            _terminate_windows_job(self._job_handle)
        if process.poll() is None:
            try:
                process.wait(timeout=grace)
            except subprocess.TimeoutExpired as error:
                raise ProcessTreeError(
                    "contained Windows process was not reaped"
                ) from error

    @staticmethod
    def _terminate_posix(process: subprocess.Popen, grace: float) -> None:
        group_id = process.pid
        try:
            os.killpg(group_id, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError as error:
            raise ProcessTreeError(
                "contained POSIX process group could not terminate"
            ) from error
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            process.poll()
            if not _posix_group_alive(group_id):
                break
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        if _posix_group_alive(group_id):
            try:
                os.killpg(group_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as error:
                raise ProcessTreeError(
                    "contained POSIX process group could not be killed"
                ) from error
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired as error:
            raise ProcessTreeError("contained POSIX process was not reaped") from error
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline and _posix_group_alive(group_id):
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        if _posix_group_alive(group_id):
            raise ProcessTreeError("contained POSIX process group remained alive")

    def __enter__(self) -> "ProcessTree":
        return self

    def __exit__(self, _error_type, _error, _traceback) -> None:
        self.close()


def _grace_seconds(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProcessTreeError("process-tree grace period is invalid")
    grace = float(value)
    if not 0.1 <= grace <= 30.0:
        raise ProcessTreeError("process-tree grace period is invalid")
    return grace


def _posix_group_alive(group_id: int) -> bool:
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

    class _JobObjectBasicLimitInformation(ctypes.Structure):
        _fields_ = (
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        )

    class _IoCounters(ctypes.Structure):
        _fields_ = tuple(
            (name, ctypes.c_ulonglong)
            for name in (
                "ReadOperationCount",
                "WriteOperationCount",
                "OtherOperationCount",
                "ReadTransferCount",
                "WriteTransferCount",
                "OtherTransferCount",
            )
        )

    class _JobObjectExtendedLimitInformation(ctypes.Structure):
        _fields_ = (
            ("BasicLimitInformation", _JobObjectBasicLimitInformation),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        )

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    _kernel32.SetInformationJobObject.restype = wintypes.BOOL
    _kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    _kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _kernel32.TerminateJobObject.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _kernel32.CloseHandle.restype = wintypes.BOOL


def _create_kill_on_close_job():
    handle = _kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise ProcessTreeError(_windows_error("Windows Job Object creation failed"))
    limits = _JobObjectExtendedLimitInformation()
    limits.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not _kernel32.SetInformationJobObject(
        handle,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(limits),
        ctypes.sizeof(limits),
    ):
        detail = _windows_error("Windows Job Object configuration failed")
        _kernel32.CloseHandle(handle)
        raise ProcessTreeError(detail)
    return handle


def _assign_process_to_job(job_handle, process: subprocess.Popen) -> None:
    process_handle = wintypes.HANDLE(int(process._handle))
    if not _kernel32.AssignProcessToJobObject(job_handle, process_handle):
        raise ProcessTreeError(_windows_error("Windows process-tree assignment failed"))


def _terminate_windows_job(job_handle) -> None:
    if not _kernel32.TerminateJobObject(job_handle, 1):
        error = ctypes.get_last_error()
        # ERROR_ACCESS_DENIED means the job is already terminating or empty.
        if error != 5:
            raise ProcessTreeError(
                _windows_error("Windows process tree could not terminate", error)
            )


def _close_windows_handle(handle) -> None:
    if handle and not _kernel32.CloseHandle(handle):
        raise ProcessTreeError(
            _windows_error("Windows Job Object handle did not close")
        )


def _windows_error(label: str, code: int | None = None) -> str:
    number = ctypes.get_last_error() if code is None else code
    return f"{label} (winerror {number})"
