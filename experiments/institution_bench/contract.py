"""Fixture-only organizational experiment contracts for BuilderWars."""
from __future__ import annotations
from copy import deepcopy
import re
from arena.canonical import digest

EXPERIMENT_SCHEMA = "builderwars.institution-experiment.v0"
RECEIPT_SCHEMA = "builderwars.institution-experiment.receipt.v0"
COMPARISON_SCHEMA = "builderwars.institution-experiment.comparison.v0"
TOPOLOGIES = {"single", "lead_worker", "independent_adjudicator", "specialist_team"}
ROLE_KINDS = {"worker", "lead", "adjudicator", "specialist"}
MEMORY = {"none", "ephemeral", "reviewed"}
EVIDENCE = {"declared", "replay_validated", "hosted_run_recorded", "independent_review", "independent_rerun"}\nINDEPENDENT_EVIDENCE = {"independent_review", "independent_rerun"}
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")

class ContractError(ValueError):
    pass

def _closed(v, keys, where):
    if not isinstance(v, dict):
        raise ContractError(f"{where}: expected object")
    missing, extra = set(keys)-set(v), set(v)-set(keys)
    if missing or extra:
        raise ContractError(f"{where}: missing={sorted(missing)} unknown={sorted(extra)}")
    return v

def _sid(v, where):
    if not isinstance(v, str) or not _ID.fullmatch(v):
        raise ContractError(f"{where}: invalid id")
    return v

def _sha(v, where):
    if not isinstance(v, str) or not _SHA.fullmatch(v):
        raise ContractError(f"{where}: expected sha256")
    return v

def _uint(v, where, positive=False):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0 or (positive and v == 0):
        raise ContractError(f"{where}: invalid integer")
    return v

def _strings(v, where, nonempty=False):
    if not isinstance(v, list) or any(not isinstance(x, str) or not x for x in v):
        raise ContractError(f"{where}: expected string list")
    if nonempty and not v:
        raise ContractError(f"{where}: empty")
    if len(v) != len(set(v)):
        raise ContractError(f"{where}: duplicate")
    return sorted(v)

def _evidence_refs(v, accepted):
    if not isinstance(v, list) or len(v) > 64:
        raise ContractError("evidence_refs: expected bounded list")
    out=[]; seen=set()
    for i,item in enumerate(v):
        item=deepcopy(_closed(item,{"ref","class"},f"evidence_refs[{i}]"))
        item["ref"]=_sid(item["ref"],f"evidence_refs[{i}].ref")
        if item["class"] not in EVIDENCE or item["class"] not in accepted:
            raise ContractError(f"evidence_refs[{i}]: evidence class not accepted")
        key=(item["ref"],item["class"])
        if key in seen: raise ContractError("evidence_refs: duplicate")
        seen.add(key); out.append(item)
    return sorted(out,key=lambda x:(x["class"],x["ref"]))

def _roles(org, allow):
    roles = org["roles"]
    if not isinstance(roles, list) or not roles or len(roles) > 16:
        raise ContractError("organization.roles: invalid size")
    out=[]
    for i,r in enumerate(roles):
        r=deepcopy(_closed(r,{"role_id","role_kind","worker_ref","responsibility","tools","can_delegate","can_adjudicate"},f"role[{i}]"))
        r["role_id"]=_sid(r["role_id"],f"role[{i}].role_id")
        r["worker_ref"]=_sid(r["worker_ref"],f"role[{i}].worker_ref")
        if r["role_kind"] not in ROLE_KINDS or not isinstance(r["responsibility"],str) or not r["responsibility"].strip():
            raise ContractError(f"role[{i}]: invalid role")
        if not isinstance(r["can_delegate"],bool) or not isinstance(r["can_adjudicate"],bool):
            raise ContractError(f"role[{i}]: invalid authority flags")
        if r["can_delegate"] and r["role_kind"] != "lead":
            raise ContractError("only lead may delegate")
        if r["can_adjudicate"] and r["role_kind"] != "adjudicator":
            raise ContractError("only adjudicator may adjudicate")
        r["tools"]=_strings(r["tools"],f"role[{i}].tools")
        if set(r["tools"])-allow:
            raise ContractError("permission widening")
        out.append(r)
    if len({r["role_id"] for r in out}) != len(out):
        raise ContractError("duplicate role_id")
    return out

def _topology(name, roles):
    leads=[r for r in roles if r["role_kind"]=="lead"]
    judges=[r for r in roles if r["role_kind"]=="adjudicator"]
    workers=[r for r in roles if r["role_kind"] in {"worker","specialist"}]
    specialists=[r for r in roles if r["role_kind"]=="specialist"]
    if name=="single":
        ok=len(roles)==1 and roles[0]["role_kind"]=="worker" and not roles[0]["can_delegate"] and not roles[0]["can_adjudicate"]
    elif name=="lead_worker":
        ok=len(leads)==1 and leads[0]["can_delegate"] and len(workers)>=1 and not judges
    elif name=="independent_adjudicator":
        ok=not leads and len(judges)==1 and judges[0]["can_adjudicate"] and len(workers)>=2 and len({r["worker_ref"] for r in roles})==len(roles)
    elif name=="specialist_team":
        ok=not judges and len(specialists)>=2 and len(leads)<=1 and (not leads or leads[0]["can_delegate"])
    else:
        ok=False
    if not ok:
        raise ContractError(f"organization: invalid {name} topology")

