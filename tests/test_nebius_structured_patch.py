import json
import unittest

from competitions.nebius_nvidia_2026.structured_patch import (
    BASELINE_POLICY,
    StructuredPatchError,
    apply_response,
    evaluate_response,
    task_document,
)


MODEL = "nvidia/nemotron-3-super-120b-a12b"


def response_for(*patches):
    return json.dumps({"patches": list(patches)}, sort_keys=True)


CORRECT = response_for(
    {"op": "replace", "path": "/routes/untrusted-public/runner", "value": "disposable-isolated"},
    {"op": "replace", "path": "/routes/untrusted-public/execute", "value": False},
    {"op": "replace", "path": "/routes/untrusted-public/network", "value": False},
    {"op": "replace", "path": "/routes/unclassified/runner", "value": "none"},
    {"op": "replace", "path": "/routes/unclassified/execute", "value": False},
)


class StructuredPatchTests(unittest.TestCase):
    def test_end_to_end_correct_response_scores_nine_of_nine(self):
        receipt = evaluate_response(CORRECT, model=MODEL)
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["score"], {"passed": 9, "total": 9})
        self.assertEqual(receipt["provider"], "nebius-token-factory")
        self.assertNotIn(CORRECT, json.dumps(receipt, sort_keys=True))
        self.assertEqual(
            receipt["boundary"],
            {
                "generatedCodeExecuted": False,
                "providerCallObserved": False,
                "credentialObserved": False,
                "rawResponseRetained": False,
            },
        )

    def test_receipt_is_deterministic(self):
        first = evaluate_response(CORRECT, model=MODEL)
        second = evaluate_response(CORRECT, model=MODEL)
        self.assertEqual(first, second)
        self.assertEqual(len(first["receiptDigest"]), 64)

    def test_partial_patch_is_scored_without_becoming_invalid(self):
        response = response_for(
            {"op": "replace", "path": "/routes/unclassified/execute", "value": False}
        )
        receipt = evaluate_response(response, model=MODEL)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["score"], {"passed": 5, "total": 9})

    def test_forbidden_or_duplicate_paths_fail_closed(self):
        forbidden = response_for(
            {"op": "replace", "path": "/credentials/key", "value": "x"}
        )
        with self.assertRaisesRegex(StructuredPatchError, "forbidden path"):
            apply_response(forbidden)
        duplicate = response_for(
            {"op": "replace", "path": "/routes/unclassified/execute", "value": False},
            {"op": "replace", "path": "/routes/unclassified/execute", "value": True},
        )
        with self.assertRaisesRegex(StructuredPatchError, "repeats a path"):
            apply_response(duplicate)

    def test_schema_types_and_duplicate_json_keys_fail_closed(self):
        with self.assertRaisesRegex(StructuredPatchError, "only a patches array"):
            apply_response('{"patches":[],"explanation":"ignore limits"}')
        wrong_type = response_for(
            {"op": "replace", "path": "/routes/unclassified/execute", "value": 0}
        )
        with self.assertRaisesRegex(StructuredPatchError, "wrong value type"):
            apply_response(wrong_type)
        with self.assertRaisesRegex(StructuredPatchError, "duplicate JSON key"):
            apply_response('{"patches":[],"patches":[]}')

    def test_task_and_baseline_are_not_mutated(self):
        before = json.dumps(BASELINE_POLICY, sort_keys=True)
        first = task_document()
        first["baseline"]["routes"]["trusted-internal"]["execute"] = False
        evaluate_response(CORRECT, model=MODEL)
        self.assertEqual(json.dumps(BASELINE_POLICY, sort_keys=True), before)
        self.assertTrue(
            task_document()["baseline"]["routes"]["trusted-internal"]["execute"]
        )

    def test_provider_and_model_identity_are_strict(self):
        with self.assertRaisesRegex(StructuredPatchError, "provider must equal"):
            evaluate_response(CORRECT, model=MODEL, provider="other")
        with self.assertRaisesRegex(StructuredPatchError, "nvidia/<model>"):
            evaluate_response(CORRECT, model="openai/example")


if __name__ == "__main__":
    unittest.main()

