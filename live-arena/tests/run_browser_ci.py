"""Bounded, credential-free browser gate. Existing journeys run unchanged in children.

Browser HTTP/WS requests not intercepted by a synthetic test are denied outside
our preview origin. Real PeerJS signaling/recovery.py and customer-client smoke
remain separate integration gates; this runner does not simulate their success.
"""
import argparse
import os
from pathlib import Path
import runpy
import signal
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
JOURNEYS = ("browser.py", "lifecycle.py", "connections_browser.py", "profiles_browser.py", "academy_browser.py", "proof_browser.py", "sharing_browser.py")


def restrict_browser_network():
    from playwright.sync_api import Browser
    origin = urlsplit(os.environ["BUILDERWARS_TEST_URL"])
    original_context, original_page = Browser.new_context, Browser.new_page
    configured = set()

    def guard(context):
        if context in configured:
            return
        configured.add(context)

        def route(request):
            target = urlsplit(request.request.url)
            if (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
                request.continue_()
            else:
                request.abort("blockedbyclient")
        context.route("**/*", route)
        context.route_web_socket("**/*", lambda ws: ws.close())

    def new_context(self, *args, **kwargs):
        kwargs["service_workers"] = "block"
        context = original_context(self, *args, **kwargs)
        guard(context)
        return context

    def new_page(self, *args, **kwargs):
        kwargs["service_workers"] = "block"
        page = original_page(self, *args, **kwargs)
        guard(page.context)
        return page

    Browser.new_context, Browser.new_page = new_context, new_page


def launch(command, env):
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    return subprocess.Popen(command, cwd=ROOT, env=env, **options)


def stop_owned(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
    else:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def run(command, env):
    process = launch(command, env)
    try:
        code = process.wait(timeout=180)
        if code:
            raise subprocess.CalledProcessError(code, command)
    finally:
        stop_owned(process)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", choices=JOURNEYS)
    args = parser.parse_args()
    if args.child:
        restrict_browser_network()
        runpy.run_path(str(ROOT / "tests" / args.child), run_name="__main__")
        return
    if not (ROOT / "dist" / "index.html").is_file():
        raise RuntimeError("Build the production candidate before browser validation.")
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", 0))
        port = port_probe.getsockname()[1]
    env = {**os.environ, "BUILDERWARS_TEST_URL": f"http://127.0.0.1:{port}", "BUILDERWARS_BROWSER": "chromium"}
    preview = launch(["node", "node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", str(port), "--strictPort"], env)
    try:
        deadline = time.monotonic() + 20
        while True:
            if preview.poll() is not None:
                raise RuntimeError("Owned preview exited before readiness.")
            try:
                with urlopen(env["BUILDERWARS_TEST_URL"], timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError("Preview readiness timed out.")
            time.sleep(0.1)
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_bridge.py"], env)
        for script in JOURNEYS:
            print(f"GATE Chromium: {script}", flush=True)
            run([sys.executable, __file__, "--child", script], env)
        for engine in ("firefox", "webkit"):
            print(f"GATE {engine}: proof_browser.py", flush=True)
            run([sys.executable, __file__, "--child", "proof_browser.py"], {**env, "BUILDERWARS_BROWSER": engine})
        print("PASS: isolated browser gate. Real PeerJS recovery and customer-client execution excluded, not certified.", flush=True)
    finally:
        stop_owned(preview)


if __name__ == "__main__":
    main()
