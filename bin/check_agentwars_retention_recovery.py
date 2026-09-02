#!/usr/bin/env python3
"""Adversarial checks for AgentWars retention, deletion, and recovery drills."""

from __future__ import annotations

import ast
import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishing import retention_recovery as rr


CHECKS = 0
T0 = "2026-09-01T00:00:00Z"
T1 = "2026-09-01T00:01:00Z"
T2 = "2026-09-01T00:02:00Z"
TENANT = "awten_" + "1" * 32
OTHER_TENANT = "awten_" + "2" * 32


def check(condition: bool, label: str) -> None:
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def refuses(callable_, label: str) -> None:
    try:
        callable_()
    except rr.RetentionRecoveryError:
        check(True, label)
    else:
        raise AssertionError(label)


def reseal(value: dict[str, object], digest_field: str) -> dict[str, object]:
    result = copy.deepcopy(value)
    result.pop(digest_field, None)
    result[digest_field] = rr.digest(result)
    return result


def resource(number: int, resource_class: str, *, tenant: str = TENANT, created_at: str = T0) -> dict[str, object]:
    return {
        "resourceId": "awres_" + f"{number:032x}",
        "resourceClass": resource_class,
        "tenantRef": tenant,
        "contentDigest": f"{number:064x}",
        "createdAt": created_at,
        "lifecycleState": "present",
    }


