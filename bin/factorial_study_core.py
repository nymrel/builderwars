"""Core plan, fixture, and statistical contracts for the AgentWars factorial study."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import re
import tempfile
from typing import Any, Iterable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_SCHEMA = "agentwars.factorial-study-plan/v1"
LOCK_SCHEMA = "agentwars.factorial-study-lock/v1"
RESULT_SCHEMA = "agentwars.factorial-study-result/v1"
CANDIDATE_SCHEMA = "agentwars.factorial-study-publication-candidate/v1"
MODEL_BACKEND_KINDS = frozenset({"api", "cli", "opencode"})
SOURCE_RE = re.compile(r"(?:^|;)source=([^;\s]+)")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class StudyError(RuntimeError):
    """A fail-closed study contract violation."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def value_digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_write_json(path: str, value: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(value, fh, sort_keys=True, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            if text and not text.endswith("\n"):
                fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StudyError(message)


def _validate_id(value: Any, field: str) -> str:
    require(isinstance(value, str) and ID_RE.fullmatch(value) is not None, f"{field} must match {ID_RE.pattern}")
    return value


def _backend_kind(spec: str) -> str:
    return spec.partition(":")[0]


def validate_plan(plan: Any, *, root: str = ROOT, check_paths: bool = True) -> dict[str, Any]:
    require(isinstance(plan, dict), "study plan must be a JSON object")
    require(plan.get("schema") == PLAN_SCHEMA, f"study plan schema must be {PLAN_SCHEMA}")
    _validate_id(plan.get("study_id"), "study_id")
    require(isinstance(plan.get("game"), str) and plan["game"], "game must be a non-empty string")
    require(plan.get("pairings") == "complete", "v1 requires pairings=complete")

    harnesses = plan.get("harnesses")
    require(isinstance(harnesses, list) and len(harnesses) == 2, "v1 requires exactly two harnesses")
    harness_ids: set[str] = set()
    roles: set[str] = set()
    for index, harness in enumerate(harnesses):
        require(isinstance(harness, dict), f"harnesses[{index}] must be an object")
        harness_id = _validate_id(harness.get("id"), f"harnesses[{index}].id")
        require(harness_id not in harness_ids, f"duplicate harness id {harness_id}")
        harness_ids.add(harness_id)
        role = harness.get("role")
        require(role in ("structured", "naive"), "harness role must be structured or naive")
        require(role not in roles, f"duplicate harness role {role}")
        roles.add(role)
        path = harness.get("path")
        require(isinstance(path, str) and path and not os.path.isabs(path), "harness path must be relative")
        normalized = os.path.normpath(path)
        require(not normalized.startswith(".."), "harness path must remain inside the repository")
        if check_paths:
            require(os.path.isfile(os.path.join(root, normalized)), f"harness file does not exist: {path}")
    require(roles == {"structured", "naive"}, "the two harness roles must be structured and naive")

    comparisons = plan.get("comparisons")
    require(isinstance(comparisons, list) and comparisons, "comparisons must be a non-empty array")
    comparison_ids: set[str] = set()
    kinds: set[str] = set()
    for index, comparison in enumerate(comparisons):
        require(isinstance(comparison, dict), f"comparisons[{index}] must be an object")
        comparison_id = _validate_id(comparison.get("id"), f"comparisons[{index}].id")
        require(comparison_id not in comparison_ids, f"duplicate comparison id {comparison_id}")
        comparison_ids.add(comparison_id)
        kind = comparison.get("kind")
        require(kind in ("cross-family", "same-family"), "comparison kind must be cross-family or same-family")
        kinds.add(kind)
        models = comparison.get("models")
        require(isinstance(models, dict) and set(models) == {"small", "large"}, "models must contain exactly small and large")
        families: list[str] = []
        sizes: list[float] = []
        for model_id in ("small", "large"):
            model = models[model_id]
            require(isinstance(model, dict), f"{comparison_id}.{model_id} must be an object")
            require(isinstance(model.get("label"), str) and model["label"], f"{comparison_id}.{model_id}.label required")
            family = model.get("family")
            require(isinstance(family, str) and family, f"{comparison_id}.{model_id}.family required")
            families.append(family.casefold())
            size_b = model.get("parameters_billions")
            require(isinstance(size_b, (int, float)) and not isinstance(size_b, bool) and size_b > 0,
                    f"{comparison_id}.{model_id}.parameters_billions must be positive")
            sizes.append(float(size_b))
            backend = model.get("backend")
            require(isinstance(backend, str) and ":" in backend, f"{comparison_id}.{model_id}.backend required")
            require(_backend_kind(backend) in MODEL_BACKEND_KINDS,
                    f"{comparison_id}.{model_id} must use a model backend, not {_backend_kind(backend)!r}")
        require(sizes[0] < sizes[1], f"{comparison_id}: small must have fewer parameters than large")
        if kind == "same-family":
            require(families[0] == families[1], f"{comparison_id}: same-family models must share family")
        else:
            require(families[0] != families[1], f"{comparison_id}: cross-family models must differ")

    require({"cross-family", "same-family"}.issubset(kinds),
            "the registered v1 plan must include both cross-family and same-family comparisons")

    profiles = plan.get("profiles")
    require(isinstance(profiles, dict) and profiles, "profiles must be a non-empty object")
    for name, profile in profiles.items():
        _validate_id(name, f"profile id {name!r}")
        require(isinstance(profile, dict), f"profile {name} must be an object")
        for field in ("start_seed", "seed_count", "replicates"):
            value = profile.get(field)
            require(isinstance(value, int) and not isinstance(value, bool), f"profile {name}.{field} must be an integer")
        require(profile["start_seed"] >= 0, f"profile {name}.start_seed must be non-negative")
        require(profile["seed_count"] > 0, f"profile {name}.seed_count must be positive")
        require(profile["replicates"] > 0, f"profile {name}.replicates must be positive")
        require(isinstance(profile.get("publishable"), bool), f"profile {name}.publishable must be boolean")

    runtime = plan.get("runtime")
    require(isinstance(runtime, dict), "runtime must be an object")
    for field in ("backend_timeout_s", "move_timeout_s"):
        value = runtime.get(field)
        require(isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0,
                f"runtime.{field} must be positive")
    require(runtime["move_timeout_s"] > runtime["backend_timeout_s"],
            "move_timeout_s must exceed backend_timeout_s")

    gate = plan.get("publication_gate")
    require(isinstance(gate, dict), "publication_gate must be an object")
    for field in ("require_replay_pass", "require_zero_fallback", "require_source_metadata",
                  "require_every_treatment_model_move"):
        require(gate.get(field) is True, f"publication_gate.{field} must be true")
    allowed = gate.get("allowed_result_reasons")
    require(isinstance(allowed, list) and allowed and all(isinstance(item, str) and item for item in allowed),
            "publication_gate.allowed_result_reasons must be non-empty strings")
    require(len(allowed) == len(set(allowed)), "allowed_result_reasons must be unique")
    confidence = gate.get("confidence_level", 0.95)
    require(isinstance(confidence, (int, float)) and 0 < confidence < 1,
            "publication_gate.confidence_level must be between 0 and 1")
    return plan


