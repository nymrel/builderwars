"""Pure retention, deletion, rollback, and recovery drills for AgentWars.

This module intentionally performs no I/O and owns no production authority. It
classifies digest-only resource manifests, plans synthetic deletion, and drills
source-bound recovery using in-memory manifests. It never reads or deletes a
real record, creates a backup, restores an artifact, changes a flag, deploys a
release, or proves that any external system performed those actions.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Iterable, Mapping


CONTRACT_SCHEMA = "agentwars.retention-recovery-contract/1"
INVENTORY_SCHEMA = "agentwars.data-inventory/1"
DELETION_REQUEST_SCHEMA = "agentwars.deletion-request/1"
DELETION_PLAN_SCHEMA = "agentwars.deletion-plan/1"
DELETION_RECEIPT_SCHEMA = "agentwars.deletion-drill-receipt/1"
RELEASE_SCHEMA = "agentwars.release-manifest/1"
SNAPSHOT_SCHEMA = "agentwars.recovery-snapshot-manifest/1"
ROLLBACK_PLAN_SCHEMA = "agentwars.rollback-plan/1"
RECOVERY_RECEIPT_SCHEMA = "agentwars.recovery-drill-receipt/1"

UTC_SECOND_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
RESOURCE_ID_RE = re.compile(r"^awres_[0-9a-f]{32}$")
TENANT_REF_RE = re.compile(r"^awten_[0-9a-f]{32}$")
REQUEST_ID_RE = re.compile(r"^awdel_[0-9a-f]{32}$")
PLAN_ID_RE = re.compile(r"^awdplan_[0-9a-f]{32}$")
RELEASE_ID_RE = re.compile(r"^awrel_[0-9a-f]{32}$")
SNAPSHOT_ID_RE = re.compile(r"^awsnap_[0-9a-f]{32}$")
ROLLBACK_ID_RE = re.compile(r"^awrb_[0-9a-f]{32}$")

RESOURCE_POLICIES: dict[str, dict[str, str]] = {
    "public_receipt_projection": {
        "disposition": "logical_suppress_preserve_lineage",
        "retentionClass": "append_only_correction_history",
    },
    "public_replay_projection": {
        "disposition": "logical_suppress_preserve_lineage",
        "retentionClass": "append_only_correction_history",
    },
    "private_submission": {
        "disposition": "physical_delete_candidate",
        "retentionClass": "delete_on_verified_request_or_policy_expiry",
    },
    "temporary_transcript": {
        "disposition": "physical_delete_candidate",
        "retentionClass": "delete_on_verified_request_or_policy_expiry",
    },
    "runner_profile": {
        "disposition": "physical_delete_candidate",
        "retentionClass": "delete_on_verified_request",
    },
    "nonce_replay_record": {
        "disposition": "physical_delete_candidate",
        "retentionClass": "expire_after_replay_window",
    },
    "operational_event": {
        "disposition": "hold_for_policy_review",
        "retentionClass": "production_policy_required",
    },
    "synthetic_probe": {
        "disposition": "physical_delete_candidate",
        "retentionClass": "delete_after_drill",
    },
}

DELETION_REASONS = frozenset(
    (
        "verified_request_fixture",
        "policy_expiry_fixture",
        "test_cleanup_fixture",
        "erroneous_disclosure_fixture",
    )
)
ROLLBACK_TRIGGERS = frozenset(
    (
        "integrity_failure_fixture",
        "source_mismatch_fixture",
        "secret_exposure_fixture",
        "deletion_failure_fixture",
        "operator_request_fixture",
    )
)
RECOVERY_FAILURES = frozenset(
    (
        "none",
        "snapshot_unavailable",
        "artifact_restore_failure",
        "verification_failure",
        "cleanup_failure",
    )
)

PRODUCTION_AUTHORITY = {
    "productionDataRead": False,
    "productionDeletionExecuted": False,
    "productionBackupConfigured": False,
    "productionSnapshotRead": False,
    "productionRestoreExecuted": False,
    "rollbackExecuted": False,
    "protectedFlagsMutated": False,
    "deploymentMutated": False,
    "externalStorageConfigured": False,
    "operatorAuthority": False,
    "launchable": False,
}

ROLLBACK_ACTION_SEQUENCE = (
    "hold_release",
    "select_last_known_good_digest_manifest",
    "simulate_artifact_restore",
    "reverify_source_tree_artifact_verifier_configuration",
    "record_cleanup",
)
ROLLBACK_VALIDATION_SEQUENCE = (
    "source_commit_matches",
    "source_tree_matches",
    "artifact_digest_matches",
    "verifier_digest_matches",
    "configuration_digest_matches",
    "cleanup_recorded",
)


class RetentionRecoveryError(ValueError):
    """Raised when a retention, deletion, rollback, or recovery input drifts."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _exact(value: object, fields: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise RetentionRecoveryError(f"{label} fields drift")
    return value


