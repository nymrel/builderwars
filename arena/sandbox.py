"""Entrant process channel.

An entrant is a subprocess that speaks JSON Lines over stdin/stdout. That is the
entire coupling. It shares no memory with the referee, cannot import it, is not
told where the transcript lives, and its working directory is a scratch dir
created for the match.

Honesty about what "sandbox" means here matters more than the word does, so the
policy is enumerated and shipped into the transcript header. See POLICY below.
A result should never imply an isolation guarantee the host did not actually
provide.
"""

import json
import math
import os
import queue
import shutil
import subprocess
import threading
import time

# Passed through so a subprocess can start at all on Windows and POSIX. None of
# these carry model access.
#
# USERPROFILE / LOCALAPPDATA / APPDATA are here because real CLI tools need them
# to find their own config and data. Probed 2026-08-14: without USERPROFILE,
# `ollama` dies with `panic: %userprofile% is not defined` before reading a
# prompt, which would block every CLI-based entrant on Windows. They widen what
# an entrant can locate on disk, but v1 already declares filesystem confinement
# unenforced below, so this removes no guarantee we actually make. Tighten this
# list and the OS-level jail together, not separately.
_BASE_ENV_KEYS = (
    "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP",
    "USERPROFILE", "LOCALAPPDATA", "APPDATA", "HOMEDRIVE", "HOMEPATH",
    "HOME", "LANG", "LC_ALL", "TZ",
)

_READ_CHUNK_BYTES = 8 * 1024
_MIN_TIMEOUT_SECONDS = 0.1
_MAX_TIMEOUT_SECONDS = 3600.0

POLICY = {
    "protocol": "arena/1",
    "enforced": [
        "separate_os_process (no shared memory or imports with the referee)",
        "cwd_isolated_scratch_dir (entrant is started in a per-match scratch dir)",
        "env_allowlist (base OS vars plus exact per-seat values explicitly provisioned by the trusted caller; manifest names never read the referee environment)",
        "no_inherited_file_handles (close_fds)",
        "transcript_path_withheld (entrant is never told where the record is written)",
        "per_move_wall_clock_timeout (exceeded -> forfeit)",
        "stdout_line_size_cap",
        "stdout_total_size_cap",
        "stderr_captured_and_capped",
        "kill_on_timeout_and_at_match_end",
    ],
    "unenforced_v1": [
        "network_egress_blocking (an entrant CAN reach the network; not restricted by the host in v1)",
        "filesystem_confinement (cwd is set, not chrooted; an entrant CAN read outside it)",
        "cpu_and_memory_limits (no job object / cgroup applied in v1)",
        "process_tree_containment (only the direct entrant PID is terminated in v1)",
    ],
    "note": (
        "The unenforced items need an OS-level jail (container, WSL cgroup, Windows job "
        "object plus a firewall profile). Until that ships, a match run on an untrusted "
        "entrant is isolated in process but not in capability, and results should be "
        "labelled accordingly."
    ),
}


class EntrantFailure(Exception):
    """The entrant did not produce a usable response. Carries a forfeit reason."""

    def __init__(self, reason, detail=None):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def _bounded_timeout(value, *, label="timeout"):
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        seconds = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be a finite number") from error
    if not math.isfinite(seconds) or not _MIN_TIMEOUT_SECONDS <= seconds <= _MAX_TIMEOUT_SECONDS:
        raise ValueError(
            f"{label} must be between {_MIN_TIMEOUT_SECONDS:g} and "
            f"{_MAX_TIMEOUT_SECONDS:g} seconds"
        )
    return seconds


def _positive_limit(value, *, label):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


