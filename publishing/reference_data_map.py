"""Deterministic, source-bound reference data map for BuilderWars.

The map describes only the data surfaces implemented in this repository. It
performs no I/O and grants no production, legal, privacy, deletion, backup, or
launch authority. Unknown production facts stay visibly held for an operator
and appropriate reviewers to resolve against an exact deployment.
"""

from __future__ import annotations

import hashlib
import json

from publishing import retention_recovery


CONTRACT_SCHEMA = "builderwars.reference-data-map/1"

PRODUCTION_AUTHORITY = {
    "productionInventoryApproved": False,
    "processingPurposesApproved": False,
    "regionResidencyApproved": False,
    "subprocessorsApproved": False,
    "privacyObligationsApproved": False,
    "retentionPeriodsApproved": False,
    "deletionPropagationVerified": False,
    "externalBackupConfigured": False,
    "restoreVerified": False,
    "legalReviewCompleted": False,
    "publicLaunchApproved": False,
    "launchable": False,
}

REFERENCE_SYSTEMS = (
    {
        "systemId": "browser_local_arena",
        "label": "Mobile Arena browser-local state",
        "referenceImplementation": "mobile-arena/app.js",
        "productionStatus": "static_reference_only",
        "operatorOwner": "operator_required_not_recorded",
        "regionOrResidency": "browser_device_local_not_a_production_region_claim",
        "subprocessors": [],
    },
    {
        "systemId": "browser_static_cache",
        "label": "Mobile Arena service-worker cache",
        "referenceImplementation": "mobile-arena/sw.js",
        "productionStatus": "static_reference_only",
        "operatorOwner": "operator_required_not_recorded",
        "regionOrResidency": "browser_device_local_not_a_production_region_claim",
        "subprocessors": [],
    },
    {
        "systemId": "hosted_reference_store",
        "label": "Hosted control-plane SQLite reference",
        "referenceImplementation": "provider_hub_hosted/store.py",
        "productionStatus": "sqlite_reference_only_not_a_production_store",
        "operatorOwner": "operator_required_not_recorded",
        "regionOrResidency": "operator_required_not_recorded",
        "subprocessors": [],
    },
    {
        "systemId": "customer_local_runner",
        "label": "Customer-local runner and provider adapter boundary",
        "referenceImplementation": "provider_hub/local_runner.py",
        "productionStatus": "customer_local_reference_only",
        "operatorOwner": "customer_controls_local_endpoint",
        "regionOrResidency": "customer_device_local_not_a_production_region_claim",
        "subprocessors": [],
    },
    {
        "systemId": "reviewed_public_artifacts",
        "label": "Reviewed receipt, replay, proof, and share projections",
        "referenceImplementation": "docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json",
        "productionStatus": "repository_artifacts_only_not_public_hosting",
        "operatorOwner": "operator_required_not_recorded",
        "regionOrResidency": "repository_local_not_a_production_region_claim",
        "subprocessors": [],
    },
    {
        "systemId": "local_launch_evidence",
        "label": "Create-only local launch evidence packs",
        "referenceImplementation": "bin/build_agentwars_local_launch_evidence.py",
        "productionStatus": "local_evidence_only",
        "operatorOwner": "operator_required_not_recorded",
        "regionOrResidency": "local_worktree_not_a_production_region_claim",
        "subprocessors": [],
    },
)


def _data_set(
    data_set_id: str,
    system_id: str,
    reference_location: str,
    data_classes: tuple[str, ...],
    *,
    sensitivity: str,
    direct_identifiers: bool,
    secrets: bool,
    customer_local_only: bool,
    public_eligible: bool,
    retention_resource_class: str,
    production_status: str = "reference_only_not_production_configured",
) -> dict[str, object]:
    policy = retention_recovery.RESOURCE_POLICIES.get(retention_resource_class)
    return {
        "dataSetId": data_set_id,
        "systemId": system_id,
        "referenceLocation": reference_location,
        "dataClasses": list(data_classes),
        "sensitivity": sensitivity,
        "containsDirectIdentifiers": direct_identifiers,
        "containsSecrets": secrets,
        "customerLocalOnly": customer_local_only,
        "publicEligible": public_eligible,
        "retentionResourceClass": retention_resource_class,
        "retentionClass": policy["retentionClass"] if policy else "operator_required_not_recorded",
        "deletionDisposition": policy["disposition"] if policy else "operator_required_not_recorded",
        "productionStatus": production_status,
    }