def assert_authority_false(value: object, label: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "productionAuthority":
                check(item == rr.PRODUCTION_AUTHORITY, f"{label}: production authority is exact")
                check(all(type(flag) is bool and flag is False for flag in item.values()), f"{label}: authority flags are false booleans")
            if key in {
                "productionDeletionProven", "actionsExecutedInProduction", "productionRestoreProven",
                "rollbackExecutedInProduction", "actionsExecuted", "productionPolicyApproved",
            }:
                check(item is False, f"{label}: {key} remains false")
            assert_authority_false(item, label)
    elif isinstance(value, list):
        for item in value:
            assert_authority_false(item, label)


def main() -> int:
    contract = rr.retention_recovery_contract()
    check(contract["schemaVersion"] == rr.CONTRACT_SCHEMA, "contract schema is pinned")
    check(contract["contractStatus"] == "local_contract_only_not_integrated", "contract reports local-only status")
    check(contract["resourcePolicies"] == rr.RESOURCE_POLICIES, "contract publishes exact resource policies")
    check(set(contract["resourcePolicies"]) == set(rr.RESOURCE_POLICIES), "all resource classes are classified")
    check(contract["rollbackActionSequence"] == list(rr.ROLLBACK_ACTION_SEQUENCE), "rollback action sequence is exact")
    check(contract["rollbackValidationSequence"] == list(rr.ROLLBACK_VALIDATION_SEQUENCE), "rollback validation sequence is exact")
    unsigned_contract = dict(contract)
    supplied_contract_digest = unsigned_contract.pop("contractDigest")
    check(rr.digest(unsigned_contract) == supplied_contract_digest, "contract digest verifies")
    assert_authority_false(contract, "contract")

    resources = [
        resource(1, "private_submission"),
        resource(2, "public_receipt_projection"),
        resource(3, "temporary_transcript"),
        resource(4, "synthetic_probe"),
    ]
    inventory = rr.build_inventory(resources, T1)
    check(inventory["schemaVersion"] == rr.INVENTORY_SCHEMA, "inventory schema is pinned")
    check(inventory["sourceStatus"] == "synthetic_digest_manifest_in_memory_only", "inventory source is explicitly synthetic")
    check(inventory["resources"] == resources, "inventory retains exact sorted digest-only resources")
    check(inventory == rr.build_inventory(resources, T1), "inventory is deterministic")
    check(rr.digest({key: value for key, value in inventory.items() if key != "inventoryDigest"}) == inventory["inventoryDigest"], "inventory digest verifies")
    check("payload" not in str(inventory).lower() and "email" not in str(inventory).lower(), "inventory contains no payload or email field")
    assert_authority_false(inventory, "inventory")

    malformed = copy.deepcopy(resources)
    malformed[0]["unexpected"] = "x"
    refuses(lambda: rr.build_inventory(malformed, T1), "inventory refuses unknown resource fields")
    malformed = copy.deepcopy(resources)
    malformed[0]["resourceId"] = "bad"
    refuses(lambda: rr.build_inventory(malformed, T1), "inventory refuses malformed resource id")
    malformed = copy.deepcopy(resources)
    malformed[0]["contentDigest"] = "0" * 63
    refuses(lambda: rr.build_inventory(malformed, T1), "inventory refuses malformed content digest")
    malformed = copy.deepcopy(resources)
    malformed[0]["resourceClass"] = "secret_blob"
    refuses(lambda: rr.build_inventory(malformed, T1), "inventory refuses unknown resource class")
    malformed = copy.deepcopy(resources)
    malformed[0]["createdAt"] = T2
    refuses(lambda: rr.build_inventory(malformed, T1), "inventory refuses future resource")
    malformed = copy.deepcopy(resources)
    malformed[0]["lifecycleState"] = "deleted"
    refuses(lambda: rr.build_inventory(malformed, T1), "inventory refuses pre-claimed deletion")
    refuses(lambda: rr.build_inventory(list(reversed(resources)), T1), "inventory refuses unstable resource order")
    refuses(lambda: rr.build_inventory([resources[0], resources[0]], T1), "inventory refuses duplicate resource ids")
    refuses(lambda: rr.build_inventory(resources, "2026-09-01"), "inventory refuses malformed observation timestamp")

    request = rr.build_deletion_request(
        request_id="awdel_" + "a" * 32,
        requested_at=T1,
        tenant_ref=TENANT,
        resource_ids=[item["resourceId"] for item in resources],
        reason="test_cleanup_fixture",
    )
    check(request["schemaVersion"] == rr.DELETION_REQUEST_SCHEMA, "deletion request schema is pinned")
    check(request["authorizationStatus"] == "synthetic_fixture_only_not_identity_or_consent", "deletion request cannot attest identity or consent")
    check(request == rr.build_deletion_request(
        request_id="awdel_" + "a" * 32,
        requested_at=T1,
        tenant_ref=TENANT,
        resource_ids=[item["resourceId"] for item in resources],
        reason="test_cleanup_fixture",
    ), "deletion request is deterministic")
    assert_authority_false(request, "deletion request")
    refuses(lambda: rr.build_deletion_request(request_id="bad", requested_at=T1, tenant_ref=TENANT, resource_ids=[resources[0]["resourceId"]], reason="test_cleanup_fixture"), "request refuses malformed id")
    refuses(lambda: rr.build_deletion_request(request_id="awdel_" + "b" * 32, requested_at=T1, tenant_ref=TENANT, resource_ids=[], reason="test_cleanup_fixture"), "request refuses empty resource set")
    refuses(lambda: rr.build_deletion_request(request_id="awdel_" + "b" * 32, requested_at=T1, tenant_ref=TENANT, resource_ids=[resources[1]["resourceId"], resources[0]["resourceId"]], reason="test_cleanup_fixture"), "request refuses unstable resource order")
    refuses(lambda: rr.build_deletion_request(request_id="awdel_" + "b" * 32, requested_at=T1, tenant_ref=TENANT, resource_ids=[resources[0]["resourceId"]] * 2, reason="test_cleanup_fixture"), "request refuses duplicate resources")
    refuses(lambda: rr.build_deletion_request(request_id="awdel_" + "b" * 32, requested_at=T1, tenant_ref=TENANT, resource_ids=[resources[0]["resourceId"]], reason="operator_said_delete"), "request refuses unclassified reason")

    plan = rr.plan_deletion(
        plan_id="awdplan_" + "b" * 32,
        planned_at=T2,
        inventory=inventory,
        request=request,
    )
    check(plan["schemaVersion"] == rr.DELETION_PLAN_SCHEMA, "deletion plan schema is pinned")
    check(plan["decision"] == "LOCAL_DRILL_ONLY", "deletion plan remains local drill only")
    check(plan["atomicity"] == "all_or_none_in_memory_simulation", "deletion plan is atomically simulated")
    check([item["action"] for item in plan["actions"]] == [
        "simulate_physical_delete", "simulate_logical_suppression", "simulate_physical_delete", "simulate_physical_delete"
    ], "deletion actions follow exact class policy")
    check(plan["actionsExecuted"] is False, "deletion plan executes no action")
    assert_authority_false(plan, "deletion plan")

    receipt = rr.execute_deletion_drill(plan=plan, inventory=inventory, request=request)
    check(receipt["schemaVersion"] == rr.DELETION_RECEIPT_SCHEMA, "deletion receipt schema is pinned")
    check(receipt["status"] == "DRILL_PASS", "deletion drill passes in memory")
    check(receipt["plannedActionCount"] == 4 and receipt["appliedActionCount"] == 4, "deletion drill accounts for every planned action")
    check(receipt["postStateSummary"]["simulatedPhysicalDeleteCount"] == 3, "deletion drill counts simulated physical deletes")
    check(receipt["postStateSummary"]["simulatedLogicalSuppressCount"] == 1, "deletion drill counts logical suppression")
    check(receipt["postStateSummary"]["retainedLineageDigestCount"] == 1, "logical suppression retains lineage digest")
    check(receipt["productionDeletionProven"] is False, "deletion drill does not prove production deletion")
    check(rr.digest({key: value for key, value in receipt.items() if key != "receiptDigest"}) == receipt["receiptDigest"], "deletion receipt digest verifies")
    assert_authority_false(receipt, "deletion receipt")

    failure = rr.execute_deletion_drill(
        plan=plan,
        inventory=inventory,
        request=request,
        injected_failure_resource_ids=[resources[2]["resourceId"]],
    )
    check(failure["status"] == "DRILL_REFUSED_INJECTED_FAILURE", "injected deletion failure is refused")
    check(failure["appliedActionCount"] == 0, "injected deletion failure applies no partial action")
    check(failure["postStateSummary"]["simulatedPhysicalDeleteCount"] == 0, "refused deletion performs no simulated physical delete")
    check(failure["postStateSummary"]["simulatedLogicalSuppressCount"] == 0, "refused deletion performs no simulated suppression")
    assert_authority_false(failure, "failed deletion receipt")
    refuses(lambda: rr.execute_deletion_drill(plan=plan, inventory=inventory, request=request, injected_failure_resource_ids=["awres_" + "f" * 32]), "deletion drill refuses failure outside plan")
    refuses(lambda: rr.execute_deletion_drill(plan=plan, inventory=inventory, request=request, injected_failure_resource_ids=[resources[0]["resourceId"]] * 2), "deletion drill refuses duplicate failure fixtures")

    held_inventory = rr.build_inventory([resource(5, "operational_event")], T1)
    held_request = rr.build_deletion_request(
        request_id="awdel_" + "c" * 32,
        requested_at=T1,
        tenant_ref=TENANT,
        resource_ids=["awres_" + f"{5:032x}"],
        reason="policy_expiry_fixture",
    )
    held_plan = rr.plan_deletion(
        plan_id="awdplan_" + "d" * 32,
        planned_at=T2,
        inventory=held_inventory,
        request=held_request,
    )
    check(held_plan["decision"] == "HELD_POLICY_REVIEW", "unapproved operations retention is held")
    check(held_plan["actions"][0]["action"] == "hold_for_policy_review", "held retention has no deletion action")
    held_receipt = rr.execute_deletion_drill(plan=held_plan, inventory=held_inventory, request=held_request)
    check(held_receipt["status"] == "DRILL_HELD_POLICY_REVIEW", "policy-held deletion drill does nothing")
    check(held_receipt["appliedActionCount"] == 0, "policy-held drill applies zero actions")
    assert_authority_false(held_receipt, "held deletion receipt")

    cross_tenant_inventory = rr.build_inventory([resource(6, "private_submission", tenant=OTHER_TENANT)], T1)
    cross_tenant_request = rr.build_deletion_request(
        request_id="awdel_" + "e" * 32,
        requested_at=T1,
        tenant_ref=TENANT,
        resource_ids=["awres_" + f"{6:032x}"],
        reason="verified_request_fixture",
    )
    refuses(lambda: rr.plan_deletion(plan_id="awdplan_" + "e" * 32, planned_at=T2, inventory=cross_tenant_inventory, request=cross_tenant_request), "deletion plan refuses cross-tenant resource")
    absent_request = rr.build_deletion_request(
        request_id="awdel_" + "f" * 32,
        requested_at=T1,
        tenant_ref=TENANT,
        resource_ids=["awres_" + "f" * 32],
        reason="verified_request_fixture",
    )
    refuses(lambda: rr.plan_deletion(plan_id="awdplan_" + "f" * 32, planned_at=T2, inventory=inventory, request=absent_request), "deletion plan refuses absent resource")
    refuses(lambda: rr.plan_deletion(plan_id="awdplan_" + "f" * 32, planned_at=T0, inventory=inventory, request=request), "deletion plan refuses pre-request timestamp")

    for field, replacement in (
        ("actionsExecuted", True),
        ("decision", "PRODUCTION_DELETE"),
        ("atomicity", "best_effort"),
    ):
        hostile = copy.deepcopy(plan)
        hostile[field] = replacement
        hostile = reseal(hostile, "planDigest")
        refuses(lambda hostile=hostile: rr.execute_deletion_drill(plan=hostile, inventory=inventory, request=request), f"deletion drill refuses resealed {field} drift")
    hostile = copy.deepcopy(plan)
    hostile["productionAuthority"]["productionDeletionExecuted"] = True
    hostile = reseal(hostile, "planDigest")
    refuses(lambda: rr.execute_deletion_drill(plan=hostile, inventory=inventory, request=request), "deletion drill refuses production authority escalation")
    hostile = copy.deepcopy(plan)
    hostile["actions"][0]["action"] = "simulate_logical_suppression"
    hostile = reseal(hostile, "planDigest")
    refuses(lambda: rr.execute_deletion_drill(plan=hostile, inventory=inventory, request=request), "deletion drill refuses action-policy drift")
    hostile = copy.deepcopy(plan)
    hostile["actions"] = hostile["actions"][1:]
    hostile = reseal(hostile, "planDigest")
    refuses(lambda: rr.execute_deletion_drill(plan=hostile, inventory=inventory, request=request), "deletion drill refuses request-action drift")
    hostile_inventory = copy.deepcopy(inventory)
    hostile_inventory["productionAuthority"]["productionDataRead"] = True
    hostile_inventory = reseal(hostile_inventory, "inventoryDigest")
    refuses(lambda: rr.execute_deletion_drill(plan=plan, inventory=hostile_inventory, request=request), "deletion drill refuses inventory authority escalation")
    hostile_request = copy.deepcopy(request)
    hostile_request["authorizationStatus"] = "verified_customer_consent"
    hostile_request = reseal(hostile_request, "requestDigest")
    refuses(lambda: rr.execute_deletion_drill(plan=plan, inventory=inventory, request=hostile_request), "deletion drill refuses consent attestation")

    known_good = rr.build_release_manifest(
        release_id="awrel_" + "1" * 32,
        observed_at=T0,
        source_commit="1" * 40,
        source_tree="2" * 40,
        artifact_digest="3" * 64,
        verifier_digest="4" * 64,
        configuration_digest="5" * 64,
    )
    current = rr.build_release_manifest(
        release_id="awrel_" + "2" * 32,
        observed_at=T1,
        source_commit="6" * 40,
        source_tree="7" * 40,
        artifact_digest="8" * 64,
        verifier_digest="9" * 64,
        configuration_digest="a" * 64,
    )
    for manifest, label in ((known_good, "known-good release"), (current, "current release")):
        check(manifest["schemaVersion"] == rr.RELEASE_SCHEMA, f"{label} schema is pinned")
        check(manifest["environmentClass"] == "local_fixture_only", f"{label} is local fixture only")
        check(manifest["deploymentStatus"] == "not_deployed", f"{label} is not deployed")
        assert_authority_false(manifest, label)
    check(known_good == rr.build_release_manifest(
        release_id="awrel_" + "1" * 32, observed_at=T0, source_commit="1" * 40,
        source_tree="2" * 40, artifact_digest="3" * 64, verifier_digest="4" * 64,
        configuration_digest="5" * 64,
    ), "release manifest is deterministic")
    refuses(lambda: rr.build_release_manifest(release_id="bad", observed_at=T0, source_commit="1" * 40, source_tree="2" * 40, artifact_digest="3" * 64, verifier_digest="4" * 64, configuration_digest="5" * 64), "release manifest refuses malformed id")
    refuses(lambda: rr.build_release_manifest(release_id="awrel_" + "3" * 32, observed_at=T0, source_commit="1" * 39, source_tree="2" * 40, artifact_digest="3" * 64, verifier_digest="4" * 64, configuration_digest="5" * 64), "release manifest refuses malformed commit")
    refuses(lambda: rr.build_release_manifest(release_id="awrel_" + "3" * 32, observed_at="soon", source_commit="1" * 40, source_tree="2" * 40, artifact_digest="3" * 64, verifier_digest="4" * 64, configuration_digest="5" * 64), "release manifest refuses malformed time")

    snapshot = rr.build_recovery_snapshot(
        snapshot_id="awsnap_" + "3" * 32,
        captured_at=T1,
        release=known_good,
    )
    check(snapshot["schemaVersion"] == rr.SNAPSHOT_SCHEMA, "recovery snapshot schema is pinned")
    check(snapshot["storageStatus"] == "digest_manifest_only_no_backup_created", "snapshot does not claim backup creation")
    check(snapshot["releaseDigest"] == known_good["releaseDigest"], "snapshot binds known-good release")
    check(snapshot["artifactDigest"] == known_good["artifactDigest"], "snapshot binds known-good artifact")
    check(snapshot == rr.build_recovery_snapshot(snapshot_id="awsnap_" + "3" * 32, captured_at=T1, release=known_good), "recovery snapshot is deterministic")
    assert_authority_false(snapshot, "recovery snapshot")
    refuses(lambda: rr.build_recovery_snapshot(snapshot_id="awsnap_" + "4" * 32, captured_at="2025-01-01T00:00:00Z", release=known_good), "snapshot refuses time before release")
    hostile_release = copy.deepcopy(known_good)
    hostile_release["deploymentStatus"] = "deployed"
    hostile_release = reseal(hostile_release, "releaseDigest")
    refuses(lambda: rr.build_recovery_snapshot(snapshot_id="awsnap_" + "4" * 32, captured_at=T1, release=hostile_release), "snapshot refuses deployment claim")

    rollback = rr.plan_rollback(
        plan_id="awrb_" + "4" * 32,
        planned_at=T2,
        trigger="integrity_failure_fixture",
        current_release=current,
        last_known_good=snapshot,
    )
    check(rollback["schemaVersion"] == rr.ROLLBACK_PLAN_SCHEMA, "rollback plan schema is pinned")
    check(rollback["planStatus"] == "local_simulation_only_not_executed", "rollback plan is not executed")
    check(rollback["restoreTarget"]["sourceCommit"] == known_good["sourceCommit"], "rollback target binds known-good source")
    check(rollback["restoreTarget"]["artifactDigest"] == known_good["artifactDigest"], "rollback target binds known-good artifact")
    check(rollback["actionSequence"] == list(rr.ROLLBACK_ACTION_SEQUENCE), "rollback plan action sequence is exact")
    check(rollback["validationSequence"] == list(rr.ROLLBACK_VALIDATION_SEQUENCE), "rollback plan validation sequence is exact")
    check(rollback["actionsExecuted"] is False, "rollback plan executes nothing")
    assert_authority_false(rollback, "rollback plan")
    refuses(lambda: rr.plan_rollback(plan_id="awrb_" + "5" * 32, planned_at=T2, trigger="deploy_because_requested", current_release=current, last_known_good=snapshot), "rollback plan refuses unclassified trigger")
    same_snapshot = rr.build_recovery_snapshot(snapshot_id="awsnap_" + "5" * 32, captured_at=T2, release=current)
    refuses(lambda: rr.plan_rollback(plan_id="awrb_" + "5" * 32, planned_at=T2, trigger="operator_request_fixture", current_release=current, last_known_good=same_snapshot), "rollback plan refuses current release as known-good target")

    recovery = rr.execute_recovery_drill(plan=rollback, current_release=current, last_known_good=snapshot)
    check(recovery["schemaVersion"] == rr.RECOVERY_RECEIPT_SCHEMA, "recovery receipt schema is pinned")
    check(recovery["status"] == "DRILL_PASS", "recovery drill passes in memory")
    check(recovery["injectedFailure"] == "none" and recovery["failedStep"] is None, "passing recovery has no failed step")
    check(all(recovery["validationResults"].values()), "passing recovery verifies every target dimension")
    check(recovery["productionRestoreProven"] is False, "recovery drill does not prove production restore")
    check(recovery["rollbackExecutedInProduction"] is False, "recovery drill does not claim rollback")
    check(rr.digest({key: value for key, value in recovery.items() if key != "receiptDigest"}) == recovery["receiptDigest"], "recovery receipt digest verifies")
    assert_authority_false(recovery, "recovery receipt")

    failure_steps = {
        "snapshot_unavailable": "select_last_known_good_digest_manifest",
        "artifact_restore_failure": "simulate_artifact_restore",
        "verification_failure": "reverify_source_tree_artifact_verifier_configuration",
        "cleanup_failure": "record_cleanup",
    }
    for failure_class, failed_step in failure_steps.items():
        failed = rr.execute_recovery_drill(
            plan=rollback,
            current_release=current,
            last_known_good=snapshot,
            injected_failure=failure_class,
        )
        check(failed["status"] == "DRILL_REFUSED_INJECTED_FAILURE", f"{failure_class} fails closed")
        check(failed["failedStep"] == failed_step, f"{failure_class} names exact failed step")
        check(not any(failed["validationResults"].values()), f"{failure_class} cannot claim validation")
        assert_authority_false(failed, f"{failure_class} receipt")
    refuses(lambda: rr.execute_recovery_drill(plan=rollback, current_release=current, last_known_good=snapshot, injected_failure="network_retry"), "recovery drill refuses unknown failure fixture")

    hostile = copy.deepcopy(rollback)
    hostile["restoreTarget"]["artifactDigest"] = "f" * 64
    hostile = reseal(hostile, "planDigest")
    refuses(lambda: rr.execute_recovery_drill(plan=hostile, current_release=current, last_known_good=snapshot), "recovery drill refuses resealed restore target drift")
    hostile = copy.deepcopy(rollback)
    hostile["actionSequence"] = list(reversed(hostile["actionSequence"]))
    hostile = reseal(hostile, "planDigest")
    refuses(lambda: rr.execute_recovery_drill(plan=hostile, current_release=current, last_known_good=snapshot), "recovery drill refuses action-order drift")
    hostile = copy.deepcopy(rollback)
    hostile["validationSequence"] = hostile["validationSequence"][:-1]
    hostile = reseal(hostile, "planDigest")
    refuses(lambda: rr.execute_recovery_drill(plan=hostile, current_release=current, last_known_good=snapshot), "recovery drill refuses validation-order drift")
    hostile = copy.deepcopy(rollback)
    hostile["planStatus"] = "executed"
    hostile = reseal(hostile, "planDigest")
    refuses(lambda: rr.execute_recovery_drill(plan=hostile, current_release=current, last_known_good=snapshot), "recovery drill refuses execution claim")
    hostile = copy.deepcopy(rollback)
    hostile["actionsExecuted"] = True
    hostile = reseal(hostile, "planDigest")
    refuses(lambda: rr.execute_recovery_drill(plan=hostile, current_release=current, last_known_good=snapshot), "recovery drill refuses actions-executed claim")
    hostile = copy.deepcopy(rollback)
    hostile["productionAuthority"]["rollbackExecuted"] = True
    hostile = reseal(hostile, "planDigest")
    refuses(lambda: rr.execute_recovery_drill(plan=hostile, current_release=current, last_known_good=snapshot), "recovery drill refuses rollback authority escalation")
    hostile_snapshot = copy.deepcopy(snapshot)
    hostile_snapshot["storageStatus"] = "production_backup_verified"
    hostile_snapshot = reseal(hostile_snapshot, "snapshotDigest")
    refuses(lambda: rr.execute_recovery_drill(plan=rollback, current_release=current, last_known_good=hostile_snapshot), "recovery drill refuses backup claim")
    hostile_current = copy.deepcopy(current)
    hostile_current["productionAuthority"]["deploymentMutated"] = True
    hostile_current = reseal(hostile_current, "releaseDigest")
    refuses(lambda: rr.execute_recovery_drill(plan=rollback, current_release=hostile_current, last_known_good=snapshot), "recovery drill refuses release authority escalation")

    source_path = ROOT / "publishing" / "retention_recovery.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    imports.discard("")
    check(imports <= {"__future__", "hashlib", "json", "re", "datetime", "typing"}, "contract imports only pure standard-library modules")
    for forbidden in ("subprocess", "socket", "requests", "urllib", "pathlib", "sqlite", "redis", "open(", "unlink(", "remove(", "rmtree("):
        check(forbidden not in source.lower(), f"contract contains no {forbidden} integration")
    check("productionDeletionProven\": True" not in source, "source contains no true production-deletion claim")
    check("productionRestoreProven\": True" not in source, "source contains no true production-restore claim")
    check("rollbackExecutedInProduction\": True" not in source, "source contains no true production-rollback claim")

    print(f"AgentWars retention, deletion, rollback, and recovery contract: PASS ({CHECKS} checks)")
    print("8 resource classes / atomic deletion simulation / source-bound recovery / 5 failure drills / zero production authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
