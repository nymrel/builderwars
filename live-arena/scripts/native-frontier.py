"""Personal native-client chess research. No provider adapters or credential handling.

stdin: {prompt, milliseconds}; argv: astra|fable|grok|gemini.
Only public final text and explicitly reported metadata leave this process.
"""
import ctypes
import json
import math
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time

MODELS = {"astra": "gpt-6-astra", "fable": "fable", "grok": "cursor-grok-4.6-high", "gemini": "gemini-3.1-pro-high"}
MAX_INPUT = 16384
MAX_OUTPUT = 1048576
REPO = Path(__file__).resolve().parents[2]
ENV_KEYS = ("APPDATA ANTHROPIC_CONFIG_DIR CLAUDE_CONFIG_DIR CODEX_HOME COLORTERM COMSPEC HOME HOMEDRIVE HOMEPATH HERMES_HOME LANG LC_ALL LC_CTYPE LOCALAPPDATA NODE_EXTRA_CA_CERTS NO_COLOR OPENCODE_CONFIG_DIR PATH PATHEXT REQUESTS_CA_BUNDLE SHELL SSL_CERT_DIR SSL_CERT_FILE SYSTEMROOT TERM TEMP TMP TMPDIR TZ USERPROFILE WINDIR XDG_CACHE_HOME XDG_CONFIG_HOME XDG_DATA_HOME").split()


class Failure(Exception):
    """Messages are fixed safe diagnostics, never provider output."""


class OwnedTemporaryDirectory(tempfile.TemporaryDirectory):
    def cleanup(self):
        until = time.monotonic() + 2
        while True:
            try:
                return super().cleanup()
            except PermissionError:
                if time.monotonic() >= until:
                    raise Failure("Owned temporary directory cleanup failed") from None
                time.sleep(.02)


def request(raw):
    if len(raw) > MAX_INPUT:
        raise Failure("Input exceeds 16 KiB")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise Failure("Malformed input") from None
    if (not isinstance(data, dict) or set(data) != {"prompt", "milliseconds"}
            or not isinstance(data["prompt"], str) or not data["prompt"].strip()
            or "\0" in data["prompt"] or type(data["milliseconds"]) is not int
            or not 1 <= data["milliseconds"] <= 120000):
        raise Failure("Invalid prompt or timeout")
    return data


def safe_path(path):
    path = Path(path).resolve()
    if not path.is_file() or path.is_relative_to(REPO):
        raise Failure("Native client unavailable outside repository")
    return str(path)


def launcher(name):
    # Search explicit PATH directories, never the working directory.
    for entry in os.get_exec_path():
        directory = Path(entry)
        if not directory.is_absolute() or directory.resolve().is_relative_to(REPO):
            continue
        for suffix in ((".exe", ".cmd", ".ps1") if os.name == "nt" else ("",)):
            path = directory / (name + suffix)
            if path.is_file():
                return Path(safe_path(path))
    raise Failure("Official native client not found")


def executable(family):
    name = {"astra": "codex", "fable": "claude", "grok": "cursor-agent", "gemini": "agy"}[family]
    path = launcher(name)
    if os.name != "nt" or path.suffix.lower() == ".exe":
        return [safe_path(path)]
    if family == "fable":
        return [safe_path(path.parent / "node_modules/@anthropic-ai/claude-code/bin/claude.exe")]
    if family == "astra":
        package = path.parent / "node_modules/@openai/codex"
        candidates = list(package.glob("node_modules/@openai/codex-win32-*/vendor/*/bin/codex.exe"))
        if len(candidates) != 1:
            raise Failure("Ambiguous native Codex package")
        return [safe_path(candidates[0])]
    if family == "grok":
        root = path.parent
        if not (root / "node.exe").is_file():
            versions = [p for p in (root / "versions").iterdir() if p.is_dir() and re.fullmatch(r"\d{4}\.\d{2}\.\d{2}(?:-\d{2}-\d{2}-\d{2})?-[a-f0-9]+", p.name)]
            if not versions:
                raise Failure("Cursor native package unavailable")
            root = max(versions, key=lambda p: p.name)
        return [safe_path(root / "node.exe"), safe_path(root / "index.js")]
    raise Failure("Unsupported native launcher")


def route(family, prompt, milliseconds):
    if family not in MODELS:
        raise Failure("Unknown native family")
    model = MODELS[family]
    if family == "astra":
        args = ["exec", "--ignore-user-config", "--ignore-rules", "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check", "--json", "-m", model, "-c", "model_reasoning_effort=high", "-c", "project_doc_max_bytes=0", "-"]
    elif family == "fable":
        args = ["-p", "--model", model, "--effort", "high", "--safe-mode", "--strict-mcp-config", "--tools", "", "--no-session-persistence", "--output-format", "json"]
    elif family == "grok":
        args = ["--mode", "ask", "--model", model, "--output-format", "json", "--print", prompt]
    else:
        args = ["--mode", "plan", "--sandbox", "--model", model, "--output-format", "json", "--print-timeout", str(milliseconds) + "ms", "--print", prompt]
    return executable(family) + args, prompt.encode("utf-8") if family in ("astra", "fable") else b""


