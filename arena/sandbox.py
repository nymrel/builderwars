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
import os
import queue
import shutil
import subprocess
import threading

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

POLICY = {
    "protocol": "arena/1",
    "enforced": [
        "separate_os_process (no shared memory or imports with the referee)",
        "cwd_isolated_scratch_dir (entrant is started in a per-match scratch dir)",
        "env_allowlist (only base OS vars plus names the entrant manifest declares)",
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


class Entrant:
    def __init__(
        self,
        manifest,
        workdir,
        move_timeout_s=15.0,
        max_line_bytes=64 * 1024,
        max_total_bytes=4 * 1024 * 1024,
        max_stderr_bytes=64 * 1024,
    ):
        self.name = manifest["name"]
        self.cmd = list(manifest["cmd"])
        self.declared_env = list(manifest.get("env", []))
        self.workdir = str(workdir)
        self.move_timeout_s = float(move_timeout_s)
        self.max_line_bytes = int(max_line_bytes)
        self.max_total_bytes = int(max_total_bytes)
        self.max_stderr_bytes = int(max_stderr_bytes)

        self._proc = None
        self._q = queue.Queue()
        self._reader = None
        self._stderr_buf = bytearray()
        self._stderr_thread = None
        self._bytes_seen = 0

    # -- lifecycle --------------------------------------------------------

    def _child_env(self):
        env = {k: os.environ[k] for k in _BASE_ENV_KEYS if k in os.environ}
        # The entrant declares which credential-bearing variables it needs. The
        # engine passes them through without reading, logging or hashing values.
        for name in self.declared_env:
            if name in os.environ:
                env[name] = os.environ[name]
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["ARENA_PROTOCOL"] = "arena/1"
        return env

    def start(self):
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
        self._reader = threading.Thread(target=self._pump_stdout, daemon=True)
        self._reader.start()
        self._stderr_thread = threading.Thread(target=self._pump_stderr, daemon=True)
        self._stderr_thread.start()

    def _pump_stdout(self):
        try:
            for raw in iter(self._proc.stdout.readline, b""):
                self._bytes_seen += len(raw)
                if len(raw) > self.max_line_bytes:
                    self._q.put(("error", f"stdout line exceeded {self.max_line_bytes} bytes"))
                    return
                if self._bytes_seen > self.max_total_bytes:
                    self._q.put(("error", f"stdout exceeded {self.max_total_bytes} bytes total"))
                    return
                line = raw.decode("utf-8", errors="replace").strip()
                if line:
                    self._q.put(("line", line))
        except Exception as e:  # pipe torn down mid-read
            self._q.put(("error", f"stdout read failed: {e.__class__.__name__}"))
        finally:
            self._q.put(("eof", None))

    def _pump_stderr(self):
        try:
            for raw in iter(self._proc.stderr.readline, b""):
                room = self.max_stderr_bytes - len(self._stderr_buf)
                if room > 0:
                    self._stderr_buf.extend(raw[:room])
        except Exception:
            pass

    # -- messaging --------------------------------------------------------

    def send(self, payload):
        if self._proc is None or self._proc.poll() is not None:
            raise EntrantFailure("entrant_not_running")
        data = (json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        try:
            self._proc.stdin.write(data)
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise EntrantFailure("entrant_stdin_closed", e.__class__.__name__) from e

    def recv(self, timeout_s=None):
        timeout_s = self.move_timeout_s if timeout_s is None else timeout_s
        try:
            kind, value = self._q.get(timeout=timeout_s)
        except queue.Empty:
            raise EntrantFailure("timeout", f"no response within {timeout_s:g}s")
        if kind == "eof":
            raise EntrantFailure("entrant_exited", f"exit code {self._proc.poll()}")
        if kind == "error":
            raise EntrantFailure("protocol_violation", value)
        try:
            msg = json.loads(value)
        except json.JSONDecodeError as e:
            raise EntrantFailure("malformed_json", str(e)) from e
        if not isinstance(msg, dict):
            raise EntrantFailure("malformed_message", "top-level value must be an object")
        return msg

    def ask(self, payload, timeout_s=None):
        self.send(payload)
        return self.recv(timeout_s)

    # -- teardown ---------------------------------------------------------

    def stderr_text(self):
        return self._stderr_buf.decode("utf-8", errors="replace")

    def close(self, grace_s=1.0):
        if self._proc is None:
            return
        try:
            if self._proc.poll() is None:
                try:
                    self._proc.stdin.close()
                except Exception:
                    pass
                try:
                    self._proc.wait(timeout=grace_s)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait(timeout=grace_s)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
        finally:
            for stream in (self._proc.stdout, self._proc.stderr, self._proc.stdin):
                try:
                    stream.close()
                except Exception:
                    pass