DATA_SETS = (
    _data_set(
        "browser_starter_guide_state", "browser_local_arena",
        "localStorage:builderwars.mobile-arena.starter-guide.v1",
        ("completion_flag",), sensitivity="low", direct_identifiers=False,
        secrets=False, customer_local_only=True, public_eligible=False,
        retention_resource_class="synthetic_probe",
    ),
    _data_set(
        "browser_private_blueprint", "browser_local_arena",
        "localStorage:builderwars.mobile-arena.blueprint.v1",
        ("agent_label", "model_selection", "harness_selection", "guard_preferences"),
        sensitivity="private", direct_identifiers=False, secrets=False,
        customer_local_only=True, public_eligible=False,
        retention_resource_class="private_submission",
    ),
    _data_set(
        "browser_static_assets", "browser_static_cache",
        "CacheStorage:builderwars-mobile-arena-v41",
        ("static_html_css_javascript", "reviewed_public_fixture"), sensitivity="public",
        direct_identifiers=False, secrets=False, customer_local_only=True,
        public_eligible=True, retention_resource_class="public_replay_projection",
    ),
    _data_set(
        "hosted_owners", "hosted_reference_store", "sqlite:owners",
        ("opaque_owner_id", "created_timestamp"), sensitivity="pseudonymous",
        direct_identifiers=False, secrets=False, customer_local_only=False,
        public_eligible=False, retention_resource_class="runner_profile",
    ),
    _data_set(
        "hosted_pairing_challenges", "hosted_reference_store", "sqlite:pairing_challenges",
        ("opaque_owner_id", "pairing_secret_digest", "runner_public_key", "provider_label", "harness_lineage", "timestamps"),
        sensitivity="sensitive", direct_identifiers=False, secrets=True,
        customer_local_only=False, public_eligible=False,
        retention_resource_class="runner_profile",
    ),
    _data_set(
        "hosted_runners", "hosted_reference_store", "sqlite:runners",
        ("opaque_owner_id", "runner_public_key", "fingerprint", "provider_label", "harness_lineage", "state", "timestamps"),
        sensitivity="sensitive", direct_identifiers=False, secrets=False,
        customer_local_only=False, public_eligible=False,
        retention_resource_class="runner_profile",
    ),
    _data_set(
        "hosted_nonces", "hosted_reference_store", "sqlite:nonces",
        ("runner_fingerprint", "nonce", "request_digest", "timestamps"),
        sensitivity="sensitive", direct_identifiers=False, secrets=False,
        customer_local_only=False, public_eligible=False,
        retention_resource_class="nonce_replay_record",
    ),
    _data_set(
        "hosted_jobs", "hosted_reference_store", "sqlite:jobs",
        ("opaque_owner_id", "runner_id", "rules_and_engine_digests", "private_input_bytes", "state", "timestamps"),
        sensitivity="private", direct_identifiers=False, secrets=False,
        customer_local_only=False, public_eligible=False,
        retention_resource_class="private_submission",
    ),
    _data_set(
        "hosted_attempts", "hosted_reference_store", "sqlite:attempts",
        ("job_id", "runner_id", "lease_state", "timestamps"), sensitivity="internal",
        direct_identifiers=False, secrets=False, customer_local_only=False,
        public_eligible=False, retention_resource_class="operational_event",
    ),
    _data_set(
        "hosted_results", "hosted_reference_store", "sqlite:results",
        ("job_id", "attempt_id", "engine_output_and_transcript_digests", "conformance", "timestamp"),
        sensitivity="internal", direct_identifiers=False, secrets=False,
        customer_local_only=False, public_eligible=False,
        retention_resource_class="operational_event",
    ),
    _data_set(
        "hosted_replay_projections", "hosted_reference_store", "sqlite:replay_projections",
        ("job_id", "bounded_projection_json", "timestamp"), sensitivity="public_candidate",
        direct_identifiers=False, secrets=False, customer_local_only=False,
        public_eligible=False, retention_resource_class="public_replay_projection",
    ),
    _data_set(
        "hosted_browser_idempotency", "hosted_reference_store", "sqlite:browser_idempotency",
        ("opaque_owner_id", "idempotency_key", "request_digest", "sealed_response", "state", "timestamps"),
        sensitivity="sensitive", direct_identifiers=False, secrets=True,
        customer_local_only=False, public_eligible=False,
        retention_resource_class="operational_event",
    ),
    _data_set(
        "customer_provider_authority", "customer_local_runner", "customer-local provider CLI, token store, or pinned PKCE callback",
        ("provider_api_keys", "provider_access_and_refresh_tokens", "subscription_sessions", "billing_authority"),
        sensitivity="secret", direct_identifiers=True, secrets=True,
        customer_local_only=True, public_eligible=False,
        retention_resource_class="operator_required_not_recorded",
        production_status="must_never_enter_hosted_control_plane_or_public_artifacts",
    ),
    _data_set(
        "customer_pairing_secret", "customer_local_runner", "customer-local one-time pairing handoff",
        ("pairing_challenge_id", "random_pairing_code"), sensitivity="secret",
        direct_identifiers=False, secrets=True, customer_local_only=True,
        public_eligible=False, retention_resource_class="nonce_replay_record",
        production_status="one_time_customer_local_input_reference",
    ),
    _data_set(
        "temporary_runner_transcript", "customer_local_runner", "bounded in-memory or customer-local runner output",
        ("prompt_or_game_input", "model_output", "runtime_diagnostics"), sensitivity="private",
        direct_identifiers=False, secrets=False, customer_local_only=True,
        public_eligible=False, retention_resource_class="temporary_transcript",
    ),
    _data_set(
        "reviewed_public_receipt", "reviewed_public_artifacts", "reviewed receipt projection",
        ("receipt_digest", "rules_engine_and_source_digests", "bounded_labels", "review_decision"),
        sensitivity="public", direct_identifiers=False, secrets=False,
        customer_local_only=False, public_eligible=True,
        retention_resource_class="public_receipt_projection",
    ),
    _data_set(
        "reviewed_public_replay", "reviewed_public_artifacts", "reviewed replay and proof projection",
        ("replay_digest", "bounded_moves", "score", "correction_lineage"), sensitivity="public",
        direct_identifiers=False, secrets=False, customer_local_only=False,
        public_eligible=True, retention_resource_class="public_replay_projection",
    ),
    _data_set(
        "allowlisted_operational_event", "local_launch_evidence", "allowlisted observability event projection",
        ("event_name", "opaque_correlation_id", "status", "duration_bucket", "failure_code"),
        sensitivity="internal", direct_identifiers=False, secrets=False,
        customer_local_only=False, public_eligible=False,
        retention_resource_class="operational_event",
    ),
    _data_set(
        "synthetic_launch_probe", "local_launch_evidence", "output/launch-evidence/<source-commit>/",
        ("source_commit", "source_tree", "command_status", "file_digests", "protected_holds"),
        sensitivity="internal", direct_identifiers=False, secrets=False,
        customer_local_only=True, public_eligible=False,
        retention_resource_class="synthetic_probe",
    ),
)

