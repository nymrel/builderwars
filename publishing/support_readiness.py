"""Pure, redacted, zero-authority support-readiness contracts for AgentWars.

This module can build an unsubmitted local support-case candidate from an
allowlisted issue class and opaque references. It configures no inbox, stores
nothing, promises no response time, and performs no human or production action.
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone

from publishing import league_operations
from publishing import observability


CONTRACT_SCHEMA = "agentwars.support-readiness-contract/1"
CASE_SCHEMA = "agentwars.support-case-candidate/1"
STATUS = "local_unstaffed_support_runbook_only"
CASE_STATUS = "local_unsubmitted_candidate"

UTC_SECOND_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
CASE_ID_RE = re.compile(r"^awsupp_[0-9a-f]{32}$")
RESOURCE_REF_RE = re.compile(r"^awref_[0-9a-f]{32}$")
SOURCE_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

AUTHORITY = {
    "transportConfigured": False,
    "caseSubmitted": False,
    "identityAttested": False,
    "supportQueueStaffed": False,
    "responseTimePromised": False,
    "humanReviewPerformed": False,
    "moderationActionExecuted": False,
    "productionFlagsChanged": False,
    "publicCommunicationPublished": False,
    "launchable": False,
}

PROHIBITED_FIELDS = (
    "account",
    "authorization",
    "cookie",
    "credential",
    "email",
    "freeText",
    "ip",
    "name",
    "output",
    "password",
    "phone",
    "prompt",
    "providerToken",
    "rawModelOutput",
    "secret",
    "session",
    "signature",
    "token",
    "url",
    "user",
)

ACTIVATION_BLOCKERS = (
    "public_support_channel_and_terms_not_approved",
    "staffed_case_owner_and_on_call_escalation_not_confirmed",
    "privacy_legal_and_data_handling_review_not_recorded",
    "production_ticket_store_access_controls_and_retention_not_verified",
    "alert_delivery_status_page_and_incident_communications_not_tested",
    "response_windows_not_measured_or_approved",
)


class SupportReadinessError(ValueError):
    """Raised when a support contract or case candidate fails closed."""


def _timestamp(value: object, label: str) -> None:
    if type(value) is not str or UTC_SECOND_RE.fullmatch(value) is None:
        raise SupportReadinessError(f"{label} must be a UTC whole-second timestamp")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise SupportReadinessError(f"{label} must be a valid UTC timestamp") from error


def _routes() -> tuple[dict[str, object], ...]:
    routes: list[dict[str, object]] = []
    seen: set[str] = set()
    for support_class in league_operations.SUPPORT_CLASSES:
        for issue_class in support_class["issueClasses"]:
            if issue_class in seen:
                raise SupportReadinessError("support issue classes must be unique")
            seen.add(issue_class)
            routes.append(
                {
                    "issueClass": issue_class,
                    "severity": support_class["severity"],
                    "releasePosture": support_class["releasePosture"],
                    "requiredEvidence": copy.deepcopy(support_class["requiredEvidence"]),
                    "responseTimePromise": support_class["responseTimePromise"],
                }
            )
    return tuple(sorted(routes, key=lambda route: route["issueClass"]))


ROUTES = _routes()
ROUTE_BY_ISSUE = {route["issueClass"]: route for route in ROUTES}


def support_readiness_contract() -> dict[str, object]:
    league_contract = league_operations.finite_league_contract()
    observability_contract = observability.observability_contract()
    contract: dict[str, object] = {
        "schemaVersion": CONTRACT_SCHEMA,
        "status": STATUS,
        "sourceBindings": {
            "leagueContractDigest": league_contract["contractDigest"],
            "supportPolicyDigest": league_operations.digest(league_contract["supportPolicy"]),
            "observabilityContractDigest": observability_contract["contractDigest"],
        },
        "intakePolicy": {
            "allowedFields": ["schemaVersion", "caseId", "openedAt", "sourceCommit", "issueClass", "resourceRefs"],
            "resourceReferencePolicy": "opaque_awref_ids_only",
            "maxResourceRefs": 8,
            "freeTextAccepted": False,
            "attachmentsAccepted": False,
            "transportConfigured": False,
            "identityAttestationAccepted": False,
            "responseTimePromise": None,
        },
        "routes": [copy.deepcopy(route) for route in ROUTES],
        "prohibitedFields": list(PROHIBITED_FIELDS),
        "activationBlockers": list(ACTIVATION_BLOCKERS),
        "incidentBridge": {
            "sev1EventName": "support_case_opened",
            "sev1IncidentCode": "SUPPORT_SEV1",
            "bridgeStatus": "schema_only_not_instrumented",
            "eventEmitted": False,
            "incidentCreated": False,
        },
        "authority": dict(AUTHORITY),
    }
    contract["contractDigest"] = league_operations.digest(contract)
    return contract


def verify_support_readiness_contract(candidate: object) -> dict[str, object]:
    if type(candidate) is not dict:
        raise SupportReadinessError("support-readiness contract must be an exact object")
    expected = support_readiness_contract()
    if candidate != expected:
        raise SupportReadinessError("support-readiness contract drift")
    unsigned = dict(candidate)
    supplied = unsigned.pop("contractDigest", None)
    if supplied != league_operations.digest(unsigned):
        raise SupportReadinessError("support-readiness contract digest mismatch")
    return candidate


def build_case_candidate(
    *,
    case_id: str,
    opened_at: str,
    source_commit: str,
    issue_class: str,
    resource_refs: list[str],
) -> dict[str, object]:
    if type(case_id) is not str or CASE_ID_RE.fullmatch(case_id) is None:
        raise SupportReadinessError("caseId is malformed")
    _timestamp(opened_at, "openedAt")
    if type(source_commit) is not str or SOURCE_COMMIT_RE.fullmatch(source_commit) is None:
        raise SupportReadinessError("sourceCommit is malformed")
    if type(issue_class) is not str or issue_class not in ROUTE_BY_ISSUE:
        raise SupportReadinessError("issueClass is unsupported")
    if type(resource_refs) is not list or len(resource_refs) > 8:
        raise SupportReadinessError("resourceRefs must be a bounded list")
    if any(type(ref) is not str or RESOURCE_REF_RE.fullmatch(ref) is None for ref in resource_refs):
        raise SupportReadinessError("resourceRefs contain a malformed opaque reference")
    if len(set(resource_refs)) != len(resource_refs):
        raise SupportReadinessError("resourceRefs must be unique")
    route = copy.deepcopy(ROUTE_BY_ISSUE[issue_class])
    candidate: dict[str, object] = {
        "schemaVersion": CASE_SCHEMA,
        "status": CASE_STATUS,
        "caseId": case_id,
        "openedAt": opened_at,
        "sourceCommit": source_commit,
        "issueClass": issue_class,
        "resourceRefs": sorted(resource_refs),
        "route": route,
        "supportContractDigest": support_readiness_contract()["contractDigest"],
        "submissionTransport": "not_configured",
        "humanReview": "not_performed",
        "responseTimePromise": None,
        "actionsExecuted": False,
        "authority": dict(AUTHORITY),
    }
    candidate["caseDigest"] = league_operations.digest(candidate)
    return candidate


def verify_case_candidate(candidate: object) -> dict[str, object]:
    if type(candidate) is not dict:
        raise SupportReadinessError("support case must be an exact object")
    required = {
        "schemaVersion", "status", "caseId", "openedAt", "sourceCommit", "issueClass",
        "resourceRefs", "route", "supportContractDigest", "submissionTransport",
        "humanReview", "responseTimePromise", "actionsExecuted", "authority", "caseDigest",
    }
    if set(candidate) != required:
        raise SupportReadinessError("support case fields drift")
    rebuilt = build_case_candidate(
        case_id=candidate["caseId"],
        opened_at=candidate["openedAt"],
        source_commit=candidate["sourceCommit"],
        issue_class=candidate["issueClass"],
        resource_refs=candidate["resourceRefs"],
    )
    if candidate != rebuilt:
        raise SupportReadinessError("support case drift")
    return candidate
