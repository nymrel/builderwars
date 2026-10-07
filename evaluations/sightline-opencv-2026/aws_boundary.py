"""Credential-free AWS planning boundary for the Sightline competition lane.

This module deliberately contains no AWS SDK import and exposes no execution method.
It can only validate and serialize a prospective deployment plan.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Mapping


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ARTIFACT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SENSITIVE_AWS_KEYS = frozenset(
    {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_WEB_IDENTITY_TOKEN_FILE",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
        "AWS_CONTAINER_CREDENTIALS_FULL_URI",
        "AWS_PROFILE",
    }
)


@dataclass(frozen=True)
class InertAWSPlan:
    schema: str
    service: str
    region: str
    runtime: str
    artifact_name: str
    artifact_sha256: str
    artifact_bytes: int
    operation: str
    execute: bool
    credentials_available: bool
    deployment_authorized: bool
    spend_authorized: bool

    def as_dict(self) -> dict[str, str | int | bool]:
        return asdict(self)


class InertAWSBoundary:
    """Builds reviewable plans while refusing credentials and authority."""

    def __init__(
        self,
        *,
        allowed_regions: tuple[str, ...] = ("us-west-2",),
        credentials_available: bool = False,
        deployment_authorized: bool = False,
        spend_authorized: bool = False,
    ) -> None:
        if not allowed_regions or any(not region for region in allowed_regions):
            raise ValueError("at least one non-empty AWS region is required")
        if credentials_available or deployment_authorized or spend_authorized:
            raise PermissionError("inert boundary requires all authority flags to remain false")
        self.allowed_regions = allowed_regions

    @staticmethod
    def assert_credential_free(environment: Mapping[str, str]) -> None:
        present = sorted(key for key in _SENSITIVE_AWS_KEYS if environment.get(key))
        if present:
            raise PermissionError(
                "credential-bearing AWS environment rejected: " + ",".join(present)
            )

    def prepare_plan(
        self,
        *,
        artifact_name: str,
        artifact_sha256: str,
        artifact_bytes: int,
        region: str = "us-west-2",
    ) -> InertAWSPlan:
        if not _ARTIFACT_NAME.fullmatch(artifact_name):
            raise ValueError("artifact_name must be a bounded portable filename")
        if not _SHA256.fullmatch(artifact_sha256):
            raise ValueError("artifact_sha256 must be lowercase hexadecimal SHA-256")
        if artifact_bytes < 1 or artifact_bytes > 50 * 1024 * 1024:
            raise ValueError("artifact_bytes must be between 1 and 52428800")
        if region not in self.allowed_regions:
            raise ValueError("AWS region is not in the inert allowlist")

        return InertAWSPlan(
            schema="sightline.aws-plan.v1",
            service="lambda",
            region=region,
            runtime="python3.12",
            artifact_name=artifact_name,
            artifact_sha256=artifact_sha256,
            artifact_bytes=artifact_bytes,
            operation="prepare_only",
            execute=False,
            credentials_available=False,
            deployment_authorized=False,
            spend_authorized=False,
        )