DATA_FLOWS = (
    {
        "flowId": "DF-001", "sourceSystemId": "browser_local_arena",
        "destinationSystemId": "hosted_reference_store",
        "data": "future authenticated owner commands after protected adapter integration",
        "referenceChannel": "not_wired_in_static_mobile_reference",
        "control": "verified principal and exact gateway commands required",
        "productionStatus": "held_not_integrated",
    },
    {
        "flowId": "DF-002", "sourceSystemId": "customer_local_runner",
        "destinationSystemId": "hosted_reference_store",
        "data": "signed runner envelopes, digests, bounded results, and replay candidates",
        "referenceChannel": "pinned_origin_https_future_local_reference",
        "control": "exact signed bytes, nonce consumption, tenant and lease checks",
        "productionStatus": "reference_only",
    },
    {
        "flowId": "DF-003", "sourceSystemId": "customer_local_runner",
        "destinationSystemId": "customer_local_runner",
        "data": "provider credentials, subscription sessions, prompt, and model output",
        "referenceChannel": "customer_local_process_or_pinned_provider_origin",
        "control": "provider authority stays customer-local and is never a hosted input",
        "productionStatus": "customer_local_boundary_required",
    },
    {
        "flowId": "DF-004", "sourceSystemId": "hosted_reference_store",
        "destinationSystemId": "reviewed_public_artifacts",
        "data": "bounded receipt, replay, proof, and share projection",
        "referenceChannel": "explicit_reviewed_allowlist_only",
        "control": "private candidate, source decision, replay verification, and false-attestation refusal",
        "productionStatus": "repository_reference_only",
    },
    {
        "flowId": "DF-005", "sourceSystemId": "local_launch_evidence",
        "destinationSystemId": "reviewed_public_artifacts",
        "data": "source-bound proof metadata only after independent review",
        "referenceChannel": "create_only_local_pack",
        "control": "clean source, canonical digest, protected launch stages held",
        "productionStatus": "no_public_delivery_configured",
    },
)

