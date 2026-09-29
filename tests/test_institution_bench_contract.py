from __future__ import annotations
import copy, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from experiments.institution_bench.contract import *  # noqa
D1,D2,D3="1"*64,"2"*64,"3"*64

def role(i,k="worker",ref=None,tools=None,d=False,a=False):
    return {"role_id":i,"role_kind":k,"worker_ref":ref or f"worker:{i}","responsibility":i,"tools":list(tools or ["read"]),"can_delegate":d,"can_adjudicate":a}

def spec(t="single"):
    roles=[role("solo")]
    if t=="lead_worker": roles=[role("lead","lead",tools=["read","write"],d=True),role("worker")]
    if t=="independent_adjudicator": roles=[role("a",ref="worker:a"),role("b",ref="worker:b"),role("judge","adjudicator",ref="worker:judge",a=True)]
    if t=="specialist_team": roles=[role("research","specialist"),role("verify","specialist")]
    return {"schema":EXPERIMENT_SCHEMA,"experiment_id":f"exp:{t}","task":{"task_id":"task:fixture","task_digest":D1,"fixture_digest":D2},"organization":{"organization_id":f"org:{t}","topology":t,"roles":roles,"tool_allowlist":["read","write"],"memory_policy":"reviewed","recovery_policy":{"checkpoint_required":True,"allow_worker_replacement":True,"max_resume_attempts":2}},"budget":{"max_steps":20,"max_tool_calls":30,"max_operator_interventions":2,"max_resource_units":100,"max_elapsed_ms":60000},"evidence_policy":{"require_receipt":True,"require_independent_review":True,"accepted_evidence_classes":["replay_validated","independent_rerun"]},"acceptance":{"acceptance_test_digest":D3,"critical_policy_violations_allowed":0}}

def outcome(**kw):
    x={"accepted":True,"steps":10,"tool_calls":8,"operator_interventions":0,"resource_units":40,"elapsed_ms":5000,"retries":0,"interruptions":0,"resume_attempts":0,"successful_resumes":0,"worker_replacements":0,"duplicate_side_effects":0,"policy_violations":[],"evidence_refs":["receipt:fixture"]}; x.update(kw); return x

class T(unittest.TestCase):
    def test_topologies(self):
        for t in TOPOLOGIES: self.assertEqual(validate_experiment(spec(t))["organization"]["topology"],t)
    def test_unknown_field(self):
        x=spec(); x["x"]=1
        with self.assertRaises(ContractError): validate_experiment(x)
    def test_permission_widening(self):
        x=spec(); x["organization"]["roles"][0]["tools"]=["shell"]
        with self.assertRaisesRegex(ContractError,"permission widening"): validate_experiment(x)
    def test_duplicate_role(self):
        x=spec("lead_worker"); x["organization"]["roles"][1]["role_id"]="lead"
        with self.assertRaisesRegex(ContractError,"duplicate role_id"): validate_experiment(x)
    def test_independent_refs(self):
        x=spec("independent_adjudicator"); x["organization"]["roles"][2]["worker_ref"]="worker:a"
        with self.assertRaises(ContractError): validate_experiment(x)
    def test_digest_normalization(self):
        a=spec("lead_worker"); b=copy.deepcopy(a); b["organization"]["tool_allowlist"]=["write","read"]; b["organization"]["roles"][0]["tools"]=["write","read"]; b["evidence_policy"]["accepted_evidence_classes"]=["independent_rerun","replay_validated"]
        self.assertEqual(experiment_digest(a),experiment_digest(b)); self.assertEqual(organization_digest(a),organization_digest(b))
    def test_pass_and_verify(self):
        s=spec("specialist_team"); r=build_receipt(s,outcome()); self.assertEqual(r["verdict"],"PASS"); self.assertEqual(verify_receipt(s,r),r); self.assertEqual(len(receipt_digest(r)),64)
    def test_policy_violation(self): self.assertEqual(build_receipt(spec(),outcome(policy_violations=["forbidden-write"]))["verdict"],"FAIL_POLICY")
    def test_duplicate_side_effect(self): self.assertEqual(build_receipt(spec(),outcome(duplicate_side_effects=1))["verdict"],"FAIL_POLICY")
    def test_budget_overrun(self):
        r=build_receipt(spec(),outcome(steps=21,tool_calls=31,resource_units=101))
        self.assertEqual(set(r["policy_violations"]),{"step_budget_exceeded","tool_call_budget_exceeded","resource_budget_exceeded"})
    def test_interruption_resume(self):
        r=build_receipt(spec("lead_worker"),outcome(interruptions=1,resume_attempts=1,successful_resumes=1,worker_replacements=1)); self.assertEqual(r["verdict"],"PASS")
    def test_disallowed_replacement(self):
        s=spec("lead_worker"); s["organization"]["recovery_policy"]["allow_worker_replacement"]=False
        self.assertEqual(build_receipt(s,outcome(interruptions=1,resume_attempts=1,successful_resumes=1,worker_replacements=1))["verdict"],"FAIL_POLICY")
    def test_tamper(self):
        s=spec(); r=build_receipt(s,outcome()); d=receipt_digest(r); r["metrics"]["resource_units"]+=1
        with self.assertRaisesRegex(ContractError,"receipt digest mismatch"): verify_receipt(s,r,d)
    def test_structural_verification_is_not_authentication(self):
        s=spec(); r=build_receipt(s,outcome()); r["metrics"]["resource_units"]+=1
        self.assertEqual(verify_receipt(s,r),r)
    def test_comparable_structures(self): self.assertEqual(comparability_reasons(spec(),spec("lead_worker")),[])
    def test_budget_drift(self):
        b=spec("lead_worker"); b["budget"]["max_resource_units"]=101; self.assertEqual(comparability_reasons(spec(),b),["budget_mismatch"])
    def test_compare_no_ranking(self):
        a,b=spec(),spec("lead_worker"); c=compare_receipts(a,build_receipt(a,outcome(operator_interventions=1,resource_units=60)),b,build_receipt(b,outcome(resource_units=50))); self.assertIsNone(c["ranking"]); self.assertEqual(c["metric_deltas_right_minus_left"]["resource_units"],-10)
    def test_incomparable(self):
        a,b=spec(),spec("lead_worker"); b["task"]["fixture_digest"]="4"*64
        with self.assertRaisesRegex(ContractError,"task_mismatch"): compare_receipts(a,build_receipt(a,outcome()),b,build_receipt(b,outcome()))

if __name__=="__main__": unittest.main()