def child_env(family):
    # Native Claude auth policy: OS inheritance, no copying/rewriting values.
    if family == "fable":
        return None
    return {k: v for k, v in os.environ.items() if k.upper() in ENV_KEYS}


class WindowsJob:
    """Assign a suspended child before it can spawn; closing kills its entire tree."""
    def __init__(self, process):
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64), ("flags", w.DWORD), ("min_work", ctypes.c_size_t), ("max_work", ctypes.c_size_t), ("active", w.DWORD), ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]
        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", ctypes.c_uint64 * 6), ("process_mem", ctypes.c_size_t), ("job_mem", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.CreateJobObjectW.restype = w.HANDLE
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.api.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.api.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
        self.api.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p]
        self.api.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        info = Extended(); info.basic.flags = 0x2000
        if not self.handle or not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)) or not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            self.close()
            raise Failure("Cannot establish native process tree custody")
        resume = ctypes.WinDLL("ntdll").NtResumeProcess
        resume.argtypes = [w.HANDLE]; resume.restype = ctypes.c_long
        if resume(int(process._handle)) != 0:
            self.close()
            raise Failure("Cannot resume owned native process")

    def close(self):
        if self.handle:
            # Closing is asynchronous. Drain accounting before removing the cwd,
            # because an exiting descendant may still hold that directory open.
            self.api.TerminateJobObject(self.handle, 1)
            until = time.monotonic() + 2
            accounting = ctypes.create_string_buffer(48)
            while time.monotonic() < until:
                if not self.api.QueryInformationJobObject(self.handle, 1, accounting, 48, None): break
                if ctypes.c_uint32.from_buffer(accounting, 40).value == 0: break
                time.sleep(.01)
            self.api.CloseHandle(self.handle)
            self.handle = None


def run_child(argv, payload, milliseconds, family):
    started = time.monotonic(); deadline = started + milliseconds / 1000
    process = None; job = None; threads = []
    # Fixed OS temporary parent avoids caller-controlled TEMP pointing at Desktop.
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Temp" if os.name == "nt" else Path("/tmp")
    if not base.is_absolute() or base.resolve().is_relative_to(REPO.parent):
        raise Failure("Unsafe native temporary directory")
    with OwnedTemporaryDirectory(prefix="bw-native-", dir=base) as workdir:
        try:
            options = dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir, env=child_env(family))
            if os.name == "nt":
                options["creationflags"] = subprocess.CREATE_NO_WINDOW | 4
            else:
                options["start_new_session"] = True
            process = subprocess.Popen(argv, **options)
            if os.name == "nt":
                job = WindowsJob(process)
            chunks = queue.Queue(maxsize=16); stopped = threading.Event()
            def publish(item):
                while not stopped.is_set():
                    try:
                        chunks.put(item, timeout=.02); return
                    except queue.Full:
                        pass
            def reader(stream, label):
                try:
                    while True:
                        data = stream.read(4096)
                        if not data: break
                        publish((label, data))
                except (OSError, ValueError):
                    pass  # Tree shutdown may close a pipe; never retain its output.
                finally:
                    publish((label, None))
            def writer():
                try:
                    process.stdin.write(payload); process.stdin.close()
                except (OSError, ValueError):
                    pass
            for stream, label in ((process.stdout, "out"), (process.stderr, "err")):
                thread = threading.Thread(target=reader, args=(stream, label), daemon=True); thread.start(); threads.append(thread)
            thread = threading.Thread(target=writer, daemon=True); thread.start(); threads.append(thread)
            output = bytearray(); total = 0; done = 0
            while done != 2:
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise Failure("Native client timeout")
                try: label, data = chunks.get(timeout=min(remaining, .05))
                except queue.Empty: continue
                if data is None: done += 1; continue
                total += len(data)
                if total > MAX_OUTPUT: raise Failure("Native output exceeds 1 MiB")
                if label == "out": output.extend(data)
            remaining = deadline - time.monotonic()
            if remaining <= 0: raise Failure("Native client timeout")
            if process.wait(timeout=remaining): raise Failure("Native client exited unsuccessfully")
            return bytes(output), round((time.monotonic() - started) * 1000)
        except subprocess.TimeoutExpired:
            raise Failure("Native client timeout") from None
        finally:
            if "stopped" in locals(): stopped.set()
            if job: job.close()
            if process:
                if os.name != "nt":
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                elif process.poll() is None:
                    process.kill()
                process.wait(timeout=2)
                for thread in threads: thread.join(timeout=.2)
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream: stream.close()


