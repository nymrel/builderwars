import json
import unittest

from competitions.nebius_nvidia_2026.live_report import render_live_receipt_report
from competitions.nebius_nvidia_2026.live_run import provider_prompt, run_live_once


MODEL = "nvidia/nemotron-3-super-120b-a12b"
CORRECT = json.dumps(
    {
        "patches": [
            {"op": "replace", "path": "/routes/untrusted-public/runner", "value": "disposable-isolated"},
            {"op": "replace", "path": "/routes/untrusted-public/execute", "value": False},
            {"op": "replace", "path": "/routes/untrusted-public/network", "value": False},
            {"op": "replace", "path": "/routes/unclassified/runner", "value": "none"},
            {"op": "replace", "path": "/routes/unclassified/execute", "value": False},
        ]
    },
    sort_keys=True,
)


class FakeBackend:
    model = MODEL
    timeout_s = 17

    def __init__(self, response):
        self.response = response
        self.prompts = []

    def complete(self, prompt):
        self.prompts.append(prompt)
        return self.response


class NebiusLiveRunTests(unittest.TestCase):
    def test_prompt_is_exact_json_only_contract(self):
        prompt = provider_prompt()
        self.assertIn("Return exactly one JSON object", prompt)
        self.assertIn('"taskVersion":"nebius-routing-policy-repair.v1"', prompt)

    def test_injected_transport_cannot_masquerade_as_live_provider_proof(self):
        backend = FakeBackend(CORRECT)
        ticks = iter([1_000_000_000, 1_025_000_000])
        receipt = run_live_once(
            model=MODEL,
            backend=backend,
            observed_at="2026-10-07T00:00:00Z",
            clock_ns=lambda: next(ticks),
        )
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["evaluation"]["score"], {"passed": 9, "total": 9})
        self.assertEqual(receipt["durationMs"], 25)
        self.assertFalse(receipt["runtimeEvidence"]["providerCallObserved"])
        self.assertFalse(receipt["runtimeEvidence"]["modelExecutionObservedByRunner"])
        self.assertEqual(receipt["runtimeEvidence"]["transport"], "injected-test-double")
        self.assertNotIn(CORRECT, json.dumps(receipt, sort_keys=True))
        self.assertEqual(len(receipt["receiptDigest"]), 64)
        self.assertEqual(len(backend.prompts), 1)

    def test_invalid_model_output_still_records_hash_only_test_receipt(self):
        receipt = run_live_once(
            model=MODEL,
            backend=FakeBackend("not-json"),
            observed_at="2026-10-07T00:00:00Z",
            clock_ns=lambda: 1,
        )
        self.assertEqual(receipt["status"], "invalid")
        self.assertEqual(receipt["evaluation"]["error"], "StructuredPatchError")
        self.assertNotIn("not-json", json.dumps(receipt, sort_keys=True))

    def test_report_is_script_free_and_preserves_evidence_boundary(self):
        receipt = run_live_once(
            model=MODEL,
            backend=FakeBackend(CORRECT),
            observed_at="2026-10-07T00:00:00Z",
            clock_ns=lambda: 1,
        )
        report = render_live_receipt_report(receipt)
        self.assertIn("Nebius × NVIDIA live run", report)
        self.assertIn("injected-test-double", json.dumps(receipt))
        self.assertIn("runner-observed record", report)
        self.assertIn("default-src 'none'", report)
        self.assertNotIn("<script", report.lower())
        self.assertNotIn(CORRECT, report)


if __name__ == "__main__":
    unittest.main()
