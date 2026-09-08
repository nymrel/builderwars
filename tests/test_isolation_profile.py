import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from arena.isolation import IsolationRequirementError, resolve_isolation
from arena.match import run_reference_match
from arena.replay import verify

ROOT = Path(__file__).resolve().parents[1]


def entrant(name):
    return {
        "name": name,
        "cmd": [sys.executable, str(ROOT / "entrants" / f"{name}_harness.py"), "--backend", "stub:v1"],
        "env": [],
        "claimed_model": "stub:v1",
        "execution_claim": "scripted",
    }


def test_capability_requirement_refuses_before_output():
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "must-not-exist"
        with pytest.raises(IsolationRequirementError) as caught:
            run_reference_match(game_name="nim", seed=7, entrants=[entrant("solver"), entrant("naive")], out_dir=out, require_capability_isolation=True)
        assert caught.value.to_json()["match_started"] is False
        assert not out.exists()


def test_process_receipt_is_bound_and_replay_validates_profile():
    with tempfile.TemporaryDirectory() as directory:
        result = run_reference_match(game_name="nim", seed=7, entrants=[entrant("solver"), entrant("naive")], out_dir=directory)
        assert result["isolation"]["capability_isolation"] is False
        report = verify(result["transcript"])
        assert report["verdict"] == "PASS"
        assert report["isolation_profile_ok"] is True


def test_cli_refusal_is_bounded_json_without_output():
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "must-not-exist"
        process = subprocess.run([sys.executable, str(ROOT / "bin" / "run_match.py"), "--seed", "7", "--entrant", str(ROOT / "entrants" / "solver_harness.py"), "--entrant", str(ROOT / "entrants" / "naive_harness.py"), "--out", str(out), "--require-capability-isolation"], cwd=ROOT, text=True, capture_output=True, check=False)
        assert process.returncode == 2
        assert json.loads(process.stderr)["match_started"] is False
        assert not out.exists()
