import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arena.canonical import GENESIS, chain  # noqa: E402
from arena.isolation import (  # noqa: E402
    ISOLATION_SCHEMA,
    IsolationRequirementError,
    resolve_isolation,
    validate_isolation_profile,
)
from arena.match import run_match  # noqa: E402
from arena.replay import verify  # noqa: E402
from arena.transcript import first, load  # noqa: E402


def entrant(script):
    return {
        "name": Path(script).stem.replace("_", "-"),
        "cmd": [
            sys.executable,
            str(ROOT / "entrants" / script),
            "--backend",
            "stub:v1",
        ],
        "env": [],
        "claimed_model": "stub:v1",
    }


def rechain(path, mutate):
    records = load(path)
    mutate(records)
    previous = GENESIS
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for index, record in enumerate(records):
            body = {
                "kind": record["kind"],
                "seq": index,
                "body": record["body"],
            }
            digest = chain(previous, body)
            line = {**body, "prev": previous, "hash": digest}
            handle.write(
                json.dumps(
                    line,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n"
            )
            previous = digest


def legacy_policy():
    return {
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
        "note": "legacy process policy",
    }


class IsolationProfileTests(unittest.TestCase):
    def test_process_profile_is_explicitly_not_capability_isolated(self):
        profile = resolve_isolation()
        self.assertEqual(profile["schema"], ISOLATION_SCHEMA)
        self.assertEqual(profile["mode"], "process")
        self.assertIs(profile["capability_isolation"], False)
        self.assertIs(profile["trusted_entrants_only"], True)
        self.assertTrue(all(profile["enforced"].values()))
        self.assertTrue(all(value is False for value in profile["unenforced"].values()))
        self.assertIn("capability-unconfined", profile["claim"])

    def test_capability_requirement_fails_closed(self):
        with self.assertRaises(IsolationRequirementError) as caught:
            resolve_isolation(require_capability_isolation=True)
        receipt = caught.exception.to_json()
        self.assertEqual(receipt["error"], "isolation_requirement_unsatisfied")
        self.assertIs(receipt["match_started"], False)
        self.assertIs(receipt["required"]["capability_isolation"], True)
        self.assertIs(receipt["available"]["capability_isolation"], False)

    def test_unknown_mode_never_falls_back_to_process(self):
        with self.assertRaises(IsolationRequirementError) as caught:
            resolve_isolation(mode="docker")
        self.assertEqual(caught.exception.requested_mode, "docker")
        self.assertIn("not implemented", caught.exception.reason)

    def test_false_process_capability_claim_is_rejected(self):
        forged = resolve_isolation()
        forged["capability_isolation"] = True
        with self.assertRaisesRegex(ValueError, "capability_isolation"):
            validate_isolation_profile(forged)

    def test_deleted_unenforced_control_is_rejected(self):
        forged = resolve_isolation()
        del forged["unenforced"]["host_credential_boundary"]
        with self.assertRaisesRegex(ValueError, "fields are not exact"):
            validate_isolation_profile(forged)

    def test_invented_control_is_rejected(self):
        forged = resolve_isolation()
        forged["enforced"]["magic_hypervisor_boundary"] = True
        with self.assertRaisesRegex(ValueError, "unknown"):
            validate_isolation_profile(forged)


class IsolationAdmissionTests(unittest.TestCase):
    def test_strict_api_preflight_has_zero_match_side_effects(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "must-not-exist"
            with self.assertRaises(IsolationRequirementError):
                run_match(
                    game_name="nim",
                    seed=7,
                    entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
                    out_dir=out,
                    require_capability_isolation=True,
                )
            self.assertFalse(out.exists())

    def test_strict_cli_refusal_is_bounded_json_and_creates_no_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "must-not-exist"
            command = [
                sys.executable,
                str(ROOT / "bin" / "run_match.py"),
                "--seed",
                "7",
                "--entrant",
                str(ROOT / "entrants" / "solver_harness.py"),
                "--entrant",
                str(ROOT / "entrants" / "naive_harness.py"),
                "--out",
                str(out),
                "--require-capability-isolation",
            ]
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=30,
            )
            self.assertEqual(result.returncode, 2)
            refusal = json.loads(result.stderr)
            self.assertEqual(refusal["error"], "isolation_requirement_unsatisfied")
            self.assertIs(refusal["match_started"], False)
            self.assertEqual(result.stdout, "")
            self.assertFalse(out.exists())

    def test_process_match_binds_profile_and_still_replay_verifies(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_match(
                game_name="nim",
                seed=7,
                entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
                out_dir=temporary,
            )
            self.assertIs(result["isolation"]["capability_isolation"], False)
            records = load(result["transcript"])
            header = first(records, "header")["body"]
            self.assertEqual(header["isolation"], result["isolation"])
            self.assertNotIn("sandbox_policy", header)
            report = verify(result["transcript"])
            self.assertEqual(report["verdict"], "PASS")
            self.assertIs(report["isolation_profile_ok"], True)
            self.assertTrue(
                any("capability-unconfined" in item for item in report["does_not_prove"])
            )

    def test_same_process_match_remains_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            first_result = run_match(
                game_name="nim",
                seed=41,
                entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
                out_dir=os.path.join(temporary, "one"),
            )
            second_result = run_match(
                game_name="nim",
                seed=41,
                entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
                out_dir=os.path.join(temporary, "two"),
            )
            self.assertEqual(first_result["chain_head"], second_result["chain_head"])
            self.assertEqual(
                Path(first_result["transcript"]).read_bytes(),
                Path(second_result["transcript"]).read_bytes(),
            )


class IsolationReplayTests(unittest.TestCase):
    def _match(self, directory):
        return run_match(
            game_name="nim",
            seed=73,
            entrants=[entrant("solver_harness.py"), entrant("naive_harness.py")],
            out_dir=directory,
        )

    def test_rechained_false_capability_claim_fails_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self._match(temporary)
            rechain(
                result["transcript"],
                lambda records: records[0]["body"]["isolation"].__setitem__(
                    "capability_isolation", True
                ),
            )
            report = verify(result["transcript"])
            self.assertEqual(report["verdict"], "FAIL")
            self.assertIs(report["chain_ok"], True)
            self.assertIs(report["isolation_profile_ok"], False)
            self.assertTrue(any("isolation_profile" in error for error in report["errors"]))

    def test_rechained_deleted_limitation_fails_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self._match(temporary)

            def delete_limit(records):
                del records[0]["body"]["isolation"]["unenforced"]["network_egress_blocking"]

            rechain(result["transcript"], delete_limit)
            report = verify(result["transcript"])
            self.assertEqual(report["verdict"], "FAIL")
            self.assertIs(report["chain_ok"], True)
            self.assertIs(report["isolation_profile_ok"], False)

    def test_ambiguous_current_and_legacy_declarations_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self._match(temporary)
            rechain(
                result["transcript"],
                lambda records: records[0]["body"].__setitem__(
                    "sandbox_policy", legacy_policy()
                ),
            )
            report = verify(result["transcript"])
            self.assertEqual(report["verdict"], "FAIL")
            self.assertIn("both current and legacy", " ".join(report["errors"]))

    def test_complete_legacy_policy_remains_verifiable_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self._match(temporary)
            legacy_path = Path(temporary) / "legacy.jsonl"
            shutil.copy(result["transcript"], legacy_path)

            def downgrade(records):
                header = records[0]["body"]
                del header["isolation"]
                header["sandbox_policy"] = legacy_policy()

            rechain(legacy_path, downgrade)
            report = verify(legacy_path)
            self.assertEqual(report["verdict"], "PASS")
            self.assertEqual(
                report["isolation"]["source"],
                "legacy-sandbox-policy",
            )
            self.assertIs(report["isolation"]["capability_isolation"], False)

    def test_legacy_policy_missing_a_caveat_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self._match(temporary)

            def malformed_legacy(records):
                header = records[0]["body"]
                del header["isolation"]
                policy = legacy_policy()
                policy["unenforced_v1"] = [
                    item
                    for item in policy["unenforced_v1"]
                    if not item.startswith("network_egress_blocking")
                ]
                header["sandbox_policy"] = policy

            rechain(result["transcript"], malformed_legacy)
            report = verify(result["transcript"])
            self.assertEqual(report["verdict"], "FAIL")
            self.assertIs(report["isolation_profile_ok"], False)
            self.assertIn("omits capability limitations", " ".join(report["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
