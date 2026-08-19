import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
        with self.assertRaisesRegex(ValueError, "may not claim capability isolation"):
            validate_isolation_profile(forged)

    def test_control_overlap_is_rejected(self):
        forged = resolve_isolation()
        forged["unenforced"]["separate_process"] = False
        with self.assertRaisesRegex(ValueError, "both enforced and unenforced"):
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
            self.assertEqual(verify(result["transcript"])["verdict"], "PASS")

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
