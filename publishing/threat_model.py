"""Pure, repository-grounded BuilderWars threat-model contract.

The contract records launch risks and the local evidence anchors that justify
them. It performs no I/O and cannot attest production authentication, tenant
mapping, rate limits, secret custody, OS isolation, monitoring, deployment, or
security approval.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping


THREAT_MODEL_SCHEMA = "builderwars.threat-model/1"
ASSESSMENT_SCHEMA = "builderwars.local-security-assessment/1"
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

PRODUCTION_AUTHORITY = {
    "browserAuthenticationIntegrated": False,
    "tenantMappingExternallyVerified": False,
    "durableRateLimitsActive": False,
    "productionSecretCustodyVerified": False,
    "osIsolationEnforced": False,
    "productionStoreVerified": False,
    "monitoringAndAlertingActive": False,
    "externalPenetrationReviewCompleted": False,
    "deletionPropagationVerified": False,
    "sourceBoundDeploymentVerified": False,
    "securityLaunchApproved": False,
    "publicLaunch": False,
}

CONTEXT = {
    "intendedUsage": "public_multi_tenant_agent_competition_and_learning_beta",
    "deploymentModel": "protected_web_adapter_plus_hosted_control_plane_and_customer_local_runner",
    "dataSensitivity": "tenant_identifiers_runner_keys_receipt_digests_and_customer_owned_provider_authority",
    "internetExposure": "planned_public_browser_and_runner_endpoints_not_locally_proven",
    "authnAuthzExpectations": "clerk_authenticated_browser_owner_mapping_plus_ed25519_runner_requests",
    "scope": [
        "mobile-arena",
        "provider_hub",
        "provider_hub_hosted",
        "arena",
        "competitions",
        "publishing",
        "creator_sdk",
        "bin",
    ],
    "outOfScope": [
        "provider_internal_security",
        "customer_endpoint_security_outside_the_runner",
        "unimplemented_production_infrastructure",
        "builderwars_com_apex_and_www_mutation",
        "legal_or_terms_acceptance",
    ],
    "riskQualifier": "beta_scale_unknown_availability_and_abuse_rankings_are_conditional",
}

ASSUMPTIONS = (
    "The first protected release is a public multi-tenant beta rather than an internal-only service.",
    "A production web adapter verifies a Clerk session, constructs the reviewed principal input, and routes every owner command through the local authorization-gateway contract.",
    "Provider credentials and subscription sessions stay customer-local; the hosted control plane never receives raw provider secrets.",
    "Public arbitrary creator code and untrusted entrant execution remain disabled until an OS isolation profile is independently verified.",
    "Production state is expected to replace the local SQLite reference while preserving its tenant and transaction invariants.",
)

OPEN_QUESTIONS = (
    "What peak authenticated-user, runner, and public-spectator request rates define the beta capacity target?",
    "Which production regions, subprocessors, retention periods, and privacy obligations apply to the final data map?",
    "Will any launch phase admit third-party entrant or creator code, or only reviewed declarative games and customer-local harnesses?",
)


def _component(component_id: str, label: str, role: str, status: str, anchors: tuple[str, ...]) -> dict[str, object]:
    return {"componentId": component_id, "label": label, "role": role, "status": status, "evidenceAnchorIds": list(anchors)}


COMPONENTS = (
    _component("C-001", "Mobile Arena", "static local-first reader and builder shell", "implemented_local", ("EA-015",)),
    _component("C-002", "Browser authorization gateway", "maps an injected verified browser principal to an opaque owner id and exact owner command", "local_reference_production_integration_held", ("EA-001", "EA-017")),
    _component("C-003", "Hosted control plane", "framework-neutral pairing, runner, job, deletion, and replay handlers", "reference_implemented", ("EA-001", "EA-002")),
    _component("C-004", "Hosted state store", "transactional tenant, browser-idempotency, runner, nonce, lease, result, and projection state", "sqlite_reference_only", ("EA-003", "EA-004", "EA-006")),
    _component("C-005", "Runner verifier", "origin-bound Ed25519 request verification and durable nonce consumption", "implemented_local", ("EA-005", "EA-006")),
    _component("C-006", "Customer-local runner", "holds provider authority and invokes reviewed local provider adapters", "implemented_local", ("EA-007", "EA-008")),
    _component("C-007", "Arena referee", "deterministic game state, transcript, replay, and scoring", "implemented_local", ("EA-009",)),
    _component("C-008", "Entrant process boundary", "JSONL subprocess channel and process-tree cleanup", "partial_not_os_isolation", ("EA-009", "EA-010", "EA-011")),
    _component("C-009", "Publication pipeline", "private review candidate, source decision, bounded public projection", "implemented_local", ("EA-012", "EA-013")),
    _component("C-010", "Launch evidence builder", "source-bound local checks and protected launch holds", "implemented_local", ("EA-014", "EA-016")),
)


def _boundary(boundary_id: str, source: str, destination: str, data: str, channel: str, guarantees: tuple[str, ...], gaps: tuple[str, ...], anchors: tuple[str, ...]) -> dict[str, object]:
    return {
        "boundaryId": boundary_id,
        "source": source,
        "destination": destination,
        "data": data,
        "channel": channel,
        "guarantees": list(guarantees),
        "gaps": list(gaps),
        "evidenceAnchorIds": list(anchors),
    }


BOUNDARIES = (
    _boundary("B-001", "internet_browser", "browser_authorization_gateway", "session_and_customer_actions", "https_future", ("exact_origin", "canonical_csrf_pair", "strict_routes_and_bodies", "injected_verified_principal", "owner_scoped_local_rate_limit_reference", "owner_scoped_local_idempotency_reference", "aes256gcm_sealed_replay_response", "versioned_bounded_keyring_rotation_reference"), ("production_clerk_cookie_session_verifier_and_edge_limits_unproven", "durable_account_limits_owner_pepper_idempotency_key_custody_rotation_execution_and_store_parity_unproven"), ("EA-001", "EA-004", "EA-017")),
    _boundary("B-002", "browser_authorization_gateway", "hosted_control_plane", "opaque_owner_id_and_bounded_commands", "in_process_reference", ("hmac_derived_opaque_owner_id", "no_request_owner_id", "canonical_owner_id_validation", "uniform_foreign_object_errors"), ("live_clerk_subject_to_gateway_binding_and_direct_handler_non_exposure_unproven",), ("EA-001", "EA-002", "EA-017")),
    _boundary("B-003", "customer_local_runner", "runner_verifier", "signed_exact_method_path_body_timestamp_nonce", "https_future", ("ed25519_signature", "origin_binding", "timestamp_window", "durable_nonce_consumption"), ("tls_edge_and_perimeter_rate_limits_unproven",), ("EA-005", "EA-006", "EA-007")),
    _boundary("B-004", "hosted_control_plane", "hosted_state_store", "tenant_browser_idempotency_runner_nonce_lease_job_and_result_state", "sqlite_reference", ("exact_identifiers", "parameterized_queries", "foreign_keys", "begin_immediate_transactions", "nested_savepoint_atomicity", "browser_mutation_and_replay_record_same_transaction"), ("production_store_adapter_idempotency_parity_backup_and_capacity_unproven",), ("EA-003", "EA-004", "EA-006")),
    _boundary("B-005", "customer_local_runner", "provider_cli_or_pkce", "customer_owned_prompt_and_provider_authority", "local_subprocess_or_pinned_https", ("explicit_local_intent", "bounded_output", "redacted_secret_wrapper", "pinned_origin"), ("customer_machine_and_claude_environment_not_isolated", "provider_identity_and_billing_unattested"), ("EA-007", "EA-008")),
    _boundary("B-006", "arena_referee", "entrant_process", "arena_1_jsonl_moves_and_bounded_environment", "stdin_stdout_subprocess", ("scratch_cwd", "environment_allowlist", "timeouts", "output_caps", "process_tree_cleanup"), ("network_filesystem_cpu_and_memory_not_confined",), ("EA-009", "EA-010", "EA-011")),
    _boundary("B-007", "private_result", "public_projection", "receipt_replay_digests_labels_and_review_decision", "offline_files_and_reviewed_source", ("exact_schemas", "replay_verification", "false_attestations", "separate_source_decision"), ("production_reviewer_identity_registry_and_signing_unproven",), ("EA-012", "EA-013")),
    _boundary("B-008", "reviewed_source", "launch_evidence_pack", "commit_tree_commands_file_digests_and_protected_holds", "local_subprocess_and_json", ("clean_source_requirement", "closed_child_environment", "create_only_output", "canonical_digest"), ("remote_custody_deployment_binding_and_detached_signature_unproven",), ("EA-014", "EA-016")),
)


ASSETS = (
    {"assetId": "A-001", "asset": "tenant_principal_to_owner_mapping", "why": "A forged mapping enables cross-tenant control", "objectives": ["integrity", "confidentiality"]},
    {"assetId": "A-002", "asset": "pairing_secrets_runner_public_keys_and_fingerprints", "why": "They authorize durable runner enrollment and possession evidence", "objectives": ["confidentiality", "integrity"]},
    {"assetId": "A-003", "asset": "customer_provider_credentials_sessions_and_billing_authority", "why": "Exposure or confused use can compromise accounts or incur charges", "objectives": ["confidentiality", "integrity"]},
    {"assetId": "A-004", "asset": "tenant_runner_nonce_lease_job_and_result_state", "why": "Its integrity prevents replay, duplicate work, and tenant crossover", "objectives": ["integrity", "availability"]},
    {"assetId": "A-005", "asset": "rules_transcripts_replays_scores_and_receipt_lineage", "why": "These are the competitive truth and evaluation record", "objectives": ["integrity", "availability"]},
    {"assetId": "A-006", "asset": "review_publication_ranking_and_correction_decisions", "why": "Corruption can falsely promote or rank a result", "objectives": ["integrity"]},
    {"assetId": "A-007", "asset": "source_bundles_verifier_dependencies_and_launch_evidence", "why": "Substitution breaks every downstream proof claim", "objectives": ["integrity", "availability"]},
    {"assetId": "A-008", "asset": "compute_capacity_and_customer_cost_budget", "why": "Abuse can deny service or create unbounded local/provider cost", "objectives": ["availability", "integrity"]},
    {"assetId": "A-009", "asset": "deletion_rollback_incident_and_audit_receipts", "why": "They are required to contain and prove recovery from harm", "objectives": ["integrity", "availability", "confidentiality"]},
)


def _entry(entry_id: str, surface: str, reached: str, boundary: str, notes: str, anchors: tuple[str, ...]) -> dict[str, object]:
    return {"entryPointId": entry_id, "surface": surface, "reachedBy": reached, "boundaryId": boundary, "notes": notes, "evidenceAnchorIds": list(anchors)}


ENTRY_POINTS = (
    _entry("EP-001", "owner_authenticated_hosted_commands", "verified_browser_principal_reference", "B-001", "create confirm revoke delete and fixture operations pass the local gateway with local atomic retry replay but still require production Clerk and store parity", ("EA-001", "EA-002", "EA-004", "EA-017")),
    _entry("EP-002", "pairing_claim", "one_time_pairing_secret", "B-002", "exact JSON claim with TTL and attempt lock", ("EA-002", "EA-003")),
    _entry("EP-003", "signed_runner_commands", "runner_https_request", "B-003", "probe poll renew abandon and result paths use exact signed bytes", ("EA-005", "EA-006")),
    _entry("EP-004", "public_replay_projection", "public_job_identifier", "B-004", "returns a bounded result projection or not found", ("EA-002", "EA-012")),
    _entry("EP-005", "customer_local_provider_runner", "local_cli_and_provider_auth", "B-005", "provider authority stays on the customer machine", ("EA-007", "EA-008")),
    _entry("EP-006", "arena_entrant_manifest", "reviewed_subprocess_command", "B-006", "untrusted commands are not safe for shared hosting without a jail", ("EA-009", "EA-010")),
    _entry("EP-007", "private_review_and_source_decision", "bounded offline artifacts", "B-007", "review does not directly publish", ("EA-012", "EA-013")),
    _entry("EP-008", "local_launch_evidence_builder", "reviewed_source_and_bounded_checks", "B-008", "local success leaves three protected stages held", ("EA-014", "EA-016")),
)


EVIDENCE_ANCHORS = (
    {"anchorId": "EA-001", "path": "provider_hub_hosted/handlers.py", "symbol": "Callers are responsible for authenticating browser/account requests"},
    {"anchorId": "EA-002", "path": "provider_hub_hosted/handlers.py", "symbol": "class HostedControlPlane"},
    {"anchorId": "EA-003", "path": "provider_hub_hosted/store.py", "symbol": "PAIRING_MAX_CLAIM_ATTEMPTS = 8"},
    {"anchorId": "EA-004", "path": "provider_hub_hosted/store.py", "symbol": "BEGIN IMMEDIATE"},
    {"anchorId": "EA-005", "path": "provider_hub_hosted/verify.py", "symbol": "def verify_signed_request"},
    {"anchorId": "EA-006", "path": "provider_hub_hosted/store.py", "symbol": "def consume_nonce"},
    {"anchorId": "EA-007", "path": "provider_hub/local_runner.py", "symbol": "def validate_origin"},
    {"anchorId": "EA-008", "path": "provider_hub/secrets.py", "symbol": "class SecretValue"},
    {"anchorId": "EA-009", "path": "arena/sandbox.py", "symbol": "POLICY = {"},
    {"anchorId": "EA-010", "path": "arena/sandbox.py", "symbol": "network_egress_blocking"},
    {"anchorId": "EA-011", "path": "arena/process_tree.py", "symbol": "_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE"},
    {"anchorId": "EA-012", "path": "publishing/promotion.py", "symbol": "FALSE_ATTESTATION_KEYS"},
    {"anchorId": "EA-013", "path": "publishing/source_decision.py", "symbol": "EXPECTED_AUTHORIZATIONS"},
    {"anchorId": "EA-014", "path": "publishing/retention_recovery.py", "symbol": "PRODUCTION_AUTHORITY"},
    {"anchorId": "EA-015", "path": "mobile-arena/data-adapter.js", "symbol": "DEMO FALLBACK"},
    {"anchorId": "EA-016", "path": "bin/build_agentwars_local_launch_evidence.py", "symbol": "PROTECTED_STATUS = \"HELD_PROTECTED\""},
    {"anchorId": "EA-017", "path": "provider_hub_hosted/browser_gateway.py", "symbol": "class BrowserAuthorizationGateway"},
)


def _threat(
    threat_id: str,
    title: str,
    source: str,
    prerequisites: str,
    action: str,
    impact: str,
    assets: tuple[str, ...],
    boundaries: tuple[str, ...],
    entry_points: tuple[str, ...],
    controls: tuple[str, ...],
    gaps: tuple[str, ...],
    mitigations: tuple[str, ...],
    detection: tuple[str, ...],
    likelihood: str,
    likelihood_reason: str,
    impact_severity: str,
    impact_reason: str,
    priority: str,
) -> dict[str, object]:
    return {
        "threatId": threat_id,
        "title": title,
        "threatSource": source,
        "prerequisites": prerequisites,
        "threatAction": action,
        "impact": impact,
        "assetIds": list(assets),
        "boundaryIds": list(boundaries),
        "entryPointIds": list(entry_points),
        "existingControlAnchorIds": list(controls),
        "gaps": list(gaps),
        "recommendedMitigations": list(mitigations),
        "detectionIdeas": list(detection),
        "likelihood": {"rating": likelihood, "reason": likelihood_reason},
        "impactSeverity": {"rating": impact_severity, "reason": impact_reason},
        "priority": priority,
        "protectedHoldRequired": priority in {"critical", "high"},
    }


THREATS = (
    _threat(
        "TM-001", "Browser authentication or owner-mapping bypass", "remote unauthenticated attacker",
        "A production HTTP adapter exposes owner-scoped handlers and accepts an attacker-influenced owner id.",
        "Forge or confuse the authenticated-principal to owner-id mapping, then call pairing, job, revocation, or deletion methods as another tenant.",
        "Cross-tenant runner control, state deletion, unauthorized jobs, and privacy breach.",
        ("A-001", "A-002", "A-004", "A-009"), ("B-001", "B-002"), ("EP-001", "EP-002"),
        ("EA-001", "EA-002", "EA-004", "EA-017"),
        ("production_clerk_token_cookie_session_and_adapter_wiring_unproven", "durable_edge_account_limits_owner_pepper_idempotency_key_custody_rotation_execution_and_store_parity_unproven", "direct_handler_non_exposure_unproven"),
        ("Wire one deny-by-default production adapter that verifies Clerk and constructs the reviewed principal input.", "Provision the owner pepper and bounded active-retiring idempotency keyring through protected secret and state custody.", "Exercise staged overlap retirement rollback and disaster recovery without dropping an eligible replay key.", "Port the same-owner same-key same-request replay and mismatch-refusal transaction contract to the production store.", "Expose only the gateway for owner commands and keep uniform not-found responses for foreign tenant objects."),
        ("Alert on owner-mapping failures foreign-object probes and destructive-action spikes.", "Audit redacted subject-to-owner decisions with source and deployment digest."),
        "medium", "A local gateway reference now rejects request owner ids, bad origin, CSRF, stale principals, schema drift, limiter failure, idempotency mismatch, replay corruption, unknown key ids, and key-id substitution; likelihood becomes high if production bypasses it or trusts unverified principal data.",
        "high", "A single bypass can cross tenant boundaries and delete or control security-sensitive state.", "critical",
    ),
    _threat(
        "TM-002", "Cross-tenant state access through integration drift", "authenticated malicious tenant",
        "The production store or adapter weakens owner predicates or fails to preserve transactional invariants.",
        "Enumerate runner or job identifiers and exploit an unscoped read, update, revoke, or delete path.",
        "Disclosure or mutation of another tenant's runner, job, result, or cleanup state.",
        ("A-001", "A-002", "A-004", "A-009"), ("B-002", "B-004"), ("EP-001", "EP-003", "EP-004"),
        ("EA-002", "EA-004", "EA-006", "EA-017"),
        ("production_store_adapter_unimplemented", "external_multi_tenant_penetration_test_missing"),
        ("Port owner predicates and foreign-key semantics as conformance tests for the production adapter.", "Use tenant-scoped keys plus authorization at both adapter and store layers.", "Run cross-tenant fuzzing against every production route."),
        ("Count foreign-object denials by route without logging identifiers.", "Alert on unusual tenant-mismatch and destructive-operation rates."),
        "low", "The SQLite reference has strong owner checks and transaction tests, but production integration does not yet exist.",
        "high", "Successful exploitation compromises tenant confidentiality and integrity.", "high",
    ),
    _threat(
        "TM-003", "Runner request replay or origin confusion", "network attacker or malicious runner",
        "The attacker captures signed bytes or a deployment accepts signatures on the wrong origin, path, timestamp, or nonce store.",
        "Replay or redirect a valid runner command to duplicate work, submit a result, or cross a host boundary.",
        "Duplicate execution, stale result acceptance, or forged possession evidence.",
        ("A-002", "A-004", "A-005"), ("B-003", "B-004"), ("EP-003",),
        ("EA-005", "EA-006", "EA-007"),
        ("production_nonce_store_and_tls_edge_unproven",),
        ("Preserve atomic nonce consumption and exact origin binding in the production adapter.", "Reject redirects and require canonical timestamps methods paths and bodies."),
        ("Measure replay stale future signature and origin-mismatch refusals.", "Alert on nonce-store errors and repeated runner fingerprint failures."),
        "low", "The local verifier binds exact bytes and durably consumes nonce state; risk depends on production parity.",
        "high", "A bypass undermines runner possession and match integrity.", "medium",
    ),
    _threat(
        "TM-004", "Pairing brute force race or enrollment denial", "remote attacker",
        "The pairing claim route is internet exposed and perimeter limits are absent or inconsistent.",
        "Guess, race, or repeatedly submit pairing secrets to lock a legitimate challenge or enroll an attacker key.",
        "Runner enrollment denial or unauthorized runner binding.",
        ("A-002", "A-004", "A-008"), ("B-002", "B-004"), ("EP-002",),
        ("EA-003", "EA-004", "EA-017"),
        ("durable_per_ip_per_tenant_and_global_rate_limits_unproven",),
        ("Add layered per-IP per-challenge per-owner and global rate limits with bounded retry-after.", "Keep 600-second TTL hash-only storage one-winner transaction and attempt lock."),
        ("Track claim failures locks races and challenge creation volume.", "Alert on distributed low-rate guessing and lockout bursts."),
        "medium", "Secrets are high entropy and locally attempt-locked, but a public perimeter is not implemented.",
        "medium", "Likely impact is enrollment denial; secret compromise could bind an unauthorized runner.", "medium",
    ),
    _threat(
        "TM-005", "Entrant sandbox escape or host resource exhaustion", "malicious entrant or creator",
        "A shared or hosted environment executes attacker-controlled commands with the current process-only sandbox.",
        "Read host files, access the network, consume CPU or memory, or detach descendants beyond the intended match lifecycle.",
        "Credential theft, host compromise, lateral movement, service denial, or cost exhaustion.",
        ("A-003", "A-005", "A-007", "A-008"), ("B-006",), ("EP-006",),
        ("EA-009", "EA-010", "EA-011"),
        ("network_filesystem_cpu_memory_and_posix_escape_controls_absent",),
        ("Keep public arbitrary code disabled.", "Require disposable OS sandbox identity read-only root isolated workspace egress denylist or allowlist CPU memory process and wall limits.", "Independently test escape cleanup and quota enforcement before enablement."),
        ("Record sandbox profile digest resource-limit exits egress denials and descendant cleanup.", "Alert on limit pressure escape attempts and orphaned processes."),
        "low", "Attacker-controlled hosted commands are currently disabled; likelihood becomes high immediately if that gate opens.",
        "high", "Capability escape can expose host and customer assets or exhaust service capacity.", "high",
    ),
    _threat(
        "TM-006", "Provider credential leakage or unauthorized customer charges", "malicious artifact compromised local harness or integration bug",
        "Provider authority crosses from the customer machine into logs, receipts, environment inheritance, hosted storage, or an unintended billing route.",
        "Exfiltrate credentials or cause provider calls the customer did not freshly authorize.",
        "Provider account compromise, financial loss, terms violation, and loss of trust.",
        ("A-003", "A-005", "A-008"), ("B-005",), ("EP-005",),
        ("EA-007", "EA-008", "EA-012"),
        ("customer_endpoint_not_isolated", "claude_native_environment_inheritance_is_broad", "live_provider_consent_and_cost_receipts_unproven"),
        ("Keep secrets customer-local and never serialize provider auth stores.", "Require per-match cost ceiling fresh consent and explicit provider route display.", "Redact raw stderr and response bodies and rotate or revoke compromised links."),
        ("Expose local redacted cost and route receipts to the customer.", "Alert only on hosted anomalies without collecting provider secrets."),
        "medium", "The design strongly limits custody, but customer-local processes and broad native provider environments remain capable.",
        "high", "Credential loss or unintended billed calls directly harm customers.", "high",
    ),
    _threat(
        "TM-007", "Result publication ranking or lineage poisoning", "malicious runner reviewer or source contributor",
        "A forged or mismatched receipt bypasses replay, private review, source decision, or false-attestation boundaries.",
        "Promote an unattested or tampered result into public projection, ranking, rivalry, or share surfaces.",
        "False evaluation claims, unfair standings, reputational harm, and corrupted correction history.",
        ("A-005", "A-006", "A-007"), ("B-007", "B-008"), ("EP-004", "EP-007", "EP-008"),
        ("EA-012", "EA-013", "EA-016"),
        ("production_reviewer_identity_registry_signing_and_detached_acceptance_unproven",),
        ("Require receipt replay verifier and source-decision digests to agree before publication.", "Keep provider model person and execution attestations false unless separately signed.", "Use append-only corrections and detached reviewer keys."),
        ("Alert on digest disagreement replay failure attestation escalation and correction bursts.", "Continuously reverify public projections from source manifests."),
        "medium", "Multiple local gates exist, but production reviewer identity and registry custody are not active.",
        "high", "A poisoned public record attacks the core competitive-evaluation product.", "high",
    ),
    _threat(
        "TM-008", "Incomplete deletion retention or rollback propagation", "operator error integration bug or malicious tenant",
        "Production data spans stores queues caches logs analytics backups or derivatives not represented by the local reference.",
        "Trigger partial deletion or rollback that leaves sensitive data, deletes the wrong tenant, or loses evidence needed for recovery.",
        "Privacy harm, unavailable accounts, irrecoverable evidence, or false deletion claims.",
        ("A-001", "A-004", "A-006", "A-009"), ("B-004", "B-008"), ("EP-001", "EP-008"),
        ("EA-004", "EA-014", "EA-016"),
        ("production_data_map_retention_policy_backup_restore_and_propagation_unproven",),
        ("Approve a complete data inventory and per-class deletion or suppression policy.", "Implement idempotent tenant-scoped deletion with retry dead-letter and redacted receipts.", "Run supervised restore and rollback against an external backup."),
        ("Track deletion propagation lag retry exhaustion orphan counts and restore verification.", "Alert on partial state and post-delete access."),
        "medium", "The reference store is atomic, but the future production topology and policies are unknown.",
        "high", "Failures can expose tenant data or destroy evidence and availability.", "high",
    ),
    _threat(
        "TM-009", "Control-plane or spectator denial of service", "remote unauthenticated or authenticated attacker",
        "Public routes accept enough requests jobs or identifiers to exhaust application state CPU database locks or network capacity.",
        "Flood JSON parsing pairing job polling result submission or public replay lookups within individually valid bounds.",
        "Service unavailability queue starvation elevated cost or delayed cleanup.",
        ("A-004", "A-008", "A-009"), ("B-001", "B-003", "B-004"), ("EP-001", "EP-002", "EP-003", "EP-004"),
        ("EA-003", "EA-005", "EA-006", "EA-017"),
        ("production_capacity_concurrency_backpressure_and_rate_limits_unproven",),
        ("Set body header concurrency queue and tenant quotas at the edge and service.", "Use bounded public cache semantics and fail-closed backpressure.", "Load test authenticated and public routes at the named beta target."),
        ("Measure request class saturation lock time queue age rejection and error budgets.", "Alert before capacity or cost budgets are exceeded."),
        "medium", "Local bodies attempts leases timestamps and browser-mutation retries are bounded, but aggregate public abuse controls do not exist.",
        "medium", "Likely impact is bounded outage or cost rather than tenant compromise.", "medium",
    ),
    _threat(
        "TM-010", "Source dependency bundle or verifier substitution", "supply-chain attacker or compromised contributor",
        "A deployment or runner artifact is built from different source dependencies verifier or configuration than the reviewed evidence.",
        "Replace a bundle or verifier while retaining a misleading filename dashboard status or stale local pack.",
        "Silent code execution, false replay verification, invalid results, or unsafe production rollback.",
        ("A-005", "A-006", "A-007", "A-009"), ("B-008",), ("EP-008",),
        ("EA-013", "EA-014", "EA-016"),
        ("remote_custody_signed_release_provenance_served_byte_parity_and_production_signature_unproven",),
        ("Bind deployment artifact verifier dependencies and configuration to one reviewed commit and tree.", "Require create-only signed evidence and served-byte probes before promotion.", "Maintain last-known-good digests and rehearse rollback."),
        ("Continuously compare served artifact and verifier digests to the signed release manifest.", "Alert on dependency lock source tree or configuration drift."),
        "medium", "Local deterministic locks and packs exist, but remote custody and deployment parity are protected gaps.",
        "high", "Substitution invalidates the evaluation system and may execute attacker code.", "high",
    ),
)

CRITICALITY_CALIBRATION = {
    "critical": "A remotely reachable auth or isolation failure that can cross tenants, execute on the host, or expose provider authority before containment.",
    "high": "A credible path to tenant data mutation, credential or billed-provider harm, public evaluation corruption, destructive cleanup failure, or source substitution.",
    "medium": "A bounded replay, enrollment, or availability attack with meaningful impact but strong local controls or missing remote reachability.",
    "low": "A low-sensitivity disclosure or noisy failure requiring trusted local access and offering straightforward containment.",
}

FOCUS_PATHS = (
    {"path": "provider_hub_hosted/browser_gateway.py", "reason": "origin CSRF verified-principal owner derivation exact routes safe errors rate limits sealed idempotent replay and bounded key rotation", "threatIds": ["TM-001", "TM-002", "TM-004", "TM-009"]},
    {"path": "provider_hub_hosted/handlers.py", "reason": "external browser-auth boundary and destructive owner-scoped methods", "threatIds": ["TM-001", "TM-002", "TM-009"]},
    {"path": "provider_hub_hosted/store.py", "reason": "tenant predicates nested transactions idempotency nonces leases results and deletion", "threatIds": ["TM-001", "TM-002", "TM-003", "TM-004", "TM-008", "TM-009"]},
    {"path": "provider_hub_hosted/verify.py", "reason": "runner signature origin timestamp owner and nonce verification", "threatIds": ["TM-003"]},
    {"path": "provider_hub/local_runner.py", "reason": "pinned transport signed bodies and customer-local credential boundary", "threatIds": ["TM-003", "TM-006"]},
    {"path": "provider_hub/secrets.py", "reason": "secret redaction serialization refusal and explicit reveal sites", "threatIds": ["TM-006"]},
    {"path": "arena/sandbox.py", "reason": "subprocess protocol environment limits and explicitly unenforced isolation", "threatIds": ["TM-005", "TM-009"]},
    {"path": "arena/process_tree.py", "reason": "descendant lifecycle without CPU memory filesystem or network confinement", "threatIds": ["TM-005"]},
    {"path": "publishing/promotion.py", "reason": "private review projection size limits and false-attestation boundary", "threatIds": ["TM-006", "TM-007"]},
    {"path": "publishing/source_decision.py", "reason": "separate reviewed-source admission and mutation authorization", "threatIds": ["TM-007", "TM-010"]},
    {"path": "publishing/retention_recovery.py", "reason": "deletion suppression recovery and rollback truth boundary", "threatIds": ["TM-008", "TM-010"]},
    {"path": "bin/build_agentwars_local_launch_evidence.py", "reason": "source custody bounded child environment and protected launch holds", "threatIds": ["TM-008", "TM-010"]},
    {"path": "provider_hub_hosted/tests/test_control_plane.py", "reason": "reference conformance for tenant replay race rollback and cleanup behavior", "threatIds": ["TM-001", "TM-002", "TM-003", "TM-004", "TM-008", "TM-009"]},
    {"path": "provider_hub_hosted/tests/test_browser_idempotency.py", "reason": "same-request replay owner isolation concurrency rollback restart ciphertext tamper expiry and key rotation conformance", "threatIds": ["TM-001", "TM-008", "TM-009"]},
)

RESIDUAL_PROTECTED_GATES = (
    "production_browser_authentication_owner_mapping_pepper_idempotency_key_custody_rotation_execution_and_adapter_wiring",
    "production_store_tenant_nonce_and_browser_idempotency_conformance",
    "durable_edge_service_and_tenant_rate_limits",
    "production_secret_and_provider_consent_boundary",
    "os_level_untrusted_code_isolation_or_continued_disablement",
    "monitoring_alert_delivery_and_incident_staffing",
    "complete_data_map_deletion_propagation_backup_and_restore",
    "source_bound_deployment_served_byte_parity_and_rollback",
    "external_penetration_review_and_separate_security_acceptance",
)


class ThreatModelError(ValueError):
    """Raised when the BuilderWars threat model drifts or overclaims."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _clone(value: object) -> object:
    return json.loads(canonical_bytes(value).decode("ascii"))


