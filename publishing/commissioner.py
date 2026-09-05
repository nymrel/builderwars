"""Deterministic, zero-authority commissioner starter for AgentWars.

The packet assembles reviewed league-operation contracts into one human-facing
handoff. It schedules nothing, admits nobody, executes no provider or creator
code, and grants no production, moderation, publication, or launch authority.
"""

from __future__ import annotations

import copy

from publishing import league_operations as league_ops


SCHEMA_VERSION = "agentwars.commissioner-starter/1"
STATUS = "local_commissioner_starter_not_scheduled"

AUTHORITY = {
    "seasonScheduled": False,
    "entrantsInvited": False,
    "entrantIdentityVerified": False,
    "providerAuthorizationGranted": False,
    "fixturesActivated": False,
    "supportQueueStaffed": False,
    "moderationActionAuthorized": False,
    "correctionCommitAuthorized": False,
    "rankingsPublished": False,
    "creatorGameAdmitted": False,
    "productionConfigured": False,
    "launchApproved": False,
}

LOCAL_ACTIONS = (
    "inspect_exact_rules_and_contract_digests",
    "run_provider_free_scripted_preseason",
    "review_fail_closed_operations_candidates",
    "prepare_but_not_commit_append_only_correction_candidate",
)

FORBIDDEN_ACTIONS = (
    "schedule_or_activate_a_season",
    "invite_or_admit_an_entrant",
    "attest_identity_model_provider_or_consent",
    "accept_or_execute_creator_code",
    "staff_support_or_execute_moderation",
    "commit_a_correction_or_mutate_standings",
    "configure_production_or_customer_credentials",
    "publish_rankings_or_claim_launch",
)

PROTECTED_STAGES = (
    {
        "stageId": 11,
        "name": "protected_runtime_configuration",
        "status": "HELD_PROTECTED",
        "requiredReceipt": "exact_source_bound_runtime_configuration_receipt",
        "operatorAction": "authorize_named_protected_configuration_ceremony",
    },
    {
        "stageId": 12,
        "name": "source_bound_deployment_and_rollback",
        "status": "HELD_PROTECTED",
        "requiredReceipt": "served_byte_deployment_and_rollback_receipt",
        "operatorAction": "authorize_exact_deployment_and_rollback_targets",
    },
    {
        "stageId": 13,
        "name": "consented_tester_review_and_launch_authority",
        "status": "HELD_PROTECTED",
        "requiredReceipt": "consented_tester_review_cleanup_and_launch_decision_receipts",
        "operatorAction": "consent_to_tester_journey_then_record_separate_launch_decision",
    },
)


class CommissionerStarterError(ValueError):
    """Raised when a commissioner packet fails closed."""


def commissioner_starter() -> dict[str, object]:
    contract = league_ops.verify_finite_league_contract(league_ops.finite_league_contract())
    formats = {item["formatId"]: item for item in contract["formats"]}
    redraft = formats["redraft"]
    dynasty = formats["dynasty"]
    packet: dict[str, object] = {
        "schemaVersion": SCHEMA_VERSION,
        "status": STATUS,
        "leagueContractDigest": contract["contractDigest"],
        "activeSeasonCandidate": {
            "leagueId": contract["leagueId"],
            "formatId": redraft["formatId"],
            "gameName": redraft["gameName"],
            "gameVersion": redraft["gameVersion"],
            "rulesDigest": redraft["rulesDigest"],
            "scoringHorizon": redraft["scoringHorizon"],
            "standingsScope": redraft["standingsScope"],
            "seasonStatus": redraft["seasonStatus"],
            "fixturePlan": copy.deepcopy(contract["fixturePlan"]),
        },
        "inactiveCohorts": [
            {
                "formatId": dynasty["formatId"],
                "gameName": dynasty["gameName"],
                "gameVersion": dynasty["gameVersion"],
                "rulesDigest": dynasty["rulesDigest"],
                "scoringHorizon": dynasty["scoringHorizon"],
                "standingsScope": dynasty["standingsScope"],
                "seasonStatus": dynasty["seasonStatus"],
                "rosterCarryoverAuthorized": dynasty["rosterCarryoverAuthorized"],
                "ratingCarryoverAuthorized": dynasty["ratingCarryoverAuthorized"],
            }
        ],
        "operationsBindings": {
            "supportPolicyDigest": league_ops.digest(contract["supportPolicy"]),
            "moderationPolicyDigest": league_ops.digest(contract["moderationPolicy"]),
            "correctionPolicyDigest": league_ops.digest(contract["correctionPolicy"]),
            "rollbackPolicyDigest": league_ops.digest(contract["rollbackPolicy"]),
            "standingsPolicyDigest": league_ops.digest(contract["standingsPolicy"]),
        },
        "creatorBoundary": copy.deepcopy(contract["creatorAdmissionBoundary"]),
        "localActionsAvailable": list(LOCAL_ACTIONS),
        "forbiddenActions": list(FORBIDDEN_ACTIONS),
        "protectedLaunchStages": [copy.deepcopy(item) for item in PROTECTED_STAGES],
        "operatorBlockers": [
            "exact_source_bound_production_configuration_not_verified",
            "source_bound_deployment_and_rollback_not_proven",
            "consented_tester_review_cleanup_and_launch_authority_not_recorded",
            "support_moderation_and_incident_ownership_not_staffed",
        ],
        "documentation": {
            "starterKit": "docs/AGENTWARS_STARTER_KIT.md",
            "leagueOperations": "docs/AGENTWARS_FINITE_FANTASY_LEAGUE_OPERATIONS.md",
            "creatorSdk": "docs/AGENTWARS_CREATOR_GAME_SDK.md",
            "testerCeremony": "docs/AGENTWARS_TESTER_CEREMONY.md",
        },
        "evidenceLimits": [
            "no_real_entrant_model_provider_identity_or_consent",
            "no_scheduled_or_activated_fixture",
            "no_staffed_support_or_executed_moderation",
            "no_committed_correction_standings_or_public_ranking",
            "no_production_configuration_deployment_audience_retention_or_revenue",
            "no_launch_authority",
        ],
        "authority": dict(AUTHORITY),
    }
    packet["packetDigest"] = league_ops.digest(packet)
    return packet


def verify_commissioner_starter(candidate: object) -> dict[str, object]:
    if type(candidate) is not dict:
        raise CommissionerStarterError("commissioner starter must be an exact object")
    expected = commissioner_starter()
    if candidate != expected:
        raise CommissionerStarterError("commissioner starter drift")
    unsigned = dict(candidate)
    supplied = unsigned.pop("packetDigest", None)
    if supplied != league_ops.digest(unsigned):
        raise CommissionerStarterError("commissioner starter digest mismatch")
    return candidate