def validate_experiment(spec):
    s=deepcopy(_closed(spec,{"schema","experiment_id","task","organization","budget","evidence_policy","acceptance"},"experiment"))
    if s["schema"] != EXPERIMENT_SCHEMA: raise ContractError("experiment.schema")
    s["experiment_id"]=_sid(s["experiment_id"],"experiment_id")
    t=_closed(s["task"],{"task_id","task_digest","fixture_digest"},"task")
    s["task"]={"task_id":_sid(t["task_id"],"task_id"),"task_digest":_sha(t["task_digest"],"task_digest"),"fixture_digest":_sha(t["fixture_digest"],"fixture_digest")}
    o=_closed(s["organization"],{"organization_id","topology","roles","tool_allowlist","memory_policy","recovery_policy"},"organization")
    if o["topology"] not in TOPOLOGIES or o["memory_policy"] not in MEMORY: raise ContractError("organization policy")
    allow=_strings(o["tool_allowlist"],"tool_allowlist")
    roles=_roles(o,set(allow)); _topology(o["topology"],roles)
    rp=_closed(o["recovery_policy"],{"checkpoint_required","allow_worker_replacement","max_resume_attempts"},"recovery_policy")
    if not isinstance(rp["checkpoint_required"],bool) or not isinstance(rp["allow_worker_replacement"],bool): raise ContractError("recovery flags")
    rp={**rp,"max_resume_attempts":_uint(rp["max_resume_attempts"],"max_resume_attempts")}
    if rp["max_resume_attempts"]>10: raise ContractError("max_resume_attempts")
    s["organization"]={"organization_id":_sid(o["organization_id"],"organization_id"),"topology":o["topology"],"roles":roles,"tool_allowlist":allow,"memory_policy":o["memory_policy"],"recovery_policy":rp}
    b=_closed(s["budget"],{"max_steps","max_tool_calls","max_operator_interventions","max_resource_units","max_elapsed_ms"},"budget")
    s["budget"]={k:_uint(v,k,positive=k in {"max_steps","max_elapsed_ms"}) for k,v in b.items()}
    ep=_closed(s["evidence_policy"],{"require_receipt","require_independent_review","accepted_evidence_classes"},"evidence_policy")
    if ep["require_receipt"] is not True or not isinstance(ep["require_independent_review"],bool): raise ContractError("evidence flags")
    classes=_strings(ep["accepted_evidence_classes"],"evidence classes",True)
    if set(classes)-EVIDENCE: raise ContractError("unknown evidence class")
    s["evidence_policy"]={**ep,"accepted_evidence_classes":classes}
    a=_closed(s["acceptance"],{"acceptance_test_digest","critical_policy_violations_allowed"},"acceptance")
    if _uint(a["critical_policy_violations_allowed"],"critical violations") != 0: raise ContractError("critical violations must be zero")
    s["acceptance"]={"acceptance_test_digest":_sha(a["acceptance_test_digest"],"acceptance digest"),"critical_policy_violations_allowed":0}
    return s

def experiment_digest(spec): return digest(validate_experiment(spec))
def organization_digest(spec): return digest(validate_experiment(spec)["organization"])
def receipt_digest(receipt): return digest(receipt)

def _outcome(o):
    keys={"accepted","steps","tool_calls","operator_interventions","resource_units","elapsed_ms","retries","interruptions","resume_attempts","successful_resumes","worker_replacements","duplicate_side_effects","policy_violations","evidence_refs"}
    x=deepcopy(_closed(o,keys,"outcome"))
    if not isinstance(x["accepted"],bool): raise ContractError("outcome.accepted")
    for k in keys-{"accepted","policy_violations","evidence_refs"}: x[k]=_uint(x[k],k)
    if x["successful_resumes"]>x["resume_attempts"]: raise ContractError("resume counts")
    x["policy_violations"]=_strings(x["policy_violations"],"policy_violations")
    if x["successful_resumes"]>x["interruptions"]: raise ContractError("resume without interruption")\n    x["evidence_refs"]=_evidence_refs(x["evidence_refs"],set(accepted_evidence))
    return x