PUBLIC_PROJECTION_ALLOWLIST = (
    "bounded_labels",
    "correction_lineage",
    "receipt_digest",
    "replay_digest",
    "review_decision",
    "rules_engine_and_source_digests",
    "score",
    "verified_bounded_moves",
)

PUBLIC_PROJECTION_DENYLIST = (
    "clerk_subject",
    "email_address",
    "input_bytes_base64url",
    "ip_address",
    "opaque_owner_id",
    "pairing_secret",
    "provider_access_token",
    "provider_api_key",
    "provider_refresh_token",
    "raw_model_output",
    "raw_prompt",
    "sealed_response",
    "subscription_cookie",
)

UNRESOLVED_PRODUCTION_FACTS = (
    {
        "factId": "UPF-001", "fact": "production_system_inventory_and_owners",
        "status": "operator_required_not_recorded", "requiredBefore": "protected_runtime_configuration",
    },
    {
        "factId": "UPF-002", "fact": "production_regions_residency_and_cross_border_transfers",
        "status": "operator_required_not_recorded", "requiredBefore": "protected_runtime_configuration",
    },
    {
        "factId": "UPF-003", "fact": "subprocessors_and_contractual_roles",
        "status": "operator_required_not_recorded", "requiredBefore": "protected_runtime_configuration",
    },
    {
        "factId": "UPF-004", "fact": "processing_purposes_legal_basis_privacy_notice_and_age_obligations",
        "status": "operator_and_qualified_review_required_not_recorded", "requiredBefore": "consented_tester_review",
    },
    {
        "factId": "UPF-005", "fact": "exact_retention_periods_and_policy_owners",
        "status": "operator_and_policy_review_required_not_recorded", "requiredBefore": "protected_runtime_configuration",
    },
    {
        "factId": "UPF-006", "fact": "deletion_propagation_targets_timing_and_dsar_process",
        "status": "operator_and_policy_review_required_not_recorded", "requiredBefore": "consented_tester_review",
    },
    {
        "factId": "UPF-007", "fact": "backup_destinations_encryption_access_retention_and_restore_rto_rpo",
        "status": "operator_required_not_recorded", "requiredBefore": "source_bound_deployment_and_rollback",
    },
    {
        "factId": "UPF-008", "fact": "production_observability_storage_sampling_and_support_access",
        "status": "operator_required_not_recorded", "requiredBefore": "protected_runtime_configuration",
    },
)

