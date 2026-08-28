"""Strict, non-executing contracts for the BuildWars build-off format.

The first BuildWars kernel accepts only declarative evidence.  It binds a
versioned challenge to immutable entry artifacts and rubric judgments, then
derives one order-independent candidate receipt.  It never runs submitted
commands, fetches URLs, invokes a provider, publishes a result, or converts an
artifact judgment into an AgentWars rating.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Iterable
from typing import Any


CHALLENGE_SCHEMA = "buildwars.challenge.v1"
ENTRY_SCHEMA = "buildwars.entry.v1"
JUDGMENT_SCHEMA = "buildwars.judgment.v1"
RECEIPT_SCHEMA = "buildwars.buildoff_receipt.v1"
PROJECTION_SCHEMA = "buildwars.candidate_projection.v1"

MATCHUP_CLASSES = frozenset(
    {
        "builder_vs_builder",
        "builder_vs_agent",
        "agent_vs_agent",
        "team_vs_team",
    }
)
PARTICIPANT_KINDS = frozenset({"builder", "agent", "team"})
MAX_DOCUMENT_BYTES = 256 * 1024
MAX_ENTRIES = 64
MAX_CRITERIA = 24
MAX_EVIDENCE_DIGESTS = 32

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERNS = {
    "challenge": re.compile(r"^bwc1_[0-9a-f]{24}$"),
    "entry": re.compile(r"^bwe1_[0-9a-f]{24}$"),
    "judgment": re.compile(r"^bwj1_[0-9a-f]{24}$"),
}
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9][a-z0-9.-]{0,31})?$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,95}$")
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{0,47}$")
_MEDIA_RE = re.compile(r"^[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]{0,62}$")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key|authorization|bearer|cookie)"
    r"\s*[=:]\s*\S"
)
_SECRET_PREFIXES = (
    "sk-or-v1-",
    "sk-or-",
    "sk-ant-",
    "sk-proj-",
    "sk-",
    "Bearer ",
    "bearer ",
    "ghp_",
    "gho_",
    "ghu_",
    "xoxb-",
    "xoxp-",
    "AKIA",
)

_DIGEST_DOCUMENT_KEYS = frozenset({"mediaType", "canonicalization", "sha256"})
_PARTICIPANT_KEYS = frozenset({"kind", "ref", "version"})
_RUBRIC_KEYS = frozenset({"schema", "version", "criteria", "rubricDigest"})
_CRITERION_KEYS = frozenset({"criterionId", "label", "maxPoints"})
_CHALLENGE_KEYS = frozenset(
    {
        "schema",
        "challengeId",
        "version",
        "title",
        "brief",
        "fixture",
        "matchupClasses",
        "entryLimit",
        "rubric",
        "executionPolicy",
        "publicationStatus",
        "challengeDigest",
    }
)
_DECLARATION_KEYS = frozenset(
    {"toolIds", "modelClaims", "providerClaims", "agentRefs", "harnessRefs"}
)
_EVIDENCE_KEYS = frozenset(
    {
        "buildReceiptSha256",
        "testReceiptSha256",
        "artifactManifestSha256",
        "environmentSha256",
        "reproductionStatus",
    }
)
_ENTRY_KEYS = frozenset(
    {
        "schema",
        "entryId",
        "challengeId",
        "challengeVersion",
        "participant",
        "source",
        "artifact",
        "declarations",
        "evidence",
        "submissionStatus",
        "publicationStatus",
        "entryDigest",
    }
)
_SCORE_KEYS = frozenset({"criterionId", "points", "evidenceDigests"})
_JUDGMENT_KEYS = frozenset(
    {
        "schema",
        "judgmentId",
        "challengeDigest",
        "entryDigest",
        "rubricDigest",
        "reviewerRef",
        "reviewerVersion",
        "reviewEvidenceClass",
        "criteria",
        "totalPoints",
        "decisionStatus",
        "judgmentDigest",
    }
)
_SCORE_ROW_KEYS = frozenset(
    {"entryId", "entryDigest", "participant", "judgmentDigest", "totalPoints"}
)
_RECEIPT_KEYS = frozenset(
    {
        "schema",
        "evidenceClass",
        "resultStatus",
        "challengeId",
        "challengeVersion",
        "challengeDigest",
        "rubricDigest",
        "scores",
        "candidateWinnerEntryIds",
        "tie",
        "publicationDecision",
        "rankingEligible",
        "titleEligible",
        "agentWarsRatingEligible",
        "modelAttested",
        "providerAttested",
        "executionAttested",
        "reviewerIdentityAttested",
        "receiptId",
    }
)


class BuildWarsContractError(ValueError):
    """A bounded refusal from the declarative BuildWars contract."""


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise BuildWarsContractError(f"duplicate JSON object key {key!r}")
        value[key] = item
    return value


def _reject_floats(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        raise BuildWarsContractError(f"{path}: floats are not canonically encodable")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise BuildWarsContractError(f"{path}: object keys must be strings")
            _reject_floats(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_floats(item, f"{path}[{index}]")
    elif isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise BuildWarsContractError(
                f"{path}: string contains a surrogate control code point"
            )
    elif value is not None and not isinstance(value, (bool, int, str)):
        raise BuildWarsContractError(
            f"{path}: {type(value).__name__} is not canonically encodable"
        )


def decode_strict(data: str | bytes | bytearray) -> dict[str, Any]:
    """Decode one bounded JSON object, rejecting duplicate keys and floats."""

    if isinstance(data, str):
        raw = data.encode("utf-8")
        text = data
    elif isinstance(data, (bytes, bytearray)):
        raw = bytes(data)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise BuildWarsContractError("payload is not valid UTF-8") from error
    else:
        raise BuildWarsContractError("payload must be bytes or text")
    if not raw or len(raw) > MAX_DOCUMENT_BYTES:
        raise BuildWarsContractError("payload is empty or oversized")
    try:
        value = json.loads(text, object_pairs_hook=_pairs_no_duplicates)
    except json.JSONDecodeError as error:
        raise BuildWarsContractError(
            f"invalid JSON: {error.msg} at char {error.pos}"
        ) from error
    if not isinstance(value, dict):
        raise BuildWarsContractError("top-level payload must be an object")
    _reject_floats(value)
    return value


def canonical_bytes(value: Any) -> bytes:
    _reject_floats(value)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise BuildWarsContractError("value cannot be canonically encoded") from error


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _bounded_document(value: Any, label: str) -> None:
    if len(canonical_bytes(value)) > MAX_DOCUMENT_BYTES:
        raise BuildWarsContractError(f"{label} is oversized")


def _exact_keys(value: Any, expected: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BuildWarsContractError(f"{label} must be an object")
    got = set(value)
    unknown = sorted(got - expected)
    missing = sorted(expected - got)
    if unknown:
        raise BuildWarsContractError(f"{label} has unknown keys {unknown}")
    if missing:
        raise BuildWarsContractError(f"{label} is missing keys {missing}")
    return value


def _text(value: Any, label: str, *, minimum: int = 1, maximum: int = 160) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise BuildWarsContractError(f"{label} must be bounded text")
    if any(
        ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF
        for char in value
    ):
        raise BuildWarsContractError(f"{label} contains control characters")
    if _EMAIL_RE.search(value) or _ASSIGNMENT_RE.search(value):
        raise BuildWarsContractError(f"{label} contains forbidden credential-shaped text")
    if any(value.startswith(prefix) for prefix in _SECRET_PREFIXES):
        raise BuildWarsContractError(f"{label} contains a forbidden credential prefix")
    return value


def _match(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise BuildWarsContractError(f"{label} is malformed")
    return value


def _hex(value: Any, label: str) -> str:
    return _match(value, _HEX64_RE, label)


def _integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise BuildWarsContractError(
            f"{label} must be an integer from {minimum} through {maximum}"
        )
    return value


def _digest_document(value: Any, label: str) -> dict[str, str]:
    row = _exact_keys(value, _DIGEST_DOCUMENT_KEYS, label)
    media_type = _match(row["mediaType"], _MEDIA_RE, f"{label}.mediaType")
    canonicalization = _match(
        row["canonicalization"], _REF_RE, f"{label}.canonicalization"
    )
    sha256 = _hex(row["sha256"], f"{label}.sha256")
    return {
        "mediaType": media_type,
        "canonicalization": canonicalization,
        "sha256": sha256,
    }


def _participant(value: Any, label: str = "participant") -> dict[str, str]:
    row = _exact_keys(value, _PARTICIPANT_KEYS, label)
    kind = row["kind"]
    if kind not in PARTICIPANT_KINDS:
        raise BuildWarsContractError(f"{label}.kind is unsupported")
    return {
        "kind": kind,
        "ref": _match(row["ref"], _REF_RE, f"{label}.ref"),
        "version": _match(row["version"], _VERSION_RE, f"{label}.version"),
    }


def _string_list(
    value: Any,
    label: str,
    *,
    maximum: int = 32,
    pattern: re.Pattern[str] = _REF_RE,
) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise BuildWarsContractError(f"{label} must be a bounded list")
    result = [_match(item, pattern, f"{label}[{index}]") for index, item in enumerate(value)]
    if len(set(result)) != len(result):
        raise BuildWarsContractError(f"{label} contains duplicates")
    if result != sorted(result):
        raise BuildWarsContractError(f"{label} must be sorted")
    return result


def _validate_rubric(value: Any) -> dict[str, Any]:
    row = _exact_keys(value, _RUBRIC_KEYS, "challenge.rubric")
    if row["schema"] != "buildwars.rubric.v1":
        raise BuildWarsContractError("challenge.rubric.schema is unsupported")
    version = _match(row["version"], _VERSION_RE, "challenge.rubric.version")
    raw_criteria = row["criteria"]
    if not isinstance(raw_criteria, list) or not 1 <= len(raw_criteria) <= MAX_CRITERIA:
        raise BuildWarsContractError("challenge.rubric.criteria count is invalid")
    criteria: list[dict[str, Any]] = []
    for index, value in enumerate(raw_criteria):
        criterion = _exact_keys(value, _CRITERION_KEYS, f"challenge.rubric.criteria[{index}]")
        criteria.append(
            {
                "criterionId": _match(
                    criterion["criterionId"], _SLUG_RE, f"criterion[{index}].criterionId"
                ),
                "label": _text(criterion["label"], f"criterion[{index}].label", maximum=80),
                "maxPoints": _integer(
                    criterion["maxPoints"], f"criterion[{index}].maxPoints", 1, 1_000
                ),
            }
        )
    ids = [criterion["criterionId"] for criterion in criteria]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise BuildWarsContractError("challenge.rubric.criteria must be unique and sorted")
    if sum(criterion["maxPoints"] for criterion in criteria) > 10_000:
        raise BuildWarsContractError("challenge.rubric total points are oversized")
    core = {"schema": row["schema"], "version": version, "criteria": criteria}
    if not hmac.compare_digest(
        _hex(row["rubricDigest"], "challenge.rubric.rubricDigest"), digest(core)
    ):
        raise BuildWarsContractError("challenge.rubric.rubricDigest is invalid")
    return {**core, "rubricDigest": row["rubricDigest"]}


def validate_challenge(value: Any) -> dict[str, Any]:
    _bounded_document(value, "challenge")
    row = _exact_keys(value, _CHALLENGE_KEYS, "challenge")
    if row["schema"] != CHALLENGE_SCHEMA:
        raise BuildWarsContractError("challenge.schema is unsupported")
    matchup_classes = _string_list(
        row["matchupClasses"], "challenge.matchupClasses", maximum=len(MATCHUP_CLASSES), pattern=_SLUG_RE
    )
    if not matchup_classes or not set(matchup_classes).issubset(MATCHUP_CLASSES):
        raise BuildWarsContractError("challenge.matchupClasses contains an unsupported class")
    normalized = {
        "schema": CHALLENGE_SCHEMA,
        "challengeId": _match(row["challengeId"], _ID_PATTERNS["challenge"], "challenge.challengeId"),
        "version": _match(row["version"], _VERSION_RE, "challenge.version"),
        "title": _text(row["title"], "challenge.title"),
        "brief": _digest_document(row["brief"], "challenge.brief"),
        "fixture": _digest_document(row["fixture"], "challenge.fixture"),
        "matchupClasses": matchup_classes,
        "entryLimit": _integer(row["entryLimit"], "challenge.entryLimit", 2, MAX_ENTRIES),
        "rubric": _validate_rubric(row["rubric"]),
        "executionPolicy": row["executionPolicy"],
        "publicationStatus": row["publicationStatus"],
    }
    if normalized["executionPolicy"] != "declarative_evidence_only":
        raise BuildWarsContractError("challenge.executionPolicy must remain non-executing")
    if normalized["publicationStatus"] != "reviewed_candidate_not_public":
        raise BuildWarsContractError("challenge.publicationStatus overstates launch authority")
    challenge_digest = _hex(row["challengeDigest"], "challenge.challengeDigest")
    if not hmac.compare_digest(challenge_digest, digest(normalized)):
        raise BuildWarsContractError("challenge.challengeDigest is invalid")
    return {**normalized, "challengeDigest": challenge_digest}


def validate_entry(value: Any, *, challenge: dict[str, Any] | None = None) -> dict[str, Any]:
    _bounded_document(value, "entry")
    row = _exact_keys(value, _ENTRY_KEYS, "entry")
    if row["schema"] != ENTRY_SCHEMA:
        raise BuildWarsContractError("entry.schema is unsupported")
    declarations = _exact_keys(row["declarations"], _DECLARATION_KEYS, "entry.declarations")
    normalized_declarations = {
        key: _string_list(declarations[key], f"entry.declarations.{key}")
        for key in sorted(_DECLARATION_KEYS)
    }
    evidence = _exact_keys(row["evidence"], _EVIDENCE_KEYS, "entry.evidence")
    normalized_evidence = {
        key: _hex(evidence[key], f"entry.evidence.{key}")
        for key in (
            "artifactManifestSha256",
            "buildReceiptSha256",
            "environmentSha256",
            "testReceiptSha256",
        )
    }
    normalized_evidence["reproductionStatus"] = evidence["reproductionStatus"]
    if normalized_evidence["reproductionStatus"] != "customer_supplied_unverified":
        raise BuildWarsContractError("entry.evidence.reproductionStatus overstates verification")
    normalized = {
        "schema": ENTRY_SCHEMA,
        "entryId": _match(row["entryId"], _ID_PATTERNS["entry"], "entry.entryId"),
        "challengeId": _match(
            row["challengeId"], _ID_PATTERNS["challenge"], "entry.challengeId"
        ),
        "challengeVersion": _match(row["challengeVersion"], _VERSION_RE, "entry.challengeVersion"),
        "participant": _participant(row["participant"], "entry.participant"),
        "source": _digest_document(row["source"], "entry.source"),
        "artifact": _digest_document(row["artifact"], "entry.artifact"),
        "declarations": normalized_declarations,
        "evidence": normalized_evidence,
        "submissionStatus": row["submissionStatus"],
        "publicationStatus": row["publicationStatus"],
    }
    if normalized["submissionStatus"] != "submitted_unreviewed":
        raise BuildWarsContractError("entry.submissionStatus overstates admission")
    if normalized["publicationStatus"] != "not_reviewed_not_public":
        raise BuildWarsContractError("entry.publicationStatus overstates publication")
    if challenge is not None:
        challenge = validate_challenge(challenge)
        if (
            normalized["challengeId"] != challenge["challengeId"]
            or normalized["challengeVersion"] != challenge["version"]
        ):
            raise BuildWarsContractError("entry differs from the bound challenge")
    entry_digest = _hex(row["entryDigest"], "entry.entryDigest")
    if not hmac.compare_digest(entry_digest, digest(normalized)):
        raise BuildWarsContractError("entry.entryDigest is invalid")
    return {**normalized, "entryDigest": entry_digest}


def validate_judgment(
    value: Any,
    *,
    challenge: dict[str, Any],
    entry: dict[str, Any],
) -> dict[str, Any]:
    _bounded_document(value, "judgment")
    challenge = validate_challenge(challenge)
    entry = validate_entry(entry, challenge=challenge)
    row = _exact_keys(value, _JUDGMENT_KEYS, "judgment")
    if row["schema"] != JUDGMENT_SCHEMA:
        raise BuildWarsContractError("judgment.schema is unsupported")
    criteria_by_id = {
        criterion["criterionId"]: criterion for criterion in challenge["rubric"]["criteria"]
    }
    entry_evidence_digests = {
        entry["source"]["sha256"],
        entry["artifact"]["sha256"],
        *(
            entry["evidence"][key]
            for key in (
                "artifactManifestSha256",
                "buildReceiptSha256",
                "environmentSha256",
                "testReceiptSha256",
            )
        ),
    }
    raw_scores = row["criteria"]
    if not isinstance(raw_scores, list) or len(raw_scores) != len(criteria_by_id):
        raise BuildWarsContractError("judgment.criteria must score every rubric criterion")
    scores: list[dict[str, Any]] = []
    for index, value in enumerate(raw_scores):
        score = _exact_keys(value, _SCORE_KEYS, f"judgment.criteria[{index}]")
        criterion_id = _match(
            score["criterionId"], _SLUG_RE, f"judgment.criteria[{index}].criterionId"
        )
        if criterion_id not in criteria_by_id:
            raise BuildWarsContractError("judgment.criteria references an unknown criterion")
        evidence_digests = _string_list(
            score["evidenceDigests"],
            f"judgment.criteria[{index}].evidenceDigests",
            maximum=MAX_EVIDENCE_DIGESTS,
            pattern=_HEX64_RE,
        )
        if not evidence_digests:
            raise BuildWarsContractError("every judgment criterion needs digest-bound evidence")
        if not set(evidence_digests).issubset(entry_evidence_digests):
            raise BuildWarsContractError(
                "judgment criterion cites evidence outside the bound entry"
            )
        scores.append(
            {
                "criterionId": criterion_id,
                "points": _integer(
                    score["points"],
                    f"judgment.criteria[{index}].points",
                    0,
                    criteria_by_id[criterion_id]["maxPoints"],
                ),
                "evidenceDigests": evidence_digests,
            }
        )
    score_ids = [score["criterionId"] for score in scores]
    if score_ids != sorted(criteria_by_id) or len(score_ids) != len(set(score_ids)):
        raise BuildWarsContractError("judgment.criteria must be unique and rubric-sorted")
    total = sum(score["points"] for score in scores)
    normalized = {
        "schema": JUDGMENT_SCHEMA,
        "judgmentId": _match(
            row["judgmentId"], _ID_PATTERNS["judgment"], "judgment.judgmentId"
        ),
        "challengeDigest": _hex(row["challengeDigest"], "judgment.challengeDigest"),
        "entryDigest": _hex(row["entryDigest"], "judgment.entryDigest"),
        "rubricDigest": _hex(row["rubricDigest"], "judgment.rubricDigest"),
        "reviewerRef": _match(row["reviewerRef"], _REF_RE, "judgment.reviewerRef"),
        "reviewerVersion": _match(
            row["reviewerVersion"], _VERSION_RE, "judgment.reviewerVersion"
        ),
        "reviewEvidenceClass": row["reviewEvidenceClass"],
        "criteria": scores,
        "totalPoints": _integer(row["totalPoints"], "judgment.totalPoints", 0, 10_000),
        "decisionStatus": row["decisionStatus"],
    }
    if normalized["challengeDigest"] != challenge["challengeDigest"]:
        raise BuildWarsContractError("judgment differs from the bound challenge")
    if normalized["entryDigest"] != entry["entryDigest"]:
        raise BuildWarsContractError("judgment differs from the bound entry")
    if normalized["rubricDigest"] != challenge["rubric"]["rubricDigest"]:
        raise BuildWarsContractError("judgment differs from the bound rubric")
    if normalized["totalPoints"] != total:
        raise BuildWarsContractError("judgment.totalPoints is not derived from criteria")
    if normalized["reviewEvidenceClass"] != "unattested_offline_review":
        raise BuildWarsContractError("judgment.reviewEvidenceClass overstates reviewer proof")
    if normalized["decisionStatus"] != "scored_candidate_not_public":
        raise BuildWarsContractError("judgment.decisionStatus overstates authority")
    judgment_digest = _hex(row["judgmentDigest"], "judgment.judgmentDigest")
    if not hmac.compare_digest(judgment_digest, digest(normalized)):
        raise BuildWarsContractError("judgment.judgmentDigest is invalid")
    return {**normalized, "judgmentDigest": judgment_digest}


def seal_buildoff(
    challenge: dict[str, Any],
    entries: Iterable[dict[str, Any]],
    judgments: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Derive one non-public, non-ranking receipt from exact validated inputs."""

    challenge = validate_challenge(challenge)
    normalized_entries = [validate_entry(entry, challenge=challenge) for entry in entries]
    if not 2 <= len(normalized_entries) <= challenge["entryLimit"]:
        raise BuildWarsContractError("build-off entry count is outside the challenge limit")
    entry_ids = [entry["entryId"] for entry in normalized_entries]
    entry_digests = [entry["entryDigest"] for entry in normalized_entries]
    participant_bindings = [canonical_bytes(entry["participant"]) for entry in normalized_entries]
    if len(entry_ids) != len(set(entry_ids)) or len(entry_digests) != len(set(entry_digests)):
        raise BuildWarsContractError("build-off entries must be distinct")
    if len(participant_bindings) != len(set(participant_bindings)):
        raise BuildWarsContractError("one participant version cannot occupy two entries")
    participant_kinds = frozenset(
        entry["participant"]["kind"] for entry in normalized_entries
    )
    matchup_class = {
        frozenset({"builder"}): "builder_vs_builder",
        frozenset({"agent"}): "agent_vs_agent",
        frozenset({"team"}): "team_vs_team",
        frozenset({"builder", "agent"}): "builder_vs_agent",
    }.get(participant_kinds)
    if matchup_class is None or matchup_class not in challenge["matchupClasses"]:
        raise BuildWarsContractError(
            "build-off participant kinds are not admitted by the challenge matchup classes"
        )

    by_digest = {entry["entryDigest"]: entry for entry in normalized_entries}
    normalized_judgments: list[dict[str, Any]] = []
    for judgment in judgments:
        if not isinstance(judgment, dict) or judgment.get("entryDigest") not in by_digest:
            raise BuildWarsContractError("judgment references an unknown entry")
        normalized_judgments.append(
            validate_judgment(
                judgment,
                challenge=challenge,
                entry=by_digest[judgment["entryDigest"]],
            )
        )
    if len(normalized_judgments) != len(normalized_entries):
        raise BuildWarsContractError("build-off needs exactly one judgment per entry")
    judgment_entry_digests = [judgment["entryDigest"] for judgment in normalized_judgments]
    judgment_ids = [judgment["judgmentId"] for judgment in normalized_judgments]
    if (
        set(judgment_entry_digests) != set(entry_digests)
        or len(judgment_entry_digests) != len(set(judgment_entry_digests))
        or len(judgment_ids) != len(set(judgment_ids))
    ):
        raise BuildWarsContractError("build-off judgments must be distinct and complete")

    judgment_by_entry = {
        judgment["entryDigest"]: judgment for judgment in normalized_judgments
    }
    scores = []
    for entry in sorted(normalized_entries, key=lambda item: item["entryId"]):
        judgment = judgment_by_entry[entry["entryDigest"]]
        scores.append(
            {
                "entryId": entry["entryId"],
                "entryDigest": entry["entryDigest"],
                "participant": entry["participant"],
                "judgmentDigest": judgment["judgmentDigest"],
                "totalPoints": judgment["totalPoints"],
            }
        )
    top_score = max(score["totalPoints"] for score in scores)
    winners = sorted(
        score["entryId"] for score in scores if score["totalPoints"] == top_score
    )
    core = {
        "schema": RECEIPT_SCHEMA,
        "evidenceClass": "artifact_review",
        "resultStatus": "offline_scored_candidate",
        "challengeId": challenge["challengeId"],
        "challengeVersion": challenge["version"],
        "challengeDigest": challenge["challengeDigest"],
        "rubricDigest": challenge["rubric"]["rubricDigest"],
        "scores": scores,
        "candidateWinnerEntryIds": winners,
        "tie": len(winners) > 1,
        "publicationDecision": "not_reviewed_not_published",
        "rankingEligible": False,
        "titleEligible": False,
        "agentWarsRatingEligible": False,
        "modelAttested": False,
        "providerAttested": False,
        "executionAttested": False,
        "reviewerIdentityAttested": False,
    }
    return {**core, "receiptId": digest(core)}


