import subprocess
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from android_emulator_smoke import app_socket, run, wait_for, prepare_debug, recovery_snapshot


TEMPORARY_ERROR = {
    "code": "OS-PLUG-FILE-0013",
    "message": "'readdir' failed with: /data/user/0/com.nymrel.builderwars/files/"
               "builderwars-checkpoints-v1/checkpoint-12-9930e9fb-638f-48a6-9a72-803c9c3a286d.json.part",
}
COMMITTED_NAME = "checkpoint-12-9930e9fb-638f-48a6-9a72-803c9c3a286d.json"


class SnapshotScriptPage:
    """Execute the helper's actual injected JavaScript with a controlled native port."""
    def __init__(self, **scenario):
        self.scenario = scenario

    def evaluate(self, expression):
        driver = r"""
            import { readFileSync } from 'node:fs';
            const { expression, scenario } = JSON.parse(readFileSync(0, 'utf8'));
            const calls = [];
            const committed = 'checkpoint-12-9930e9fb-638f-48a6-9a72-803c9c3a286d.json';
            const old = 'checkpoint-11-9930e9fb-638f-48a6-9a72-803c9c3a286d.json';
            const part = 'checkpoint-13-9930e9fb-638f-48a6-9a72-803c9c3a286d.json.part';
            const envelope = JSON.stringify({payload: JSON.stringify({
                'builderwars.match.v1:own': JSON.stringify({record: {events: [{}, {}]}}),
                'builderwars.match.v1:completed': JSON.stringify({record: {events: Array(7).fill({})}}),
                'irrelevant-private-field': 'never include in a diagnostic result',
            })});
            let listing = 0;
            const fail = details => { throw Object.assign(new Error(details.message), details); };
            const fs = new Proxy({
                async readdir(options) {
                    calls.push({operation: 'readdir', options});
                    const error = (scenario.listErrors ?? [])[listing++];
                    if (error) fail(error);
                    return {files: (scenario.files ?? [old, part, committed]).map(name => ({name}))};
                },
                async readFile(options) {
                    calls.push({operation: 'readFile', options});
                    if (scenario.readError) fail(scenario.readError);
                    return {data: scenario.data ?? envelope};
                },
            }, {
                get(target, key) {
                    if (!(key in target)) throw Error('Unexpected filesystem operation: ' + String(key));
                    return target[key];
                },
            });
            globalThis.window = {Capacitor: {Plugins: {Filesystem: fs}}};
            globalThis.document = {
                querySelector: () => ({textContent: '2'}),
                querySelectorAll: () => [{}],
            };
            globalThis.setTimeout = globalThis.setInterval = () => { throw Error('Snapshot added a timer wait'); };
            let outcome;
            try { outcome = {value: await (0, eval)(expression)()}; }
            catch (error) { outcome = {error: {name: error.name, message: error.message, code: error.code ?? null}}; }
            process.stdout.write(JSON.stringify({...outcome, calls}));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", driver],
            input=json.dumps({"expression": expression, "scenario": self.scenario}),
            capture_output=True, text=True, check=True, timeout=10,
        )
        return json.loads(result.stdout)


class AndroidHarnessTests(unittest.TestCase):
    def test_overlay_is_debug_only_and_leaves_main_unchanged(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                source = Path("android/app/src/main/assets/capacitor.config.json")
                source.parent.mkdir(parents=True)
                config = {"android": {"webContentsDebuggingEnabled": False}, "server": {"hostname": "localhost"}}
                source.write_text(json.dumps(config))
                before = source.read_bytes()
                prepare_debug()
                self.assertEqual(source.read_bytes(), before)
                debug = json.loads(Path("android/app/src/debug/assets/capacitor.config.json").read_text())
                self.assertTrue(debug["android"]["webContentsDebuggingEnabled"])
                self.assertFalse(Path("android/app/src/release").exists())
                config["server"]["url"] = "https://unexpected.example"
                source.write_text(json.dumps(config))
                with self.assertRaises(RuntimeError):
                    prepare_debug()
            finally:
                os.chdir(previous)

    def test_socket_is_bound_to_exact_app_pid(self):
        self.assertEqual(app_socket("123", "000 00 @webview_devtools_remote_123"), "webview_devtools_remote_123")
        self.assertIsNone(app_socket("123", "000 00 @webview_devtools_remote_1234"))
        for pid in ("", "123 456", "0", "123;kill"):
            with self.assertRaises(RuntimeError):
                app_socket(pid, "")

    def test_commands_never_answer_license_prompts(self):
        with patch("android_emulator_smoke.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "ok", "")) as command:
            self.assertEqual(run("sdkmanager", "--install", "emulator"), "ok")
        self.assertEqual(command.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(command.call_args.kwargs["timeout"], 60)

    def test_readiness_timeout_is_failure_not_success(self):
        with patch("android_emulator_smoke.time.monotonic", side_effect=[0, 2]):
            with self.assertRaises(TimeoutError):
                wait_for(lambda: False, seconds=1)

    def test_snapshot_retries_only_enumeration_and_reads_latest_committed_counts(self):
        for failures in (0, 1, 2):
            with self.subTest(failures=failures):
                result = recovery_snapshot(SnapshotScriptPage(listErrors=[TEMPORARY_ERROR] * failures))
                self.assertEqual(result.get("value"), {
                    "storageBackend": "native-checkpoint", "visiblePlies": "2",
                    "storedEntries": [{"plies": 2}, {"plies": 7}], "resumableEntries": 1,
                })
                self.assertEqual([call["operation"] for call in result["calls"]],
                                 ["readdir"] * (failures + 1) + ["readFile"])
                self.assertEqual(result["calls"][-1]["options"], {
                    "path": "builderwars-checkpoints-v1/" + COMMITTED_NAME,
                    "directory": "DATA", "encoding": "utf8",
                })

    def test_snapshot_persistent_temporary_error_fails_after_three_attempts(self):
        result = recovery_snapshot(SnapshotScriptPage(listErrors=[TEMPORARY_ERROR] * 4))
        self.assertEqual(result["error"]["message"], TEMPORARY_ERROR["message"])
        self.assertEqual(result["error"]["code"], TEMPORARY_ERROR["code"])
        self.assertEqual([call["operation"] for call in result["calls"]], ["readdir"] * 3)
        self.assertNotIn("value", result)

    def test_snapshot_other_enumeration_errors_fail_without_retry(self):
        original = TEMPORARY_ERROR["message"]
        cases = [
            {**TEMPORARY_ERROR, "code": "OS-PLUG-FILE-0007"},
            {"message": original},
            {**TEMPORARY_ERROR, "message": original.removesuffix(".part")},
            {**TEMPORARY_ERROR, "message": original.replace("'readdir'", "'readFile'")},
            {**TEMPORARY_ERROR, "message": original.replace("com.nymrel.builderwars", "another.app")},
            {**TEMPORARY_ERROR, "message": original.replace("builderwars-checkpoints-v1/", "other-directory/")},
            {**TEMPORARY_ERROR, "message": original.replace("checkpoint-12-", "checkpoint-0-")},
            {**TEMPORARY_ERROR, "message": original + "\n"},
            {"code": "OS-PLUG-FILE-0013", "message": "Permission denied"},
        ]
        for error in cases:
            with self.subTest(error=error):
                result = recovery_snapshot(SnapshotScriptPage(listErrors=[error]))
                self.assertEqual(result["error"]["message"], error["message"])
                self.assertEqual([call["operation"] for call in result["calls"]], ["readdir"])
                self.assertNotIn("value", result)

    def test_snapshot_stops_on_unrelated_error_after_recognized_race(self):
        error = {"code": "OS-PLUG-FILE-0007", "message": "Permission denied"}
        result = recovery_snapshot(SnapshotScriptPage(listErrors=[TEMPORARY_ERROR, error]))
        self.assertEqual(result["error"]["message"], error["message"])
        self.assertEqual([call["operation"] for call in result["calls"]], ["readdir", "readdir"])

    def test_snapshot_read_failure_is_not_retried_even_with_matching_error_text(self):
        result = recovery_snapshot(SnapshotScriptPage(readError=TEMPORARY_ERROR))
        self.assertEqual(result["error"]["message"], TEMPORARY_ERROR["message"])
        self.assertEqual([call["operation"] for call in result["calls"]], ["readdir", "readFile"])
        self.assertNotIn("value", result)

    def test_snapshot_missing_or_malformed_committed_data_remains_failure(self):
        cases = [
            ({"files": []}, "Error", ["readdir"]),
            ({"data": "{"}, "SyntaxError", ["readdir", "readFile"]),
            ({"data": json.dumps({"payload": "{"})}, "SyntaxError", ["readdir", "readFile"]),
            ({"data": json.dumps({"payload": "null"})}, "TypeError", ["readdir", "readFile"]),
        ]
        for scenario, error_name, operations in cases:
            with self.subTest(scenario=scenario):
                result = recovery_snapshot(SnapshotScriptPage(**scenario))
                self.assertEqual(result["error"]["name"], error_name)
                self.assertEqual([call["operation"] for call in result["calls"]], operations)
                self.assertNotIn("value", result)


if __name__ == "__main__":
    unittest.main()