SOURCE_ANCHORS = (
    {"path": "mobile-arena/app.js", "symbol": "BLUEPRINT_STORAGE_KEY"},
    {"path": "mobile-arena/sw.js", "symbol": "CACHE_NAME"},
    {"path": "provider_hub_hosted/store.py", "symbol": "def _migrate"},
    {"path": "provider_hub/local_runner.py", "symbol": "def validate_origin"},
    {"path": "provider_hub/secrets.py", "symbol": "class SecretValue"},
    {"path": "publishing/promotion.py", "symbol": "FALSE_ATTESTATION_KEYS"},
    {"path": "publishing/source_decision.py", "symbol": "EXPECTED_AUTHORIZATIONS"},
    {"path": "publishing/retention_recovery.py", "symbol": "RESOURCE_POLICIES"},
    {"path": "docs/AGENTWARS_PUBLICATION_MANIFEST.v1.json", "symbol": "explicit_reviewed_allowlist_only"},
    {"path": "bin/build_agentwars_local_launch_evidence.py", "symbol": "HELD_PROTECTED"},
)


class ReferenceDataMapError(ValueError):
    """Raised when the reference data map drifts or claims authority."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _clone(value: object) -> object:
    return json.loads(canonical_bytes(value).decode("ascii"))


def reference_data_map_contract() -> dict[str, object]:
    contract: dict[str, object] = {
        "schemaVersion": CONTRACT_SCHEMA,
        "mapStatus": "SOURCE_BOUND_REFERENCE_CANDIDATE_PRODUCTION_FACTS_HELD",
        "scope": "repository_implemented_reference_surfaces_only",
        "systems": _clone(REFERENCE_SYSTEMS),
        "dataSets": _clone(DATA_SETS),
        "dataFlows": _clone(DATA_FLOWS),
        "publicProjectionAllowlist": list(PUBLIC_PROJECTION_ALLOWLIST),
        "publicProjectionDenylist": list(PUBLIC_PROJECTION_DENYLIST),
        "retentionContractSchema": retention_recovery.CONTRACT_SCHEMA,
        "retentionContractDigest": retention_recovery.retention_recovery_contract()["contractDigest"],
        "unresolvedProductionFacts": _clone(UNRESOLVED_PRODUCTION_FACTS),
        "sourceAnchors": _clone(SOURCE_ANCHORS),
        "invariants": [
            "provider_credentials_and_subscription_sessions_stay_customer_local",
            "hosted_reference_store_contains_no_raw_provider_credentials",
            "browser_blueprints_remain_local_only_unless_a_future_explicit_flow_is_reviewed",
            "public_artifacts_require_explicit_reviewed_allowlist_projection",
            "digests_do_not_prove_model_provider_identity_or_human_attestation",
            "reference_locations_are_not_production_storage_or_residency_claims",
        ],
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    contract["contractDigest"] = digest(contract)
    return contract


def verify_reference_data_map(value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise ReferenceDataMapError("reference data map must be an exact object")
    expected = reference_data_map_contract()
    if value != expected:
        raise ReferenceDataMapError("reference data map does not match the reviewed contract")
    authority = value.get("productionAuthority")
    if type(authority) is not dict or set(authority) != set(PRODUCTION_AUTHORITY):
        raise ReferenceDataMapError("reference data map production authority fields drift")
    if any(type(flag) is not bool or flag is not False for flag in authority.values()):
        raise ReferenceDataMapError("reference data map cannot claim production authority")
    return dict(value)