def tool_or_error(value):
    if isinstance(value, list):
        for item in value: tool_or_error(item)
    elif isinstance(value, dict):
        kind = value.get("type", "")
        if kind in ("command_execution", "mcp_tool_call", "web_search", "file_change", "tool_use", "tool_result", "tool_call", "function_call"):
            raise Failure("Native client reported tool activity")
        if kind in ("error", "turn.failed") or value.get("is_error") or value.get("error") or str(value.get("subtype", "")).startswith("error"):
            raise Failure("Native client reported an error")
        for key, item in value.items():
            if key in ("tool_calls", "toolCalls", "tool_uses", "toolsUsed", "tool_use_count") and item:
                raise Failure("Native client reported tool activity")
            if key in ("web_search_requests", "web_fetch_requests") and item:
                raise Failure("Native client reported tool activity")
            tool_or_error(item)


def number(value, integer=False):
    if value is None: return None
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (integer and type(value) is not int):
        raise Failure("Invalid reported usage")
    return value


def parse_output(raw, family, elapsed):
    if len(raw) > MAX_OUTPUT: raise Failure("Native output exceeds 1 MiB")
    try:
        text = raw.decode("utf-8")
        events = [json.loads(line) for line in text.splitlines() if line.strip()] if family == "astra" else [json.loads(text)]
    except (UnicodeError, ValueError):
        raise Failure("Malformed native JSON") from None
    if not events or any(not isinstance(e, dict) for e in events): raise Failure("Malformed native response")
    for event in events: tool_or_error(event)
    final = None; meta = {}; usage = {}; resolved = None; evidence = "unreported"
    if family == "astra":
        for event in events:
            if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "agent_message":
                final = event["item"].get("text")
            if event.get("type") == "turn.completed": meta = event; usage = event.get("usage", {})
        if not meta: raise Failure("Native turn did not complete")
    else:
        meta = events[0]; final = meta.get("result", meta.get("response")); usage = meta.get("usage") or {}
        if meta.get("type") not in (None, "result") or meta.get("subtype") not in (None, "success"):
            raise Failure("Native turn did not complete")
    model_usage = meta.get("modelUsage")
    if isinstance(model_usage, dict) and len(model_usage) == 1:
        resolved = next(iter(model_usage)); evidence = "provider-response"
        if not usage: usage = model_usage[resolved]
    elif family == "fable" and isinstance(model_usage, dict):
        main = [name for name in model_usage if name.startswith("claude-fable-")]
        if len(main) == 1 and all(name == main[0] or name.startswith("claude-haiku-") for name in model_usage):
            resolved = main[0]; evidence = "provider-response"
        # Keep result-level aggregate usage/cost including helper calls. Never
        # misrepresent the main model's usage as the entire invocation's usage.
    elif isinstance(meta.get("model"), str): resolved = meta["model"]; evidence = "client-reported"
    if resolved is not None and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,127}", resolved):
        raise Failure("Malformed reported model")
    if not isinstance(final, str) or not isinstance(usage, dict): raise Failure("Missing public final answer")
    answer = final.strip()
    if answer.startswith("```json\n") and answer.endswith("\n```"): answer = answer[8:-4].strip()
    try:
        parsed = json.loads(answer)
    except ValueError:
        parsed = {"move": answer, "comment": ""}
    if (not isinstance(parsed, dict) or set(parsed) - {"move", "comment"}
            or not isinstance(parsed.get("move"), str) or not re.fullmatch(r"[a-h][1-8][a-h][1-8][qrbn]?", parsed["move"])
            or not isinstance(parsed.get("comment", ""), str) or len(parsed.get("comment", "")) > 180
            or any(ord(c) < 32 for c in parsed.get("comment", ""))):
        raise Failure("Malformed chess final answer")
    return {"move": parsed["move"], "comment": parsed.get("comment", ""), "requestedModel": MODELS[family], "resolvedModel": resolved,
            "identityEvidence": evidence, "inputTokens": number(usage.get("input_tokens", usage.get("inputTokens")), True),
            "outputTokens": number(usage.get("output_tokens", usage.get("outputTokens")), True),
            "listCostUsd": number(meta.get("total_cost_usd", meta.get("cost_usd"))), "elapsedMilliseconds": elapsed, "toolsUsed": False}


def main():
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in MODELS: raise Failure("Choose one native family")
        data = request(sys.stdin.buffer.read(MAX_INPUT + 1)); family = sys.argv[1]
        argv, payload = route(family, **data)
        raw, elapsed = run_child(argv, payload, data["milliseconds"], family)
        result = parse_output(raw, family, elapsed)
        print(json.dumps(result, allow_nan=False))
        return 0
    except Failure as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
    except Exception:
        print(json.dumps({"error": "Native client invocation failed"}), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