def _authority(value: object, label: str) -> dict[str, bool]:
    if type(value) is not dict or set(value) != set(PRODUCTION_AUTHORITY):
        raise ThreatModelError(f"{label} production authority fields drift")
    if any(type(flag) is not bool or flag is not False for flag in value.values()):
        raise ThreatModelError(f"{label} cannot claim production authority")
    return dict(PRODUCTION_AUTHORITY)


def threat_model_contract() -> dict[str, object]:
    model: dict[str, object] = {
        "schemaVersion": THREAT_MODEL_SCHEMA,
        "modelStatus": "REPOSITORY_GROUNDED_LOCAL_MODEL_PROTECTED_GAPS_HELD",
        "context": _clone(CONTEXT),
        "components": _clone(COMPONENTS),
        "boundaries": _clone(BOUNDARIES),
        "assets": _clone(ASSETS),
        "entryPoints": _clone(ENTRY_POINTS),
        "evidenceAnchors": _clone(EVIDENCE_ANCHORS),
        "threats": _clone(THREATS),
        "criticalityCalibration": _clone(CRITICALITY_CALIBRATION),
        "focusPaths": _clone(FOCUS_PATHS),
        "assumptions": list(ASSUMPTIONS),
        "openQuestions": list(OPEN_QUESTIONS),
        "residualProtectedGates": list(RESIDUAL_PROTECTED_GATES),
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    model["contractDigest"] = digest(model)
    return model


def verify_threat_model(value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise ThreatModelError("threat model must be an exact object")
    expected = threat_model_contract()
    if value != expected:
        raise ThreatModelError("threat model does not match the reviewed contract")
    _authority(value.get("productionAuthority"), "threat model")
    return dict(value)


def build_local_security_assessment(
    *, source_commit: str, source_tree: str, observations: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    if type(source_commit) is not str or HEX40_RE.fullmatch(source_commit) is None:
        raise ThreatModelError("source commit is malformed")
    if type(source_tree) is not str or HEX40_RE.fullmatch(source_tree) is None:
        raise ThreatModelError("source tree is malformed")
    rows = list(observations)
    if len(rows) != len(EVIDENCE_ANCHORS):
        raise ThreatModelError("security assessment must cover every evidence anchor")
    normalized: list[dict[str, object]] = []
    for expected, candidate in zip(EVIDENCE_ANCHORS, rows, strict=True):
        if type(candidate) is not dict or set(candidate) != {
            "anchorId", "path", "symbol", "fileSha256", "anchorFound", "productionObserved"
        }:
            raise ThreatModelError("security evidence observation fields drift")
        for field in ("anchorId", "path", "symbol"):
            if candidate[field] != expected[field]:
                raise ThreatModelError("security evidence anchor order or identity drift")
        if type(candidate["fileSha256"]) is not str or HEX64_RE.fullmatch(candidate["fileSha256"]) is None:
            raise ThreatModelError("security evidence file digest is malformed")
        if candidate["anchorFound"] is not True:
            raise ThreatModelError("security evidence anchor is missing")
        if candidate["productionObserved"] is not False:
            raise ThreatModelError("local security evidence cannot claim production observation")
        normalized.append(dict(candidate))
    high_critical = [item["threatId"] for item in THREATS if item["priority"] in {"critical", "high"}]
    assessment: dict[str, object] = {
        "schemaVersion": ASSESSMENT_SCHEMA,
        "sourceCommit": source_commit,
        "sourceTree": source_tree,
        "threatModelDigest": threat_model_contract()["contractDigest"],
        "evidenceObservations": normalized,
        "evidenceObservationCount": len(normalized),
        "status": "LOCAL_THREAT_MODEL_PASS_PROTECTED_HELD",
        "highCriticalThreatIds": high_critical,
        "protectedThreatIds": high_critical,
        "residualProtectedGates": list(RESIDUAL_PROTECTED_GATES),
        "allEvidenceAnchorsFound": True,
        "productionSecurityApproved": False,
        "productionAuthority": dict(PRODUCTION_AUTHORITY),
    }
    assessment["assessmentDigest"] = digest(assessment)
    return assessment


def verify_local_security_assessment(value: object) -> dict[str, object]:
    if type(value) is not dict or set(value) != {
        "schemaVersion", "sourceCommit", "sourceTree", "threatModelDigest",
        "evidenceObservations", "evidenceObservationCount", "status",
        "highCriticalThreatIds", "protectedThreatIds", "residualProtectedGates",
        "allEvidenceAnchorsFound", "productionSecurityApproved", "productionAuthority",
        "assessmentDigest",
    }:
        raise ThreatModelError("local security assessment fields drift")
    if value["schemaVersion"] != ASSESSMENT_SCHEMA or value["status"] != "LOCAL_THREAT_MODEL_PASS_PROTECTED_HELD":
        raise ThreatModelError("local security assessment status drift")
    if value["allEvidenceAnchorsFound"] is not True or value["productionSecurityApproved"] is not False:
        raise ThreatModelError("local security assessment overclaims readiness")
    _authority(value["productionAuthority"], "local security assessment")
    rebuilt = build_local_security_assessment(
        source_commit=str(value["sourceCommit"]),
        source_tree=str(value["sourceTree"]),
        observations=value["evidenceObservations"] if type(value["evidenceObservations"]) is list else [],
    )
    if rebuilt != value:
        raise ThreatModelError("local security assessment does not match canonical reconstruction")
    return dict(value)