def plan_digest(plan: dict[str, Any]) -> str:
    return value_digest(plan)


def harness_by_role(plan: dict[str, Any], role: str) -> dict[str, Any]:
    return next(harness for harness in plan["harnesses"] if harness["role"] == role)


def treatment_id(comparison_id: str, model_id: str, harness_id: str) -> str:
    return f"{comparison_id}--{model_id}--{harness_id}"


def treatments_for(plan: dict[str, Any], comparison: dict[str, Any]) -> list[dict[str, Any]]:
    treatments: list[dict[str, Any]] = []
    for model_id in ("small", "large"):
        model = comparison["models"][model_id]
        for harness in plan["harnesses"]:
            tid = treatment_id(comparison["id"], model_id, harness["id"])
            treatments.append(
                {
                    "id": tid,
                    "name": tid,
                    "comparison_id": comparison["id"],
                    "model_id": model_id,
                    "model_label": model["label"],
                    "model_family": model["family"],
                    "parameters_billions": model["parameters_billions"],
                    "backend": model["backend"],
                    "harness_id": harness["id"],
                    "harness_role": harness["role"],
                    "harness_path": harness["path"],
                }
            )
    return treatments


def pairing_id(a: dict[str, Any], b: dict[str, Any]) -> str:
    return value_digest(sorted((a["id"], b["id"])))[:16]


def enumerate_fixtures(
    plan: dict[str, Any],
    profile_name: str,
    comparison_ids: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    require(profile_name in plan["profiles"], f"unknown profile {profile_name!r}")
    profile = plan["profiles"][profile_name]
    selected = set(comparison_ids or [comparison["id"] for comparison in plan["comparisons"]])
    known = {comparison["id"] for comparison in plan["comparisons"]}
    require(selected.issubset(known), f"unknown comparison ids: {sorted(selected - known)}")
    fixtures: list[dict[str, Any]] = []
    for comparison in plan["comparisons"]:
        if comparison["id"] not in selected:
            continue
        treatments = treatments_for(plan, comparison)
        for a, b in itertools.combinations(treatments, 2):
            pid = pairing_id(a, b)
            for replicate in range(profile["replicates"]):
                for seed in range(profile["start_seed"], profile["start_seed"] + profile["seed_count"]):
                    for order in (0, 1):
                        seats = [a, b] if order == 0 else [b, a]
                        descriptor = {
                            "study_id": plan["study_id"],
                            "profile": profile_name,
                            "comparison_id": comparison["id"],
                            "pairing_id": pid,
                            "treatments": sorted((a["id"], b["id"])),
                            "replicate": replicate,
                            "seed": seed,
                            "order": order,
                        }
                        fixture_id = value_digest(descriptor)[:20]
                        fixtures.append(
                            {
                                **descriptor,
                                "fixture_id": fixture_id,
                                "match_id": f"fx-{fixture_id}",
                                "seat0": seats[0],
                                "seat1": seats[1],
                            }
                        )
    return fixtures


def source_from_note(note: Any) -> str | None:
    if not isinstance(note, str):
        return None
    match = SOURCE_RE.search(note)
    return match.group(1) if match else None


def source_class(source: str | None) -> str:
    if source == "model":
        return "model"
    if source is None:
        return "missing"
    if source.startswith("fallback"):
        return "fallback"
    if source.startswith("backend_error"):
        return "backend_error"
    return "other"


def wilson_interval(wins: int, total: int, confidence_level: float = 0.95) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    # v1 supports the preregistered 95% interval without adding scipy.
    if not math.isclose(confidence_level, 0.95, rel_tol=0.0, abs_tol=1e-12):
        raise StudyError("v1 supports confidence_level=0.95 only")
    z = 1.959963984540054
    p = wins / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return (max(0.0, center - radius), min(1.0, center + radius))