class Entrant:
    def __init__(
        self,
        manifest,
        workdir,
        move_timeout_s=15.0,
        max_line_bytes=64 * 1024,
        max_total_bytes=4 * 1024 * 1024,
        max_stderr_bytes=64 * 1024,
        provisioned_env=None,
    ):
        self.name = manifest["name"]
        self.cmd = list(manifest["cmd"])
        self.declared_env = list(manifest.get("env", []))
        self.workdir = str(workdir)
        self.move_timeout_s = _bounded_timeout(move_timeout_s, label="move_timeout_s")
        self.max_line_bytes = _positive_limit(max_line_bytes, label="max_line_bytes")
        self.max_total_bytes = _positive_limit(max_total_bytes, label="max_total_bytes")
        self.max_stderr_bytes = _positive_limit(max_stderr_bytes, label="max_stderr_bytes")
        if self.max_line_bytes > self.max_total_bytes:
            raise ValueError("max_line_bytes must not exceed max_total_bytes")
        supplied = {} if provisioned_env is None else provisioned_env
        if not isinstance(supplied, dict):
            raise ValueError("provisioned_env must be an object")
        if len(self.declared_env) != len(set(self.declared_env)):
            raise ValueError("declared environment names must be unique")
        if set(supplied) != set(self.declared_env):
            raise ValueError("provisioned environment names must exactly match the manifest declaration")
        if any(
            not isinstance(name, str)
            or not isinstance(value, str)
            or "\x00" in value
            for name, value in supplied.items()
        ):
            raise ValueError("provisioned environment names and values must be strings without NUL")
        # Values are process-local custody, never logged, hashed, or recovered
        # from the referee's ambient environment merely because a manifest asks.
        self._provisioned_env = dict(supplied)

        self._proc = None
        self._q = queue.Queue()
        self._reader = None
        self._stderr_buf = bytearray()
        self._stderr_thread = None
        self._bytes_seen = 0
        self._write_lock = threading.Lock()
        self._writer_threads = set()
        self._started_once = False
        self._closed = False

    # -- lifecycle --------------------------------------------------------

    def _child_env(self):
        env = {k: os.environ[k] for k in _BASE_ENV_KEYS if k in os.environ}
        env.update(self._provisioned_env)
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["ARENA_PROTOCOL"] = "arena/1"
        return env

    def start(self):
        if self._started_once:
            raise RuntimeError("entrant process objects are single-use")
        os.makedirs(self.workdir, exist_ok=True)
        cmd = list(self.cmd)
        # Resolve the executable against PATH ourselves so a failure to find it
        # is a clear error rather than an opaque OSError.
        exe = shutil.which(cmd[0])
        if exe:
            cmd[0] = exe
        self._proc = subprocess.Popen(
            cmd,
            cwd=self.workdir,
            env=self._child_env(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            bufsize=0,
        )
        self._started_once = True
        try:
            self._reader = threading.Thread(target=self._pump_stdout, daemon=True)
            self._reader.start()
            self._stderr_thread = threading.Thread(target=self._pump_stderr, daemon=True)
            self._stderr_thread.start()
        except BaseException:
            try:
                self.close(grace_s=0.25)
            except BaseException:
                pass
            raise

    def _emit_stdout_line(self, raw):
        line = bytes(raw).decode("utf-8", errors="replace").strip()
        if line:
            self._q.put(("line", line))

    def _pump_stdout(self):
        pending = bytearray()
        proc = self._proc
        read_size = max(
            1,
            min(_READ_CHUNK_BYTES, self.max_line_bytes + 1, self.max_total_bytes + 1),
        )
        try:
            while True:
                raw = os.read(proc.stdout.fileno(), read_size)
                if not raw:
                    break
                self._bytes_seen += len(raw)
                if self._bytes_seen > self.max_total_bytes:
                    self._q.put(("error", f"stdout exceeded {self.max_total_bytes} bytes total"))
                    return
                cursor = 0
                while cursor < len(raw):
                    newline = raw.find(b"\n", cursor)
                    end = len(raw) if newline < 0 else newline
                    pending.extend(raw[cursor:end])
                    if len(pending) > self.max_line_bytes:
                        self._q.put(("error", f"stdout line exceeded {self.max_line_bytes} bytes"))
                        return
                    if newline < 0:
                        break
                    self._emit_stdout_line(pending)
                    pending.clear()
                    cursor = newline + 1
            if pending:
                self._emit_stdout_line(pending)
        except Exception as e:  # pipe torn down mid-read
            self._q.put(("error", f"stdout read failed: {e.__class__.__name__}"))
        finally:
            self._q.put(("eof", None))

    def _pump_stderr(self):
        proc = self._proc
        try:
            while True:
                raw = os.read(proc.stderr.fileno(), _READ_CHUNK_BYTES)
                if not raw:
                    break
                room = self.max_stderr_bytes - len(self._stderr_buf)
                if room > 0:
                    self._stderr_buf.extend(raw[:room])
        except Exception:
            pass

    # -- messaging --------------------------------------------------------

    @staticmethod
    def _abort_blocked_write(proc):
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=1.0)
        except Exception:
            pass

    def send(self, payload, timeout_s=None):
        timeout_s = self.move_timeout_s if timeout_s is None else _bounded_timeout(
            timeout_s, label="send timeout"
        )
        data = (json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        with self._write_lock:
            if self._closed:
                raise EntrantFailure("entrant_closed")
            proc = self._proc
            if proc is None or proc.poll() is not None:
                raise EntrantFailure("entrant_not_running")
            outcome = queue.Queue(maxsize=1)

            def write_all():
                try:
                    view = memoryview(data)
                    written = 0
                    while written < len(view):
                        count = proc.stdin.write(view[written:])
                        if count is None or count <= 0:
                            raise BrokenPipeError("entrant stdin accepted no bytes")
                        written += count
                    proc.stdin.flush()
                    outcome.put((True, None))
                except BaseException as error:
                    outcome.put((False, error))

            writer = threading.Thread(target=write_all, daemon=True)
            self._writer_threads.add(writer)
            try:
                writer.start()
            except BaseException:
                self._writer_threads.discard(writer)
                raise
            writer.join(timeout_s)
            if writer.is_alive():
                self._abort_blocked_write(proc)
                try:
                    proc.stdin.close()
                except Exception:
                    pass
                writer.join(1.0)
                if not writer.is_alive():
                    self._writer_threads.discard(writer)
                raise EntrantFailure(
                    "timeout", f"stdin write did not complete within {timeout_s:g}s"
                )
            self._writer_threads.discard(writer)
            succeeded, error = outcome.get_nowait()
            if not succeeded:
                if isinstance(error, (BrokenPipeError, OSError, ValueError)):
                    raise EntrantFailure("entrant_stdin_closed", error.__class__.__name__) from error
                raise EntrantFailure("entrant_stdin_failed", error.__class__.__name__) from error

    def recv(self, timeout_s=None):
        timeout_s = self.move_timeout_s if timeout_s is None else _bounded_timeout(
            timeout_s, label="receive timeout"
        )
        if self._closed:
            raise EntrantFailure("entrant_closed")
        proc = self._proc
        if proc is None:
            raise EntrantFailure("entrant_not_running")
        try:
            kind, value = self._q.get(timeout=timeout_s)
        except queue.Empty:
            raise EntrantFailure("timeout", f"no response within {timeout_s:g}s")
        if self._closed:
            raise EntrantFailure("entrant_closed")
        if kind == "eof":
            raise EntrantFailure("entrant_exited", f"exit code {proc.poll()}")
        if kind == "error":
            raise EntrantFailure("protocol_violation", value)
        try:
            msg = json.loads(value)
        except (ValueError, RecursionError) as e:
            raise EntrantFailure("malformed_json", str(e)) from e
        if not isinstance(msg, dict):
            raise EntrantFailure("malformed_message", "top-level value must be an object")
        return msg

    def ask(self, payload, timeout_s=None):
        timeout_s = self.move_timeout_s if timeout_s is None else _bounded_timeout(
            timeout_s, label="request timeout"
        )
        deadline = time.monotonic() + timeout_s
        self.send(payload, timeout_s=timeout_s)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise EntrantFailure("timeout", f"request exceeded {timeout_s:g}s")
        return self.recv(max(_MIN_TIMEOUT_SECONDS, remaining))

    # -- teardown ---------------------------------------------------------

    def stderr_text(self):
        return self._stderr_buf.decode("utf-8", errors="replace")

    def close(self, grace_s=1.0):
        proc = self._proc
        if proc is None:
            return
        grace_s = _bounded_timeout(grace_s, label="close grace")
        # Seal messaging before teardown so concurrent or later reads cannot
        # consume a buffered line as if it belonged to a live entrant.
        self._closed = True
        errors = []

        def remember(error):
            if not errors:
                errors.append(error)

        try:
            if proc.poll() is None:
                try:
                    proc.stdin.close()
                except Exception:
                    pass
                try:
                    proc.wait(timeout=grace_s)
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                    except Exception as error:
                        remember(error)
                    try:
                        proc.wait(timeout=grace_s)
                    except Exception as error:
                        remember(error)
        except Exception as error:
            remember(error)
            try:
                proc.kill()
                proc.wait(timeout=grace_s)
            except Exception as kill_error:
                remember(kill_error)
        finally:
            for stream in (proc.stdout, proc.stderr, proc.stdin):
                try:
                    stream.close()
                except Exception:
                    pass
            for thread in (self._reader, self._stderr_thread, *tuple(self._writer_threads)):
                if thread is not None and thread is not threading.current_thread():
                    if thread.ident is None:
                        self._writer_threads.discard(thread)
                        continue
                    thread.join(grace_s)
                    if thread.is_alive():
                        remember(RuntimeError("entrant I/O thread did not stop"))
                    else:
                        self._writer_threads.discard(thread)
            if proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=grace_s)
                except Exception as error:
                    remember(error)
            if proc.poll() is None:
                remember(RuntimeError("entrant process was not reaped"))
            else:
                self._proc = None
                self._reader = None
                self._stderr_thread = None
            while True:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break
        if errors:
            raise errors[0]