def build_receipt(spec,outcome):
    s=validate_experiment(spec); o=_outcome(outcome,s["evidence_policy"]["accepted_evidence_classes"]); b=s["budget"]; rp=s["organization"]["recovery_policy"]
    v=set(o["policy_violations"])
    if o["steps"]>b["max_steps"]: v.add("step_budget_exceeded")
    if o["tool_calls"]>b["max_tool_calls"]: v.add("tool_call_budget_exceeded")
    if o["operator_interventions"]>b["max_operator_interventions"]: v.add("operator_intervention_budget_exceeded")
    if o["resource_units"]>b["max_resource_units"]: v.add("resource_budget_exceeded")
    if o["elapsed_ms"]>b["max_elapsed_ms"]: v.add("elapsed_budget_exceeded")
    if o["resume_attempts"]>rp["max_resume_attempts"]: v.add("resume_attempt_budget_exceeded")
    if o["accepted"] and o["interruptions"] and rp["checkpoint_required"] and o["successful_resumes"] != o["interruptions"]: v.add("checkpoint_recovery_incomplete")\n    if o["accepted"] and not o["evidence_refs"]: v.add("accepted_without_evidence")\n    if o["accepted"] and s["evidence_policy"]["require_independent_review"] and not any(e["class"] in INDEPENDENT_EVIDENCE for e in o["evidence_refs"]): v.add("independent_review_missing")
    if o["worker_replacements"] and not rp["allow_worker_replacement"]: v.add("worker_replacement_not_allowed")
    if o["worker_replacements"]>o["interruptions"]: v.add("replacement_without_matching_interruption")
    if o["duplicate_side_effects"]: v.add("duplicate_side_effect_observed")
    verdict="FAIL_POLICY" if v else "PASS" if o["accepted"] else "FAIL"
    metrics={k:o[k] for k in o if k not in {"policy_violations","evidence_refs"}}
    return {"schema":RECEIPT_SCHEMA,"experiment_id":s["experiment_id"],"experiment_digest":digest(s),"organization_id":s["organization"]["organization_id"],"organization_digest":digest(s["organization"]),"topology":s["organization"]["topology"],"task":s["task"],"acceptance_test_digest":s["acceptance"]["acceptance_test_digest"],"budget":s["budget"],"tool_allowlist":s["organization"]["tool_allowlist"],"evidence_policy":s["evidence_policy"],"verdict":verdict,"claim_scope":"task_scoped_only","metrics":metrics,"policy_violations":sorted(v),"evidence_refs":o["evidence_refs"]}

def verify_receipt(spec,r,expected_digest=None):
    s=validate_experiment(spec)
    if expected_digest is not None:
        expected_digest=_sha(expected_digest,"expected_receipt_digest")
        if digest(r) != expected_digest: raise ContractError("receipt digest mismatch")
    if not isinstance(r,dict) or r.get("schema")!=RECEIPT_SCHEMA or r.get("experiment_id")!=s["experiment_id"] or r.get("experiment_digest")!=digest(s) or r.get("organization_digest")!=digest(s["organization"]): raise ContractError("receipt binding mismatch")
    if r.get("claim_scope")!="task_scoped_only": raise ContractError("receipt scope")
    observed={**r.get("metrics",{}),"policy_violations":r.get("policy_violations",[]),"evidence_refs":r.get("evidence_refs",[])}
    if build_receipt(s,observed)!=r: raise ContractError("receipt does not reproduce")
    return deepcopy(r)

def comparability_reasons(a,b):
    a,b=validate_experiment(a),validate_experiment(b); reasons=[]
    for label,av,bv in (("task",a["task"],b["task"]),("acceptance",a["acceptance"],b["acceptance"]),("budget",a["budget"],b["budget"]),("tool_allowlist",a["organization"]["tool_allowlist"],b["organization"]["tool_allowlist"]),("evidence_policy",a["evidence_policy"],b["evidence_policy"])):
        if av!=bv: reasons.append(f"{label}_mismatch")
    return reasons

def compare_receipts(a,ar,b,br):
    a,b=validate_experiment(a),validate_experiment(b); ar,br=verify_receipt(a,ar),verify_receipt(b,br)
    reasons=comparability_reasons(a,b)
    if reasons: raise ContractError("experiments not comparable: "+", ".join(reasons))
    am,bm=ar["metrics"],br["metrics"]
    keys=["steps","tool_calls","operator_interventions","operator_active_ms","resource_units","elapsed_ms","retries","interruptions","resume_attempts","successful_resumes","worker_replacements","duplicate_side_effects"]
    return {"schema":COMPARISON_SCHEMA,"claim_scope":"task_scoped_only","left":{"experiment_id":a["experiment_id"],"topology":a["organization"]["topology"],"receipt_digest":digest(ar),"verdict":ar["verdict"]},"right":{"experiment_id":b["experiment_id"],"topology":b["organization"]["topology"],"receipt_digest":digest(br),"verdict":br["verdict"]},"metric_deltas_right_minus_left":{k:bm[k]-am[k] for k in keys},"ranking":None,"note":"Task-scoped comparison only; no universal winner."}