def _match(value: object, pattern: re.Pattern[str], label: str) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise RetentionRecoveryError(f"{label} is malformed")
    return value


def _timestamp(value: object, label: str) -> datetime:
    if type(value) is not str or UTC_SECOND_RE.fullmatch(value) is None:
        raise RetentionRecoveryError(f"{label} must be a UTC whole-second timestamp")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise RetentionRecoveryError(f"{label} is not a valid timestamp") from error


def _authority(value: object, label: str) -> dict[str, bool]:
    if (
        type(value) is not dict
        or set(value) != set(PRODUCTION_AUTHORITY)
        or any(type(flag) is not bool or flag is not False for flag in value.values())
    ):
        raise RetentionRecoveryError(f"{label} production authority drift")
    return dict(PRODUCTION_AUTHORITY)


def _verify_digest(value: dict[str, object], field: str, label: str) -> None:
    supplied = value.get(field)
    if type(supplied) is not str or HEX64_RE.fullmatch(supplied) is None:
        raise RetentionRecoveryError(f"{label} digest is malformed")
    unsigned = dict(value)
    unsigned.pop(field)
    if digest(unsigned) != supplied:
        raise RetentionRecoveryError(f"{label} digest mismatch")


def retention_recovery_contract() -> dict[str, object]:
    contract: dict[str, object] = {
        "schemaVersion": CONTRACT_SCHEMA,
        "contractStatus": "local_contract_only_not_integrated",
        "resourcePolicies": {name: dict(policy) for name, policy in RESOURCE_POLICIES.items()},
        "deletionReasons": sorted(DELETION_REASONS),
        "rollbackTriggers": sorted(ROLLBACK_TRIGGERS),
        "recoveryFailureFixtures": sorted(RECOVERY_FAILURES),
        "rollbackActionSequence": list(ROLLBACK_ACTION_SEQUENCE),
        "rollbackValidationSequence": list(ROLLBACK_VALIDATION_SEQUENCE),
        "productionPolicyApproved": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    contract["contractDigest"] = digest(contract)
    return contract


def build_inventory(resources: Iterable[Mapping[str, object]], observed_at: str) -> dict[str, object]:
    cutoff = _timestamp(observed_at, "observedAt")
    normalized: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, candidate in enumerate(resources):
        row = _exact(
            candidate,
            {"resourceId", "resourceClass", "tenantRef", "contentDigest", "createdAt", "lifecycleState"},
            f"resource[{index}]",
        )
        resource_id = _match(row["resourceId"], RESOURCE_ID_RE, f"resource[{index}].resourceId")
        if resource_id in seen:
            raise RetentionRecoveryError("inventory resource ids must be unique")
        resource_class = row["resourceClass"]
        if type(resource_class) is not str or resource_class not in RESOURCE_POLICIES:
            raise RetentionRecoveryError("inventory resource class is unsupported")
        created = _timestamp(row["createdAt"], f"resource[{index}].createdAt")
        if created > cutoff:
            raise RetentionRecoveryError("inventory resource occurs after observation cutoff")
        if row["lifecycleState"] != "present":
            raise RetentionRecoveryError("inventory accepts present resources only")
        normalized.append(
            {
                "resourceId": resource_id,
                "resourceClass": resource_class,
                "tenantRef": _match(row["tenantRef"], TENANT_REF_RE, f"resource[{index}].tenantRef"),
                "contentDigest": _match(row["contentDigest"], HEX64_RE, f"resource[{index}].contentDigest"),
                "createdAt": row["createdAt"],
                "lifecycleState": "present",
            }
        )
        seen.add(resource_id)
    if normalized != sorted(normalized, key=lambda item: str(item["resourceId"])):
        raise RetentionRecoveryError("inventory resources must be sorted by resource id")
    inventory: dict[str, object] = {
        "schemaVersion": INVENTORY_SCHEMA,
        "observedAt": observed_at,
        "sourceStatus": "synthetic_digest_manifest_in_memory_only",
        "resources": normalized,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    inventory["inventoryDigest"] = digest(inventory)
    return inventory


def _validate_inventory(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {"schemaVersion", "observedAt", "sourceStatus", "resources", "productionAuthority", "inventoryDigest"},
        "inventory",
    )
    if row["schemaVersion"] != INVENTORY_SCHEMA or row["sourceStatus"] != "synthetic_digest_manifest_in_memory_only":
        raise RetentionRecoveryError("inventory schema or source status is unsupported")
    _authority(row["productionAuthority"], "inventory")
    if type(row["resources"]) is not list:
        raise RetentionRecoveryError("inventory resources must be a list")
    rebuilt = build_inventory(row["resources"], str(row["observedAt"]))
    if rebuilt != row:
        raise RetentionRecoveryError("inventory does not match its canonical reconstruction")
    return row


def build_deletion_request(
    *, request_id: str, requested_at: str, tenant_ref: str, resource_ids: Iterable[str], reason: str
) -> dict[str, object]:
    _match(request_id, REQUEST_ID_RE, "requestId")
    _timestamp(requested_at, "requestedAt")
    _match(tenant_ref, TENANT_REF_RE, "tenantRef")
    ids = list(resource_ids)
    if not ids or ids != sorted(set(ids)):
        raise RetentionRecoveryError("deletion resource ids must be non-empty, sorted, and unique")
    for resource_id in ids:
        _match(resource_id, RESOURCE_ID_RE, "resourceId")
    if reason not in DELETION_REASONS:
        raise RetentionRecoveryError("deletion reason is unsupported")
    request: dict[str, object] = {
        "schemaVersion": DELETION_REQUEST_SCHEMA,
        "requestId": request_id,
        "requestedAt": requested_at,
        "tenantRef": tenant_ref,
        "resourceIds": ids,
        "reason": reason,
        "authorizationStatus": "synthetic_fixture_only_not_identity_or_consent",
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    request["requestDigest"] = digest(request)
    return request


def _validate_deletion_request(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "requestId", "requestedAt", "tenantRef", "resourceIds", "reason",
            "authorizationStatus", "productionAuthority", "requestDigest",
        },
        "deletion request",
    )
    if row["schemaVersion"] != DELETION_REQUEST_SCHEMA:
        raise RetentionRecoveryError("deletion request schema is unsupported")
    if row["authorizationStatus"] != "synthetic_fixture_only_not_identity_or_consent":
        raise RetentionRecoveryError("deletion request cannot claim authorization")
    _authority(row["productionAuthority"], "deletion request")
    rebuilt = build_deletion_request(
        request_id=str(row["requestId"]),
        requested_at=str(row["requestedAt"]),
        tenant_ref=str(row["tenantRef"]),
        resource_ids=row["resourceIds"] if type(row["resourceIds"]) is list else [],
        reason=str(row["reason"]),
    )
    if rebuilt != row:
        raise RetentionRecoveryError("deletion request does not match its canonical reconstruction")
    return row


def plan_deletion(*, plan_id: str, planned_at: str, inventory: object, request: object) -> dict[str, object]:
    _match(plan_id, PLAN_ID_RE, "planId")
    planned = _timestamp(planned_at, "plannedAt")
    source = _validate_inventory(inventory)
    deletion = _validate_deletion_request(request)
    if planned < _timestamp(deletion["requestedAt"], "requestedAt"):
        raise RetentionRecoveryError("deletion plan predates its request")
    by_id = {str(item["resourceId"]): item for item in source["resources"]}
    actions: list[dict[str, object]] = []
    policy_hold = False
    for resource_id in deletion["resourceIds"]:
        resource = by_id.get(str(resource_id))
        if resource is None:
            raise RetentionRecoveryError("deletion request names an absent resource")
        if resource["tenantRef"] != deletion["tenantRef"]:
            raise RetentionRecoveryError("deletion request crosses tenant scope")
        policy = RESOURCE_POLICIES[str(resource["resourceClass"])]
        disposition = policy["disposition"]
        if disposition == "physical_delete_candidate":
            action = "simulate_physical_delete"
        elif disposition == "logical_suppress_preserve_lineage":
            action = "simulate_logical_suppression"
        else:
            action = "hold_for_policy_review"
            policy_hold = True
        actions.append(
            {
                "resourceId": resource_id,
                "resourceClass": resource["resourceClass"],
                "contentDigest": resource["contentDigest"],
                "action": action,
            }
        )
    plan: dict[str, object] = {
        "schemaVersion": DELETION_PLAN_SCHEMA,
        "planId": plan_id,
        "plannedAt": planned_at,
        "inventoryDigest": source["inventoryDigest"],
        "requestDigest": deletion["requestDigest"],
        "decision": "HELD_POLICY_REVIEW" if policy_hold else "LOCAL_DRILL_ONLY",
        "atomicity": "all_or_none_in_memory_simulation",
        "actions": actions,
        "actionsExecuted": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    plan["planDigest"] = digest(plan)
    return plan


def _validate_deletion_plan(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "planId", "plannedAt", "inventoryDigest", "requestDigest", "decision",
            "atomicity", "actions", "actionsExecuted", "productionAuthority", "planDigest",
        },
        "deletion plan",
    )
    if row["schemaVersion"] != DELETION_PLAN_SCHEMA:
        raise RetentionRecoveryError("deletion plan schema is unsupported")
    _match(row["planId"], PLAN_ID_RE, "planId")
    _timestamp(row["plannedAt"], "plannedAt")
    _match(row["inventoryDigest"], HEX64_RE, "inventoryDigest")
    _match(row["requestDigest"], HEX64_RE, "requestDigest")
    if row["decision"] not in {"HELD_POLICY_REVIEW", "LOCAL_DRILL_ONLY"}:
        raise RetentionRecoveryError("deletion plan decision is unsupported")
    if row["atomicity"] != "all_or_none_in_memory_simulation" or row["actionsExecuted"] is not False:
        raise RetentionRecoveryError("deletion plan cannot claim execution")
    if type(row["actions"]) is not list or not row["actions"]:
        raise RetentionRecoveryError("deletion plan actions must be non-empty")
    for action in row["actions"]:
        item = _exact(action, {"resourceId", "resourceClass", "contentDigest", "action"}, "deletion action")
        _match(item["resourceId"], RESOURCE_ID_RE, "deletion action resourceId")
        _match(item["contentDigest"], HEX64_RE, "deletion action contentDigest")
        if item["resourceClass"] not in RESOURCE_POLICIES:
            raise RetentionRecoveryError("deletion action resource class is unsupported")
        expected = RESOURCE_POLICIES[str(item["resourceClass"])]["disposition"]
        expected_action = {
            "physical_delete_candidate": "simulate_physical_delete",
            "logical_suppress_preserve_lineage": "simulate_logical_suppression",
            "hold_for_policy_review": "hold_for_policy_review",
        }[expected]
        if item["action"] != expected_action:
            raise RetentionRecoveryError("deletion action conflicts with the resource policy")
    has_hold = any(item["action"] == "hold_for_policy_review" for item in row["actions"])
    if has_hold is not (row["decision"] == "HELD_POLICY_REVIEW"):
        raise RetentionRecoveryError("deletion plan policy-hold decision is inconsistent")
    _authority(row["productionAuthority"], "deletion plan")
    _verify_digest(row, "planDigest", "deletion plan")
    return row


def execute_deletion_drill(
    *, plan: object, inventory: object, request: object, injected_failure_resource_ids: Iterable[str] = ()
) -> dict[str, object]:
    deletion_plan = _validate_deletion_plan(plan)
    source = _validate_inventory(inventory)
    deletion = _validate_deletion_request(request)
    if deletion_plan["inventoryDigest"] != source["inventoryDigest"] or deletion_plan["requestDigest"] != deletion["requestDigest"]:
        raise RetentionRecoveryError("deletion drill bindings drift")
    reconstructed = plan_deletion(
        plan_id=str(deletion_plan["planId"]),
        planned_at=str(deletion_plan["plannedAt"]),
        inventory=source,
        request=deletion,
    )
    if reconstructed != deletion_plan:
        raise RetentionRecoveryError("deletion drill plan does not match inventory and request")
    failures = list(injected_failure_resource_ids)
    if failures != sorted(set(failures)):
        raise RetentionRecoveryError("injected deletion failures must be sorted and unique")
    planned_ids = {str(item["resourceId"]) for item in deletion_plan["actions"]}
    for resource_id in failures:
        _match(resource_id, RESOURCE_ID_RE, "injected failure resourceId")
        if resource_id not in planned_ids:
            raise RetentionRecoveryError("injected deletion failure is outside the plan")

    physical = sum(item["action"] == "simulate_physical_delete" for item in deletion_plan["actions"])
    suppress = sum(item["action"] == "simulate_logical_suppression" for item in deletion_plan["actions"])
    if deletion_plan["decision"] == "HELD_POLICY_REVIEW":
        status = "DRILL_HELD_POLICY_REVIEW"
        applied = 0
        outcome = "no_simulated_action_policy_review_required"
    elif failures:
        status = "DRILL_REFUSED_INJECTED_FAILURE"
        applied = 0
        outcome = "atomic_simulation_refused_no_actions_applied"
    else:
        status = "DRILL_PASS"
        applied = len(deletion_plan["actions"])
        outcome = "targets_absent_or_suppressed_in_memory_only"
    post_state = {
        "sourceInventoryDigest": source["inventoryDigest"],
        "plannedResourceIds": sorted(planned_ids),
        "simulatedPhysicalDeleteCount": physical if applied else 0,
        "simulatedLogicalSuppressCount": suppress if applied else 0,
        "retainedLineageDigestCount": suppress if applied else 0,
        "appliedCount": applied,
        "outcome": outcome,
    }
    receipt: dict[str, object] = {
        "schemaVersion": DELETION_RECEIPT_SCHEMA,
        "planDigest": deletion_plan["planDigest"],
        "requestDigest": deletion["requestDigest"],
        "sourceInventoryDigest": source["inventoryDigest"],
        "status": status,
        "plannedActionCount": len(deletion_plan["actions"]),
        "appliedActionCount": applied,
        "injectedFailureCount": len(failures),
        "postStateDigest": digest(post_state),
        "postStateSummary": post_state,
        "productionDeletionProven": False,
        "actionsExecutedInProduction": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    receipt["receiptDigest"] = digest(receipt)
    return receipt


def build_release_manifest(
    *, release_id: str, observed_at: str, source_commit: str, source_tree: str,
    artifact_digest: str, verifier_digest: str, configuration_digest: str
) -> dict[str, object]:
    _match(release_id, RELEASE_ID_RE, "releaseId")
    _timestamp(observed_at, "observedAt")
    manifest: dict[str, object] = {
        "schemaVersion": RELEASE_SCHEMA,
        "releaseId": release_id,
        "observedAt": observed_at,
        "sourceCommit": _match(source_commit, HEX40_RE, "sourceCommit"),
        "sourceTree": _match(source_tree, HEX40_RE, "sourceTree"),
        "artifactDigest": _match(artifact_digest, HEX64_RE, "artifactDigest"),
        "verifierDigest": _match(verifier_digest, HEX64_RE, "verifierDigest"),
        "configurationDigest": _match(configuration_digest, HEX64_RE, "configurationDigest"),
        "environmentClass": "local_fixture_only",
        "deploymentStatus": "not_deployed",
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    manifest["releaseDigest"] = digest(manifest)
    return manifest


def _validate_release(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "releaseId", "observedAt", "sourceCommit", "sourceTree", "artifactDigest",
            "verifierDigest", "configurationDigest", "environmentClass", "deploymentStatus",
            "productionAuthority", "releaseDigest",
        },
        "release manifest",
    )
    if row["schemaVersion"] != RELEASE_SCHEMA or row["environmentClass"] != "local_fixture_only" or row["deploymentStatus"] != "not_deployed":
        raise RetentionRecoveryError("release manifest cannot claim a deployment")
    _authority(row["productionAuthority"], "release manifest")
    rebuilt = build_release_manifest(
        release_id=str(row["releaseId"]), observed_at=str(row["observedAt"]),
        source_commit=str(row["sourceCommit"]), source_tree=str(row["sourceTree"]),
        artifact_digest=str(row["artifactDigest"]), verifier_digest=str(row["verifierDigest"]),
        configuration_digest=str(row["configurationDigest"]),
    )
    if rebuilt != row:
        raise RetentionRecoveryError("release manifest does not match its canonical reconstruction")
    return row


def build_recovery_snapshot(*, snapshot_id: str, captured_at: str, release: object) -> dict[str, object]:
    _match(snapshot_id, SNAPSHOT_ID_RE, "snapshotId")
    captured = _timestamp(captured_at, "capturedAt")
    manifest = _validate_release(release)
    if captured < _timestamp(manifest["observedAt"], "observedAt"):
        raise RetentionRecoveryError("recovery snapshot predates the release manifest")
    snapshot: dict[str, object] = {
        "schemaVersion": SNAPSHOT_SCHEMA,
        "snapshotId": snapshot_id,
        "capturedAt": captured_at,
        "releaseDigest": manifest["releaseDigest"],
        "sourceCommit": manifest["sourceCommit"],
        "sourceTree": manifest["sourceTree"],
        "artifactDigest": manifest["artifactDigest"],
        "verifierDigest": manifest["verifierDigest"],
        "configurationDigest": manifest["configurationDigest"],
        "storageStatus": "digest_manifest_only_no_backup_created",
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    snapshot["snapshotDigest"] = digest(snapshot)
    return snapshot


def _validate_snapshot(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "snapshotId", "capturedAt", "releaseDigest", "sourceCommit", "sourceTree",
            "artifactDigest", "verifierDigest", "configurationDigest", "storageStatus",
            "productionAuthority", "snapshotDigest",
        },
        "recovery snapshot",
    )
    if row["schemaVersion"] != SNAPSHOT_SCHEMA or row["storageStatus"] != "digest_manifest_only_no_backup_created":
        raise RetentionRecoveryError("recovery snapshot cannot claim a backup")
    _match(row["snapshotId"], SNAPSHOT_ID_RE, "snapshotId")
    _timestamp(row["capturedAt"], "capturedAt")
    for field, pattern in (("releaseDigest", HEX64_RE), ("sourceCommit", HEX40_RE), ("sourceTree", HEX40_RE),
                           ("artifactDigest", HEX64_RE), ("verifierDigest", HEX64_RE), ("configurationDigest", HEX64_RE)):
        _match(row[field], pattern, field)
    _authority(row["productionAuthority"], "recovery snapshot")
    _verify_digest(row, "snapshotDigest", "recovery snapshot")
    return row


def plan_rollback(
    *, plan_id: str, planned_at: str, trigger: str, current_release: object, last_known_good: object
) -> dict[str, object]:
    _match(plan_id, ROLLBACK_ID_RE, "planId")
    planned = _timestamp(planned_at, "plannedAt")
    current = _validate_release(current_release)
    snapshot = _validate_snapshot(last_known_good)
    if trigger not in ROLLBACK_TRIGGERS:
        raise RetentionRecoveryError("rollback trigger is unsupported")
    if snapshot["releaseDigest"] == current["releaseDigest"]:
        raise RetentionRecoveryError("last-known-good target must differ from the current release")
    if planned < _timestamp(current["observedAt"], "current observedAt") or planned < _timestamp(snapshot["capturedAt"], "snapshot capturedAt"):
        raise RetentionRecoveryError("rollback plan predates its source manifests")
    plan: dict[str, object] = {
        "schemaVersion": ROLLBACK_PLAN_SCHEMA,
        "planId": plan_id,
        "plannedAt": planned_at,
        "trigger": trigger,
        "currentReleaseDigest": current["releaseDigest"],
        "recoverySnapshotDigest": snapshot["snapshotDigest"],
        "restoreTarget": {
            "sourceCommit": snapshot["sourceCommit"],
            "sourceTree": snapshot["sourceTree"],
            "artifactDigest": snapshot["artifactDigest"],
            "verifierDigest": snapshot["verifierDigest"],
            "configurationDigest": snapshot["configurationDigest"],
        },
        "actionSequence": list(ROLLBACK_ACTION_SEQUENCE),
        "validationSequence": list(ROLLBACK_VALIDATION_SEQUENCE),
        "planStatus": "local_simulation_only_not_executed",
        "actionsExecuted": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    plan["planDigest"] = digest(plan)
    return plan


def _validate_rollback_plan(value: object) -> dict[str, object]:
    row = _exact(
        value,
        {
            "schemaVersion", "planId", "plannedAt", "trigger", "currentReleaseDigest",
            "recoverySnapshotDigest", "restoreTarget", "actionSequence", "validationSequence",
            "planStatus", "actionsExecuted", "productionAuthority", "planDigest",
        },
        "rollback plan",
    )
    if row["schemaVersion"] != ROLLBACK_PLAN_SCHEMA or row["planStatus"] != "local_simulation_only_not_executed":
        raise RetentionRecoveryError("rollback plan cannot claim execution")
    _match(row["planId"], ROLLBACK_ID_RE, "planId")
    _timestamp(row["plannedAt"], "plannedAt")
    if row["trigger"] not in ROLLBACK_TRIGGERS:
        raise RetentionRecoveryError("rollback plan trigger is unsupported")
    _match(row["currentReleaseDigest"], HEX64_RE, "currentReleaseDigest")
    _match(row["recoverySnapshotDigest"], HEX64_RE, "recoverySnapshotDigest")
    target = _exact(
        row["restoreTarget"],
        {"sourceCommit", "sourceTree", "artifactDigest", "verifierDigest", "configurationDigest"},
        "restore target",
    )
    for field, pattern in (("sourceCommit", HEX40_RE), ("sourceTree", HEX40_RE), ("artifactDigest", HEX64_RE),
                           ("verifierDigest", HEX64_RE), ("configurationDigest", HEX64_RE)):
        _match(target[field], pattern, f"restore target {field}")
    if row["actionSequence"] != list(ROLLBACK_ACTION_SEQUENCE) or row["validationSequence"] != list(ROLLBACK_VALIDATION_SEQUENCE):
        raise RetentionRecoveryError("rollback plan sequence drift")
    if row["actionsExecuted"] is not False:
        raise RetentionRecoveryError("rollback plan cannot claim actions executed")
    _authority(row["productionAuthority"], "rollback plan")
    _verify_digest(row, "planDigest", "rollback plan")
    return row


def execute_recovery_drill(
    *, plan: object, current_release: object, last_known_good: object, injected_failure: str = "none"
) -> dict[str, object]:
    rollback = _validate_rollback_plan(plan)
    current = _validate_release(current_release)
    snapshot = _validate_snapshot(last_known_good)
    if rollback["currentReleaseDigest"] != current["releaseDigest"] or rollback["recoverySnapshotDigest"] != snapshot["snapshotDigest"]:
        raise RetentionRecoveryError("recovery drill bindings drift")
    reconstructed = plan_rollback(
        plan_id=str(rollback["planId"]),
        planned_at=str(rollback["plannedAt"]),
        trigger=str(rollback["trigger"]),
        current_release=current,
        last_known_good=snapshot,
    )
    if reconstructed != rollback:
        raise RetentionRecoveryError("recovery drill plan does not match its source manifests")
    expected_target = {
        "sourceCommit": snapshot["sourceCommit"],
        "sourceTree": snapshot["sourceTree"],
        "artifactDigest": snapshot["artifactDigest"],
        "verifierDigest": snapshot["verifierDigest"],
        "configurationDigest": snapshot["configurationDigest"],
    }
    if rollback["restoreTarget"] != expected_target:
        raise RetentionRecoveryError("recovery drill restore target drift")
    if injected_failure not in RECOVERY_FAILURES:
        raise RetentionRecoveryError("recovery failure fixture is unsupported")

    failed_step = {
        "none": None,
        "snapshot_unavailable": "select_last_known_good_digest_manifest",
        "artifact_restore_failure": "simulate_artifact_restore",
        "verification_failure": "reverify_source_tree_artifact_verifier_configuration",
        "cleanup_failure": "record_cleanup",
    }[injected_failure]
    passed = injected_failure == "none"
    validation = {
        item: passed for item in ROLLBACK_VALIDATION_SEQUENCE
    }
    if not passed:
        for item in ROLLBACK_VALIDATION_SEQUENCE:
            validation[item] = False
    post_state = {
        "targetDigest": digest(expected_target) if passed else None,
        "validationResults": validation,
        "failedStep": failed_step,
        "injectedFailure": injected_failure,
    }
    receipt: dict[str, object] = {
        "schemaVersion": RECOVERY_RECEIPT_SCHEMA,
        "planDigest": rollback["planDigest"],
        "currentReleaseDigest": current["releaseDigest"],
        "recoverySnapshotDigest": snapshot["snapshotDigest"],
        "status": "DRILL_PASS" if passed else "DRILL_REFUSED_INJECTED_FAILURE",
        "injectedFailure": injected_failure,
        "failedStep": failed_step,
        "validationResults": validation,
        "postStateDigest": digest(post_state),
        "productionRestoreProven": False,
        "rollbackExecutedInProduction": False,
        "actionsExecutedInProduction": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    receipt["receiptDigest"] = digest(receipt)
    return receipt
