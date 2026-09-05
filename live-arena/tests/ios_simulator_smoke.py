"""Launch the built app on one preinstalled CI simulator; no signing or stores.

Screenshots require human/model inspection. Launch success is not interaction,
physical-device, provider, accessibility, or store proof.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import time


def run(*args, timeout=60):
    print(f"Running {' '.join(args[:3])} (limit {timeout}s)", flush=True)
    try:
        return subprocess.run(args, check=True, text=True, capture_output=True, timeout=timeout).stdout.strip()
    except subprocess.CalledProcessError as error:
        print((error.stderr or "")[-3000:], flush=True)
        raise


def select_device(inventory):
    for runtime, devices in sorted(inventory.get("devices", {}).items(), reverse=True):
        if "iOS" not in runtime:
            continue
        for device in devices:
            if (device.get("isAvailable") is True and device.get("state") == "Shutdown"
                    and str(device.get("name", "")).startswith("iPhone")
                    and re.fullmatch(r"[0-9A-Fa-f-]{36}", str(device.get("udid", "")))):
                return runtime, device
    raise RuntimeError("No available shutdown iPhone simulator; no runtime download attempted.")


def cleanup(udid):
    try:
        subprocess.run(["xcrun", "simctl", "terminate", udid, "com.nymrel.builderwars"],
                       capture_output=True, timeout=30)
    finally:
        # A terminate timeout must not skip shutdown of the owned simulator.
        run("xcrun", "simctl", "shutdown", udid, timeout=60)


def main():
    app = Path(".native-build/Build/Products/Debug-iphonesimulator/App.app").resolve()
    if not app.is_dir():
        raise RuntimeError("Build the unsigned simulator app first.")
    out = Path("output/playwright/native-ios")
    out.mkdir(parents=True, exist_ok=True)
    runtime, device = select_device(json.loads(run("xcrun", "simctl", "list", "devices", "available", "--json")))
    udid = device["udid"]
    receipt = {
        "schema": "builderwars.ios-simulator-launch.v1",
        "sourceHead": os.environ.get("SOURCE_HEAD", "unreported"),
        "builtCheckout": run("git", "rev-parse", "HEAD"),
        "runtime": runtime, "device": device["name"], "udid": udid,
        "status": "started", "launch": None, "screenshot": None,
        "classification": "unsigned simulator launch attempt; no user-flow proof",
        "physicalDeviceTested": False, "userFlowsTested": False, "storeSubmitted": False,
    }
    print(json.dumps(receipt), flush=True)
    attempted_boot = False
    try:
        # Exact UUID only; never boot/shutdown all simulators or alter an active device.
        attempted_boot = True
        run("xcrun", "simctl", "boot", udid)
        run("xcrun", "simctl", "bootstatus", udid, "-b", timeout=180)
        run("xcrun", "simctl", "install", udid, str(app), timeout=180)
        launched = run("xcrun", "simctl", "launch", udid, "com.nymrel.builderwars")
        if not re.fullmatch(r"com\.nymrel\.builderwars: [0-9]+", launched):
            raise RuntimeError("Unexpected launch receipt; refusing to infer successful launch.")
        time.sleep(8)  # Bounded rendering delay; screenshots are inspected, not an assertion.
        run("xcrun", "simctl", "io", udid, "screenshot", str(out / "launch.png"))
        receipt.update(status="launched", launch=launched, screenshot="launch.png",
                       classification="unsigned simulator launch; screenshot inspection required")
        print(json.dumps(receipt))
    except Exception as error:
        receipt.update(status="failed", error=type(error).__name__)
        raise
    finally:
        try:
            if attempted_boot:
                # The runner is ephemeral; cleanup targets only the exact device selected above.
                cleanup(udid)
        finally:
            (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