def verify_receipt(
    receipt: Any,
    *,
    challenge: dict[str, Any],
    entries: Iterable[dict[str, Any]],
    judgments: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Recompute a receipt instead of trusting its editable score summary."""

    receipt = validate_receipt(receipt)
    expected = seal_buildoff(challenge, entries, judgments)
    if not hmac.compare_digest(canonical_bytes(receipt), canonical_bytes(expected)):
        raise BuildWarsContractError("receipt differs from its exact derived inputs")
    return expected


def validate_receipt(receipt: Any) -> dict[str, Any]:
    """Validate consistency, not signer provenance, for one candidate receipt."""

    _bounded_document(receipt, "receipt")
    row = _exact_keys(receipt, _RECEIPT_KEYS, "receipt")
    fixed = {
        "schema": RECEIPT_SCHEMA,
        "evidenceClass": "artifact_review",
        "resultStatus": "offline_scored_candidate",
        "publicationDecision": "not_reviewed_not_published",
        "rankingEligible": False,
        "titleEligible": False,
        "agentWarsRatingEligible": False,
        "modelAttested": False,
        "providerAttested": False,
        "executionAttested": False,
        "reviewerIdentityAttested": False,
    }
    for key, expected in fixed.items():
        observed = row.get(key)
        if isinstance(expected, bool):
            valid = isinstance(observed, bool) and observed is expected
        else:
            valid = observed == expected
        if not valid:
            raise BuildWarsContractError(
                "receipt overstates evidence or publication authority"
            )
    _match(row["challengeId"], _ID_PATTERNS["challenge"], "receipt.challengeId")
    _match(row["challengeVersion"], _VERSION_RE, "receipt.challengeVersion")
    _hex(row["challengeDigest"], "receipt.challengeDigest")
    _hex(row["rubricDigest"], "receipt.rubricDigest")
    raw_scores = row["scores"]
    if not isinstance(raw_scores, list) or not 2 <= len(raw_scores) <= MAX_ENTRIES:
        raise BuildWarsContractError("receipt.scores must be a bounded build-off table")
    scores: list[dict[str, Any]] = []
    for index, value in enumerate(raw_scores):
        score = _exact_keys(value, _SCORE_ROW_KEYS, f"receipt.scores[{index}]")
        scores.append(
            {
                "entryId": _match(
                    score["entryId"], _ID_PATTERNS["entry"], f"receipt.scores[{index}].entryId"
                ),
                "entryDigest": _hex(
                    score["entryDigest"], f"receipt.scores[{index}].entryDigest"
                ),
                "participant": _participant(
                    score["participant"], f"receipt.scores[{index}].participant"
                ),
                "judgmentDigest": _hex(
                    score["judgmentDigest"], f"receipt.scores[{index}].judgmentDigest"
                ),
                "totalPoints": _integer(
                    score["totalPoints"], f"receipt.scores[{index}].totalPoints", 0, 10_000
                ),
            }
        )
    entry_ids = [score["entryId"] for score in scores]
    entry_digests = [score["entryDigest"] for score in scores]
    judgment_digests = [score["judgmentDigest"] for score in scores]
    participants = [canonical_bytes(score["participant"]) for score in scores]
    if entry_ids != sorted(entry_ids):
        raise BuildWarsContractError("receipt.scores must be sorted by entry id")
    for values, label in (
        (entry_ids, "entry ids"),
        (entry_digests, "entry digests"),
        (judgment_digests, "judgment digests"),
        (participants, "participant versions"),
    ):
        if len(values) != len(set(values)):
            raise BuildWarsContractError(f"receipt.scores has duplicate {label}")
    winner_ids = _string_list(
        row["candidateWinnerEntryIds"],
        "receipt.candidateWinnerEntryIds",
        maximum=len(scores),
        pattern=_ID_PATTERNS["entry"],
    )
    if not winner_ids:
        raise BuildWarsContractError("receipt.candidateWinnerEntryIds cannot be empty")
    top_score = max(score["totalPoints"] for score in scores)
    expected_winners = sorted(
        score["entryId"] for score in scores if score["totalPoints"] == top_score
    )
    if winner_ids != expected_winners:
        raise BuildWarsContractError("receipt candidate leaders do not follow from scores")
    if not isinstance(row["tie"], bool) or row["tie"] is not (len(winner_ids) > 1):
        raise BuildWarsContractError("receipt tie status does not follow from scores")
    receipt_id = _hex(row["receiptId"], "receipt.receiptId")
    core = {key: row[key] for key in _RECEIPT_KEYS if key != "receiptId"}
    if not hmac.compare_digest(receipt_id, digest(core)):
        raise BuildWarsContractError("receipt.receiptId is invalid")
    return row


def candidate_projection(receipt: Any) -> dict[str, Any]:
    """Return the only safe projection before independent review and publication.

    It intentionally contains no source paths, artifact locations, provider or
    model claims, judging evidence, share call-to-action, or public winner claim.
    """

    row = validate_receipt(receipt)
    return {
        "schema": PROJECTION_SCHEMA,
        "projectionStatus": "private_candidate_not_public",
        "evidenceClass": "artifact_review",
        "challengeId": row["challengeId"],
        "challengeVersion": row["challengeVersion"],
        "receiptId": row["receiptId"],
        "entryCount": len(row["scores"]),
        "candidateWinnerEntryIds": list(row["candidateWinnerEntryIds"]),
        "tie": row["tie"],
        "shareEligible": False,
        "rankingEligible": False,
        "agentWarsRatingEligible": False,
        "truth": "Offline artifact-review candidate; not independently attested or published.",
    }
