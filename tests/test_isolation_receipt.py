import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arena.isolation import IsolationRequirementError, resolve_isolation  # noqa: E402


class IsolationReceiptTests(unittest.TestCase):
    def test_strict_process_receipt_matches_the_actual_requirement(self):
        with self.assertRaises(IsolationRequirementError) as caught:
            resolve_isolation(
                mode="process",
                require_capability_isolation=True,
            )
        receipt = caught.exception.to_json()
        self.assertEqual(
            receipt["required"],
            {"mode": "process", "capability_isolation": True},
        )
        self.assertEqual(
            receipt["available"],
            {"mode": "process", "capability_isolation": False},
        )
        self.assertIs(receipt["match_started"], False)

    def test_unknown_mode_does_not_invent_a_capability_requirement(self):
        with self.assertRaises(IsolationRequirementError) as caught:
            resolve_isolation(
                mode="docker",
                require_capability_isolation=False,
            )
        receipt = caught.exception.to_json()
        self.assertEqual(
            receipt["required"],
            {"mode": "docker", "capability_isolation": False},
        )
        self.assertEqual(receipt["available_mode"], "process")
        self.assertEqual(receipt["requested_mode"], "docker")
        self.assertIs(receipt["match_started"], False)

    def test_unknown_mode_preserves_an_explicit_capability_requirement(self):
        with self.assertRaises(IsolationRequirementError) as caught:
            resolve_isolation(
                mode="future-jail",
                require_capability_isolation=True,
            )
        receipt = caught.exception.to_json()
        self.assertEqual(
            receipt["required"],
            {"mode": "future-jail", "capability_isolation": True},
        )
        self.assertEqual(
            receipt["available"],
            {"mode": "process", "capability_isolation": False},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
