"""Real debug APK/WebView journey on one disposable CI AVD, not device/store proof.

Uses installed SDK licenses only: sdkmanager receives closed stdin, never `yes` or
--licenses. No account, model provider, mock bridge, or release signing is used.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import zipfile

PACKAGE = "com.nymrel.builderwars"
SERIAL = "emulator-5556"
CDP_PORT = 9223
IMAGE = "system-images;android-35;google_apis;x86_64"


def recovery_snapshot(page):
    """Counts only: never export stored prompts, endpoints, keys or record bodies."""
    return page.evaluate("""async () => {
        const entries = [];
        const fs = window.Capacitor.Plugins.Filesystem;
        const path = 'builderwars-checkpoints-v1';
        const files = (await fs.readdir({path, directory:'DATA'})).files
            .filter(f => /^checkpoint-[1-9][0-9]*-[a-f0-9-]{36}\\.json$/.test(f.name))
            .sort((a,b) => Number(b.name.split('-')[1]) - Number(a.name.split('-')[1]));
        if (!files.length) throw Error('No committed native checkpoint');
        const envelope = JSON.parse((await fs.readFile({path:path+'/'+files[0].name, directory:'DATA', encoding:'utf8'})).data);
        const values = JSON.parse(envelope.payload);
        for (const key of Object.keys(values)) {
            if (!key?.startsWith('builderwars.match.v1:')) continue;
            try {
                const entry = JSON.parse(values[key]);
                entries.push({plies: Array.isArray(entry?.record?.events)
                    ? entry.record.events.length : null});
            } catch { entries.push({plies: null}); }
        }
        return {storageBackend:'native-checkpoint', visiblePlies: document.querySelector('#metric-moves')?.textContent,
            storedEntries: entries.sort((a, b) => (a.plies ?? -1) - (b.plies ?? -1)),
            resumableEntries: document.querySelectorAll('[data-saved-resume]').length};
    }""")


def prepare_debug():
    # Android's debug source-set asset overrides main only for debug builds.
    # Keep the committed/release config disabled; never enable a remote server.
    config = json.loads(Path("android/app/src/main/assets/capacitor.config.json").read_text())
    if config.get("server", {}).get("url") or config.get("android", {}).get("webContentsDebuggingEnabled") is not False:
        raise RuntimeError("Unexpected production config; refusing debug overlay")
    config["android"]["webContentsDebuggingEnabled"] = True
    target = Path("android/app/src/debug/assets/capacitor.config.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, indent=2), encoding="utf-8")


def run(*args, timeout=60, env=None):
    result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=timeout, env=env)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args[:3]}\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
    return result.stdout.strip()


def wait_for(check, seconds=90):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (RuntimeError, subprocess.TimeoutExpired):
            pass
        time.sleep(1)
    raise TimeoutError("Bounded Android readiness check expired")


def app_socket(pid, inventory):
    if not re.fullmatch(r"[1-9][0-9]*", pid):
        raise RuntimeError("Expected one exact app PID")
    expected = f"webview_devtools_remote_{pid}"
    if not any(line.split()[-1:] == ["@" + expected] for line in inventory.splitlines()):
        return None
    return expected


def main():
    from playwright.sync_api import sync_playwright, expect
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.name == "nt":
        raise RuntimeError("This owner-scoped fixture runs only on a disposable Linux CI runner")
    sdk = Path(os.environ["ANDROID_HOME"])
    apk = Path("android/app/build/outputs/apk/debug/app-debug.apk").resolve()
    if not apk.is_file():
        raise RuntimeError("Build debug APK first")
    with zipfile.ZipFile(apk) as archive:
        config = json.loads(archive.read("assets/capacitor.config.json"))
        if config.get("android", {}).get("webContentsDebuggingEnabled") is not True or config.get("server", {}).get("url"):
            raise RuntimeError("APK does not contain the isolated debug inspection overlay")
        assets = Path("dist-native")
        if not (assets / "index.html").is_file():
            raise RuntimeError("Missing native build assets")
        for asset in assets.rglob("*"):
            if asset.is_file() and archive.read("assets/public/" + asset.relative_to(assets).as_posix()) != asset.read_bytes():
                raise RuntimeError("APK content differs from the built native assets")
    out = Path("output/playwright/native-android").resolve()
    out.mkdir(parents=True, exist_ok=True)
    receipt = {"schema": "builderwars.android-emulator-journey.v1",
               "sourceHead": os.environ.get("SOURCE_HEAD", "unreported"),
               "builtCheckout": run("git", "rev-parse", "HEAD"),
               "apkSha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
               "image": IMAGE, "serial": SERIAL, "stages": [], "status": "started", "recoveryTrace": {},
               "physicalDeviceTested": False, "storeSubmitted": False,
               "debugOnlyInspectionOverlay": True,
               "packagedAssetsMatchBuild": True,
               "classification": "debug APK; actual Android WebView input via CDP; no physical touch or provider proof"}
    emulator = None
    log = None
    adb = str(sdk / "platform-tools/adb")
    def device(*args, **kwargs):
        return run(adb, "-s", SERIAL, *args, **kwargs)
    def screenshot(name):
        result = subprocess.run([adb, "-s", SERIAL, "exec-out", "screencap", "-p"],
                                capture_output=True, check=True, timeout=30)
        if not result.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("Invalid Android screenshot")
        (out / name).write_bytes(result.stdout)
    try:
        # Refuse occupied ports/serials; never attach to or clear another device.
        for port in (5556, 5557, CDP_PORT):
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
        if SERIAL in run(adb, "devices"):
            raise RuntimeError("Reserved emulator serial already exists")
        manager = sdk / "cmdline-tools/latest/bin/sdkmanager"
        run(str(manager), "--install", "emulator", IMAGE, timeout=240)
        receipt["stages"].append("sdk-installed-without-license-acceptance")
        with tempfile.TemporaryDirectory(prefix="builderwars-avd-") as avd_dir:
            env = dict(os.environ, ANDROID_AVD_HOME=avd_dir)
            run(str(sdk / "cmdline-tools/latest/bin/avdmanager"), "create", "avd",
                "-n", "builderwars-ci", "-k", IMAGE, "--device", "pixel_6", env=env)
            log = (out / "emulator.log").open("wb")
            emulator = subprocess.Popen([str(sdk / "emulator/emulator"), "-avd", "builderwars-ci",
                "-port", "5556", "-no-window", "-no-audio", "-no-boot-anim", "-no-snapshot",
                "-gpu", "swiftshader_indirect", "-memory", "2048"], env=env, stdout=log, stderr=log)
            try:
                def booted():
                    if emulator.poll() is not None:
                        raise ChildProcessError("Owned emulator exited before boot; inspect emulator.log")
                    return device("shell", "getprop", "sys.boot_completed", timeout=10) == "1"
                wait_for(booted, 180)
                receipt["androidRelease"] = device("shell", "getprop", "ro.build.version.release")
                receipt["stages"].append("booted")
                device("install", str(apk), timeout=120)
                device("shell", "input", "keyevent", "82")
                def launch():
                    device("shell", "am", "start", "-W", "-n", PACKAGE + "/.MainActivity")
                errors, paid_requests = [], []
                def connect(p):
                    def ready():
                        pid = device("shell", "pidof", PACKAGE)
                        return app_socket(pid, device("shell", "cat", "/proc/net/unix"))
                    target = wait_for(ready)
                    device("forward", f"tcp:{CDP_PORT}", "localabstract:" + target)
                    # Keep the actual WebView's download/focus/media defaults.
                    # Android cannot implement desktop Browser.setDownloadBehavior.
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}", no_defaults=True)
                    page = wait_for(lambda: next((pg for c in browser.contexts for pg in c.pages
                                                  if pg.url.startswith("https://localhost")), None))
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("request", lambda request: paid_requests.append(request.url)
                            if request.method == "POST" and not request.url.startswith("https://localhost/") else None)
                    page.locator("#board .cell").first.wait_for()
                    return browser, page
                launch()
                with sync_playwright() as p:
                    browser, page = connect(p)
                    expect(page.locator("#quickplay")).to_have_text("Play free ↗")
                    screenshot("initial.png")
                    page.locator('[data-game="tictactoe"]').click()
                    page.locator("#quickplay").click()
                    expect(page.locator("#match-result")).to_be_visible(timeout=45000)
                    receipt["completedGamePlies"] = int(page.locator("#metric-moves").inner_text())
                    if not 5 <= receipt["completedGamePlies"] <= 9:
                        raise RuntimeError("Expected completed free tic-tac-toe game")
                    screenshot("completed.png")
                    receipt["stages"].append("free-game-completed")
                    page.locator("#reset").click()
                    page.locator("#step").click()
                    expect(page.locator("#metric-moves")).to_have_text("1")
                    page.locator("#step").click()
                    expect(page.locator("#metric-moves")).to_have_text("2")
                    receipt["recoveryTrace"]["afterTwoMoves"] = recovery_snapshot(page)
                    device("shell", "input", "keyevent", "KEYCODE_HOME")
                    expect(page.locator("#match-status")).to_have_text("Paused when app left foreground")
                    launch()
                    expect(page.locator("#notice")).to_contain_text("resumed paused")
                    expect(page.locator("#metric-moves")).to_have_text("2")
                    receipt["recoveryTrace"]["beforeForceStop"] = recovery_snapshot(page)
                    receipt["stages"].append("os-background-resume-paused")
                    device("shell", "am", "force-stop", PACKAGE)
                    browser.close()
                    launch()
                    browser, page = connect(p)
                    expect(page.locator("#metric-moves")).to_have_text("0")
                    receipt["recoveryTrace"]["afterRestart"] = recovery_snapshot(page)
                    page.locator("#match-library summary").click()
                    # Completed quickplay has no resume action; require one paused entry.
                    expect(page.locator("[data-saved-resume]")).to_have_count(1)
                    receipt["recoveryTrace"]["beforeResume"] = recovery_snapshot(page)
                    page.locator("[data-saved-resume]").click()
                    receipt["recoveryTrace"]["afterResume"] = recovery_snapshot(page)
                    expect(page.locator("#metric-moves")).to_have_text("2")
                    expect(page.locator("#start")).to_have_text("▶ Start match")
                    screenshot("recovered.png")
                    receipt["stages"].append("process-restart-recovery-paused")
                    # A diagnostic read before kill can accidentally hide a write race.
                    # Exercise three fresh games with no pre-kill storage probe or sleep.
                    receipt["rapidRestartTrials"] = []
                    for trial in range(3):
                        page.locator("#reset").click()
                        if not page.locator("#match-library").evaluate("e => e.open"):
                            page.locator("#match-library summary").click()
                        # This disposable AVD contains only this test's generated games.
                        page.once("dialog", lambda dialog: dialog.accept())
                        page.locator("#forget-matches").click()
                        expect(page.locator("[data-saved-resume]")).to_have_count(0)
                        if recovery_snapshot(page)["storedEntries"]:
                            raise RuntimeError("Generated trial games were not cleared")
                        page.locator("#save-matches").check()
                        page.locator("#step").click()
                        expect(page.locator("#metric-moves")).to_have_text("1")
                        page.locator("#step").click()
                        expect(page.locator("#metric-moves")).to_have_text("2")
                        restart_path = "foreground" if trial == 1 else "background-resume"
                        if restart_path == "background-resume":
                            # Reproduce the original failing path without storage probes.
                            device("shell", "input", "keyevent", "KEYCODE_HOME")
                            expect(page.locator("#match-status")).to_have_text("Paused when app left foreground")
                            launch()
                            expect(page.locator("#notice")).to_contain_text("resumed paused")
                            expect(page.locator("#metric-moves")).to_have_text("2")
                        device("shell", "am", "force-stop", PACKAGE)
                        browser.close()
                        launch()
                        browser, page = connect(p)
                        trace = {"trial": trial + 1, "path": restart_path, "afterRestart": recovery_snapshot(page)}
                        receipt["rapidRestartTrials"].append(trace)
                        expect(page.locator("#metric-moves")).to_have_text("0")
                        page.locator("#match-library summary").click()
                        expect(page.locator("[data-saved-resume]")).to_have_count(1)
                        page.locator("[data-saved-resume]").click()
                        # Immediate diagnostic sample, not a substitute for the assertion.
                        trace["afterResume"] = recovery_snapshot(page)
                        expect(page.locator("#metric-moves")).to_have_text("2")
                        expect(page.locator("#start")).to_have_text("▶ Start match")
                    receipt["stages"].append("three-rapid-restarts-recovered-paused")
                    if errors or paid_requests:
                        raise RuntimeError(f"Unexpected errors/remote POST: {errors} {paid_requests}")
                    receipt["status"] = "passed"
                    browser.close()
            finally:
                # Scope cleanup to our spawned emulator/process, never all adb devices.
                if emulator is not None:
                    try:
                        device("forward", "--remove", f"tcp:{CDP_PORT}", timeout=10)
                    except (RuntimeError, subprocess.TimeoutExpired):
                        pass
                    try:
                        device("emu", "kill", timeout=15)
                    except (RuntimeError, subprocess.TimeoutExpired):
                        emulator.terminate()
                    try:
                        emulator.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        emulator.kill()
                        emulator.wait(timeout=10)
    except Exception as error:
        receipt.update(status="failed", error=str(error))
        raise
    finally:
        if log is not None:
            log.close()
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["--prepare-debug"]:
        prepare_debug()
    elif sys.argv[1:]:
        raise SystemExit("Usage: android_emulator_smoke.py [--prepare-debug]")
    else:
        main()
