"""Regressions for the new bounded demonstration operator boundary."""

import unittest

from demo_approval import DEMO_ACTION, DemoApprovalGate


class DemoApprovalGateTests(unittest.TestCase):
    def gate(self):
        return DemoApprovalGate(findings_sha256="a" * 64, candidate_sha256="b" * 64)

    def test_no_approval_cannot_restore_fixture(self):
        with self.assertRaisesRegex(PermissionError, "approval is required"):
            self.gate().consume(action=DEMO_ACTION, current_candidate_sha256="b" * 64)

    def test_changed_candidate_cannot_use_prior_approval(self):
        gate = self.gate()
        gate.record_demo_operator_event()
        with self.assertRaisesRegex(PermissionError, "candidate changed"):
            gate.consume(action=DEMO_ACTION, current_candidate_sha256="c" * 64)

    def test_approval_cannot_authorize_other_action(self):
        gate = self.gate()
        gate.record_demo_operator_event()
        with self.assertRaisesRegex(PermissionError, "outside the approved"):
            gate.consume(action="deploy", current_candidate_sha256="b" * 64)

    def test_demo_approval_is_single_use_and_never_claims_a_human(self):
        gate = self.gate()
        event = gate.record_demo_operator_event()
        self.assertFalse(event["human_approval_observed"])
        self.assertFalse(event["production_authority"])
        approved = gate.consume(action=DEMO_ACTION, current_candidate_sha256="b" * 64)
        self.assertEqual(approved.actor, "automated_demo_operator")
        with self.assertRaisesRegex(PermissionError, "already been consumed"):
            gate.consume(action=DEMO_ACTION, current_candidate_sha256="b" * 64)


if __name__ == "__main__":
    unittest.main()
