#!/usr/bin/env python3
"""AgentWars customer-local runner CLI.

Install ``bin`` on PATH and use:

    agentwars runner pair ...
    agentwars runner activate --challenge-id ... --runner-id ...
    agentwars runner probe --challenge-id ...
    agentwars runner work --challenge-id ... --once
    agentwars runner prepare-match --challenge-id ... --once ...
    agentwars runner run-prepared-match --plan ... --once ...
    agentwars runner submit-match --challenge-id ... --once ...
    agentwars runner request ...
    agentwars provider catalog
    agentwars provider connect-plan openrouter

Pairing secrets and key passphrases are accepted only through no-echo prompts.
The CLI never reads provider credential stores. The local copy of an explicitly
requested OpenRouter PKCE key is held only in this customer process for one
fixed match; it is never printed, serialized, or sent to BuildWars. The
provider-side key may persist until the customer revokes it in OpenRouter.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import os
import re
import sys
import warnings
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent_identity.keys import MIN_PASSPHRASE_CHARACTERS  # noqa: E402
from competitions.evidence_job import (  # noqa: E402
    COMPETITION_JOB_PREPARE_BODY,
    COMPETITION_JOB_PREPARE_PATH,
    COMPETITION_JOB_POLL_BODY,
    COMPETITION_JOB_POLL_PATH,
    COMPETITION_JOB_RESULT_PATH,
    CompetitionGrant,
    CompetitionPreparation,
    build_competition_evidence,
    validate_competition_prepare_response,
    validate_competition_poll_response,
    validate_competition_result_response,
)
from competitions.source_match import (  # noqa: E402
    build_source_match_plan,
    write_source_match_plan,
)
from competitions.prepared_match import (  # noqa: E402
    execute_prepared_match,
    load_prepared_match,
)
from provider_hub.catalog import (  # noqa: E402
    EXECUTABLE_PROVIDER_IDS,
    PROVIDER_IDS,
    connect_plan,
    get_provider,
    public_catalog,
)
from provider_hub.local_runner import (  # noqa: E402
    MAX_BODY_BYTES,
    PRODUCTION_ORIGIN,
    RUNNER_PROBE_BODY,
    RUNNER_PROBE_PATH,
    RunnerClientError,
    claim_runner,
    digest_harness_file,
    grouped_fingerprint,
    parse_pairing_secret,
    send_signed_request,
    sign_runner_request,
    validate_probe_response,
)
from provider_hub.match_worker import (  # noqa: E402
    MATCH_JOB_POLL_BODY,
    MATCH_JOB_POLL_PATH,
    MATCH_JOB_RESULT_PATH,
    FixtureGrant,
    compute_closed_fixture,
    encode_result_request,
    validate_poll_response,
    validate_result_response,
)
from provider_hub.runner_state import RunnerStateStore  # noqa: E402
from provider_hub.secrets import SecretValue  # noqa: E402
from provider_hub.pkce import (  # noqa: E402
    PkceError,
    authorize_openrouter_loopback,
)


_PAIRING_SECRET_ARG_RE = re.compile(r"awp1_[A-Za-z0-9_-]{22}_[A-Za-z0-9_-]{32}")
_SECRET_OPTION_NAMES = frozenset(
    ("--pairing-secret", "--passphrase", "--key-passphrase")
)
_SECRET_OPTION_STEMS = tuple(
    option.removeprefix("--") for option in _SECRET_OPTION_NAMES
)


def _hidden_prompt(label: str) -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            return getpass.getpass(label)
    except (getpass.GetPassWarning, EOFError) as error:
        raise RunnerClientError(
            "a real interactive no-echo terminal is required"
        ) from error


def _new_key_passphrase() -> SecretValue:
    first = _hidden_prompt(
        f"passphrase for the encrypted runner key (min {MIN_PASSPHRASE_CHARACTERS} chars): "
    )
    if len(first) < MIN_PASSPHRASE_CHARACTERS:
        raise RunnerClientError(
            f"runner key passphrase must be at least {MIN_PASSPHRASE_CHARACTERS} characters"
        )
    second = _hidden_prompt("repeat runner key passphrase: ")
    if first != second:
        raise RunnerClientError("runner key passphrases do not match")
    return SecretValue(first.encode("utf-8"))


def _existing_key_passphrase() -> SecretValue:
    value = _hidden_prompt("passphrase for the encrypted runner key: ")
    if not value:
        raise RunnerClientError("runner key passphrase is required")
    return SecretValue(value.encode("utf-8"))


def _pairing_secret_prompt() -> SecretValue:
    value = _hidden_prompt("one-time AgentWars pairing secret: ")
    parse_pairing_secret(value)
    return SecretValue(value)


def _bounded_timeout(value: str) -> int:
    try:
        timeout = int(value)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError(
            "timeout must be an integer from 1 to 60 seconds"
        ) from error
    if not 1 <= timeout <= 60:
        raise argparse.ArgumentTypeError(
            "timeout must be an integer from 1 to 60 seconds"
        )
    return timeout


def _bounded_backend_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError(
            "backend timeout must be a number from 10 to 900 seconds"
        ) from error
    if not 10 <= timeout <= 900:
        raise argparse.ArgumentTypeError(
            "backend timeout must be a number from 10 to 900 seconds"
        )
    return float(format(timeout, ".3f"))


def _bounded_authorization_timeout(value: str) -> int:
    try:
        timeout = int(value)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError(
            "authorization timeout must be an integer from 10 to 600 seconds"
        ) from error
    if not 10 <= timeout <= 600:
        raise argparse.ArgumentTypeError(
            "authorization timeout must be an integer from 10 to 600 seconds"
        )
    return timeout


def _looks_like_secret_option(argument: object) -> bool:
    token = str(argument)
    if not token.startswith("-"):
        return False
    name = token.split("=", 1)[0].lstrip("-").lower().replace("_", "-")
    return len(name) >= 3 and any(
        stem.startswith(name) for stem in _SECRET_OPTION_STEMS
    )


def cmd_runner_pair(args) -> int:
    harness_digest = digest_harness_file(args.harness_file)
    pairing_secret = _pairing_secret_prompt()
    challenge_id, _random_code = parse_pairing_secret(pairing_secret.reveal())
    store = RunnerStateStore(args.state_dir)
    # Confirming twice is intentional even on a retry.  It avoids a racy,
    # pre-lock "new or existing" branch and never moves the passphrase to argv.
    passphrase = _new_key_passphrase()
    profile, _key, created = store.prepare(
        challenge_id=challenge_id,
        passphrase=passphrase.reveal(),
        endpoint_origin=args.origin,
        provider_id=args.provider,
        display_label=args.display_label,
        harness_id=args.harness_id,
        harness_version=args.harness_version,
        harness_digest=harness_digest,
    )
    result = claim_runner(
        origin=profile["endpointOrigin"],
        pairing_secret=pairing_secret.reveal(),
        provider_id=profile["providerId"],
        display_label=profile["displayLabel"],
        harness_id=profile["harnessId"],
        harness_version=profile["harnessVersion"],
        harness_digest=profile["harnessDigest"],
        public_key=profile["publicKey"],
        fingerprint=profile["fingerprint"],
        timeout_seconds=args.timeout,
    )
    profile = store.mark_claim_accepted(challenge_id, result.status)
    print("Local runner claim accepted; browser confirmation is still required.")
    print(f"challenge   : {challenge_id}")
    print(f"fingerprint : {grouped_fingerprint(profile['fingerprint'])}")
    print(
        f"key custody : encrypted local PKCS#8 ({'created' if created else 'reused'})"
    )
    print()
    print(
        "Compare every fingerprint group with the signed-in browser, then confirm there."
    )
    print("After confirmation, copy the public runner id and record it locally:")
    activate = f"  agentwars runner activate --challenge-id {challenge_id} --runner-id awr1_..."
    if args.state_dir:
        activate += f' --state-dir "{store.root}"'
    print(activate)
    print()
    print(
        "This claim does not attest a provider, plan, billing route, model, runtime, or match."
    )
    return 0


def cmd_runner_activate(args) -> int:
    store = RunnerStateStore(args.state_dir)
    profile = store.record_runner_id(args.challenge_id, args.runner_id)
    print("Runner id recorded locally as owner-entered and unverified.")
    print(f"runner id   : {profile['runnerId']}")
    print(f"fingerprint : {grouped_fingerprint(profile['fingerprint'])}")
    print("The next signed server request must still verify this exact active key.")
    return 0


def cmd_runner_list(args) -> int:
    profiles = RunnerStateStore(args.state_dir).list_profiles()
    if not profiles:
        print("No local AgentWars runner profiles.")
        return 0
    for profile in profiles:
        print(f"{profile['displayLabel']}")
        print(f"  challenge : {profile['challengeId']}")
        print(f"  runner    : {profile['runnerId'] or 'not recorded'}")
        print(f"  state     : {profile['localState']}")
        print(f"  provider  : {profile['providerId']} ({profile['connectionMode']})")
        print(f"  harness   : {profile['harnessId']}@{profile['harnessVersion']}")
        print(f"  digest    : {profile['harnessDigest']}")
        print(f"  fingerprint: {grouped_fingerprint(profile['fingerprint'])}")
        print("  attestations: provider/model/runtime/execution all false")
    return 0


def cmd_runner_probe(args) -> int:
    store = RunnerStateStore(args.state_dir)
    profile = store.load_profile(args.challenge_id)
    if (
        profile["localState"] != "runner_id_recorded_unverified"
        or profile["runnerId"] is None
    ):
        raise RunnerClientError(
            "record the browser-issued runner id before probing the active key"
        )
    passphrase = _existing_key_passphrase()
    key = store.load_key(profile, passphrase.reveal())
    signed = sign_runner_request(
        key,
        origin=profile["endpointOrigin"],
        method="POST",
        path=RUNNER_PROBE_PATH,
        body=RUNNER_PROBE_BODY,
        runner_id=profile["runnerId"],
    )
    status, payload, raw = send_signed_request(
        origin=profile["endpointOrigin"],
        signed=signed,
        timeout_seconds=args.timeout,
    )
    if status != 200:
        raise RunnerClientError("runner probe returned a contradictory HTTP status")
    result = validate_probe_response(
        payload,
        runner_id=profile["runnerId"],
        fingerprint=profile["fingerprint"],
        request_body_sha256=signed.body_sha256,
    )
    print("Server returned the exact active-key probe contract.")
    print(f"runner id   : {result.runner_id}")
    print(f"fingerprint : {grouped_fingerprint(result.fingerprint)}")
    print(f"request sha : {result.request_body_sha256}")
    print(f"response sha: {hashlib.sha256(raw).hexdigest()}")
    print(
        "This response is evidence only that the configured server accepted possession of this active local signing key."
    )
    print(
        "Provider account, subscription, billing, model, person, runtime, harness, and match attestations remain false."
    )
    return 0


def cmd_runner_work(args) -> int:
    """Poll and complete at most one closed deterministic fixture job."""

    if args.once is not True:
        raise RunnerClientError("runner work requires explicit --once consent")
    store = RunnerStateStore(args.state_dir)
    profile = store.load_profile(args.challenge_id)
    if (
        profile["localState"] != "runner_id_recorded_unverified"
        or profile["runnerId"] is None
    ):
        raise RunnerClientError(
            "record the browser-issued runner id before polling for work"
        )
    passphrase = _existing_key_passphrase()
    key = store.load_key(profile, passphrase.reveal())

    poll = sign_runner_request(
        key,
        origin=profile["endpointOrigin"],
        method="POST",
        path=MATCH_JOB_POLL_PATH,
        body=MATCH_JOB_POLL_BODY,
        runner_id=profile["runnerId"],
    )
    poll_status, poll_payload, _poll_raw = send_signed_request(
        origin=profile["endpointOrigin"],
        signed=poll,
        timeout_seconds=args.timeout,
    )
    if poll_status != 200:
        raise RunnerClientError("match-job poll returned a contradictory HTTP status")
    grant_or_terminal = validate_poll_response(
        poll_payload,
        profile=profile,
        request_body_sha256=poll.body_sha256,
    )
    if not isinstance(grant_or_terminal, FixtureGrant):
        print(
            f"Server reports the deterministic fixture job as {grant_or_terminal.status}."
        )
        if grant_or_terminal.conformance is not None:
            print(f"digest conformance : {grant_or_terminal.conformance}")
        print(
            "No provider, model, subprocess, or arbitrary harness was invoked by this command."
        )
        print("Provider/model/runtime/harness/match attestations remain false.")
        return 0 if grant_or_terminal.conformance == "match" else 1

    computation = compute_closed_fixture(grant_or_terminal)
    result_body = encode_result_request(grant_or_terminal, computation)
    result = sign_runner_request(
        key,
        origin=profile["endpointOrigin"],
        method="POST",
        path=MATCH_JOB_RESULT_PATH,
        body=result_body,
        runner_id=profile["runnerId"],
    )
    result_status, result_payload, _result_raw = send_signed_request(
        origin=profile["endpointOrigin"],
        signed=result,
        timeout_seconds=args.timeout,
    )
    if result_status != 200:
        raise RunnerClientError("match-job result returned a contradictory HTTP status")
    receipt = validate_result_response(
        result_payload,
        profile=profile,
        request_body_sha256=result.body_sha256,
        grant=grant_or_terminal,
        computation=computation,
    )
    print("Completed one built-in deterministic AgentWars fixture job.")
    print(f"job id             : {grant_or_terminal.job.job_id}")
    print(f"attempt id         : {grant_or_terminal.attempt_id}")
    print(f"output sha256      : {computation.output_sha256}")
    print(f"transcript sha256  : {computation.transcript_sha256}")
    print(f"digest conformance : {receipt.conformance}")
    print(f"duplicate receipt  : {'yes' if receipt.duplicate else 'no'}")
    print(
        "This is digest conformance only; no provider, model, subprocess, or arbitrary harness was invoked."
    )
    print("Provider/model/runtime/harness/match attestations remain false.")
    return 0 if receipt.conformance == "match" else 1


def cmd_runner_submit_match(args) -> int:
    """Submit one existing replay-verified customer-local match privately."""

    if (
        args.once is not True
        or args.customer_local_v1 is not True
        or args.provider_usage_v1 is not True
        or args.private_evidence_upload_v1 is not True
    ):
        raise RunnerClientError(
            "match submission requires --once and all three explicit consent flags"
        )
    store = RunnerStateStore(args.state_dir)
    profile = store.load_profile(args.challenge_id)
    if (
        profile["localState"] != "runner_id_recorded_unverified"
        or profile["runnerId"] is None
    ):
        raise RunnerClientError(
            "record the browser-issued runner id before submitting a match"
        )
    passphrase = _existing_key_passphrase()
    key = store.load_key(profile, passphrase.reveal())

    poll = sign_runner_request(
        key,
        origin=profile["endpointOrigin"],
        method="POST",
        path=COMPETITION_JOB_POLL_PATH,
        body=COMPETITION_JOB_POLL_BODY,
        runner_id=profile["runnerId"],
    )
    poll_status, poll_payload, _poll_raw = send_signed_request(
        origin=profile["endpointOrigin"],
        signed=poll,
        timeout_seconds=args.timeout,
    )
    if poll_status != 200:
        raise RunnerClientError(
            "competition-job poll returned a contradictory HTTP status"
        )
    grant_or_terminal = validate_competition_poll_response(
        poll_payload,
        profile=profile,
        request_body_sha256=poll.body_sha256,
    )
    if not isinstance(grant_or_terminal, CompetitionGrant):
        print(
            f"Server reports the private competition job as {grant_or_terminal.status}."
        )
        if grant_or_terminal.truth_status is not None:
            print(f"truth status : {grant_or_terminal.truth_status}")
        print(
            "No provider, model, subprocess, or arbitrary harness was invoked by this command."
        )
        print("No publication or provider/model ranking was requested.")
        return 0 if grant_or_terminal.status == "completed" else 1

    evidence = build_competition_evidence(
        grant_or_terminal,
        summary_path=args.summary_file,
        transcript_path=args.transcript_file,
    )
    result = sign_runner_request(
        key,
        origin=profile["endpointOrigin"],
        method="POST",
        path=COMPETITION_JOB_RESULT_PATH,
        body=evidence.result_body,
        runner_id=profile["runnerId"],
    )
    result_status, result_payload, _result_raw = send_signed_request(
        origin=profile["endpointOrigin"],
        signed=result,
        timeout_seconds=args.timeout,
    )
    if result_status != 200:
        raise RunnerClientError(
            "competition result returned a contradictory HTTP status"
        )
    receipt = validate_competition_result_response(
        result_payload,
        profile=profile,
        request_body_sha256=result.body_sha256,
        grant=grant_or_terminal,
        evidence=evidence,
    )
    print("Submitted one replay-verified customer-local match for private review.")
    print(f"job id          : {grant_or_terminal.job.job_id}")
    print(f"competition id  : {grant_or_terminal.job.competition_id}")
    print(f"match id        : {evidence.summary['matchId']}")
    print(f"bundle sha256   : {evidence.evidence_bundle_sha256}")
    print(f"truth status    : {receipt.truth_status}")
    print(f"verification    : {receipt.verification_status}")
    print(f"duplicate       : {'yes' if receipt.duplicate else 'no'}")
    print("The source files remain customer-local and are not deleted by this command.")
    print(
        "The server receipt remains private, unpublished, ranking-ineligible, and unattested."
    )
    print(
        "No provider, model, subprocess, or arbitrary harness was invoked by this command."
    )
    return 0


def cmd_runner_prepare_match(args) -> int:
    """Prepare, but never execute, one exact customer-local source match."""

    if args.once is not True:
        raise RunnerClientError("match preparation requires --once")
    store = RunnerStateStore(args.state_dir)
    profile = store.load_profile(args.challenge_id)
    if (
        profile["localState"] != "runner_id_recorded_unverified"
        or profile["runnerId"] is None
    ):
        raise RunnerClientError(
            "record the browser-issued runner id before preparing a match"
        )
    passphrase = _existing_key_passphrase()
    key = store.load_key(profile, passphrase.reveal())
    request = sign_runner_request(
        key,
        origin=profile["endpointOrigin"],
        method="POST",
        path=COMPETITION_JOB_PREPARE_PATH,
        body=COMPETITION_JOB_PREPARE_BODY,
        runner_id=profile["runnerId"],
    )
    status, payload, _raw = send_signed_request(
        origin=profile["endpointOrigin"],
        signed=request,
        timeout_seconds=args.timeout,
    )
    if status != 200:
        raise RunnerClientError(
            "competition preparation returned a contradictory HTTP status"
        )
    preparation = validate_competition_prepare_response(
        payload,
        profile=profile,
        request_body_sha256=request.body_sha256,
    )
    if not isinstance(preparation, CompetitionPreparation):
        print(f"Server reports the private competition job as {preparation.status}.")
        if preparation.job_id is not None:
            print(f"job id         : {preparation.job_id}")
        if preparation.competition_id is not None:
            print(f"competition id : {preparation.competition_id}")
        if preparation.truth_status is not None:
            print(f"truth status   : {preparation.truth_status}")
        print(
            "No lease was acquired and no provider, model, subprocess, or harness was invoked."
        )
        return 0 if preparation.status == "completed" else 1

    passport_paths = (
        tuple(args.agent_passports) if args.agent_passports is not None else None
    )
    plan = build_source_match_plan(
        preparation,
        profile=profile,
        plan_path=args.plan_out,
        match_directory=args.match_dir,
        summary_path=args.summary_file,
        passport_paths=passport_paths,
        backend_timeout=args.backend_timeout,
    )
    target = write_source_match_plan(args.plan_out, plan)
    print("Prepared one exact customer-local AgentWars source match.")
    print(f"job id            : {preparation.job.job_id}")
    print(f"competition id    : {preparation.job.competition_id}")
    print(f"launch plan       : {target}")
    print(f"launch plan sha256: {plan['launchPlanDigest']}")
    print("Inspect the plan before separately starting its fixed local match runner.")
    print(
        "This command acquired no lease, spent no provider quota, and launched no subprocess."
    )
    print("Provider/model/runtime/harness/match attestations remain false.")
    return 0


def cmd_runner_run_prepared_match(args) -> int:
    preflight = load_prepared_match(args.plan)
    uses_openrouter = "openrouter" in preflight.provider_ids
    pkce_key = None
    if (
        args.openrouter_provider_key_persists_v1
        and not args.openrouter_pkce_v1
    ):
        raise RunnerClientError(
            "--openrouter-provider-key-persists-v1 requires --openrouter-pkce-v1"
        )
    try:
        if args.openrouter_pkce_v1:
            if not uses_openrouter:
                raise RunnerClientError(
                    "OpenRouter authorization was requested for a plan without OpenRouter"
                )
            if not args.openrouter_provider_key_persists_v1:
                raise RunnerClientError(
                    "OpenRouter PKCE requires --openrouter-provider-key-persists-v1 "
                    "because removing local custody does not revoke the provider-side key"
                )
            if "OPENROUTER_API_KEY" in os.environ:
                raise RunnerClientError(
                    "OpenRouter environment key already exists; omit --openrouter-pkce-v1"
                )

            def announce(authorize_url):
                print("Approve one customer-owned OpenRouter key for this match.")
                print("If the browser does not open, paste this URL into your browser:")
                print(authorize_url)
                print(
                    "Waiting on the exact local callback; no credential is sent to BuildWars."
                )

            try:
                pkce_key = authorize_openrouter_loopback(
                    timeout_seconds=args.openrouter_auth_timeout,
                    announce=announce,
                )
            except PkceError as error:
                raise RunnerClientError(
                    f"OpenRouter authorization failed: {error}. If browser approval "
                    "completed, review or revoke any newly created key in your "
                    "OpenRouter dashboard"
                ) from None
            if not isinstance(pkce_key, SecretValue):
                raise RunnerClientError(
                    "OpenRouter authorization did not return one wrapped key"
                )
            print("OpenRouter authorization received; running the one fixed match now.")
        elif uses_openrouter and "OPENROUTER_API_KEY" not in os.environ:
            raise RunnerClientError(
                "prepared match uses OpenRouter; set OPENROUTER_API_KEY locally or pass "
                "--openrouter-pkce-v1"
            )

        prepared, status = execute_prepared_match(
            args.plan,
            customer_local_v1=args.customer_local_v1,
            provider_usage_v1=args.provider_usage_v1,
            expected_launch_plan_digest=preflight.launch_plan_digest,
            openrouter_api_key=pkce_key,
        )
    finally:
        if pkce_key is not None:
            print(
                "Local OpenRouter environment custody ended. The provider-side key may "
                "remain active; review or revoke the newly created key in your "
                "OpenRouter dashboard."
            )
    if status in (0, 2):
        print("Completed one fixed customer-local prepared match.")
        print(f"job id            : {prepared.job_id}")
        print(f"competition id    : {prepared.competition_id}")
        print(f"launch plan sha256: {prepared.launch_plan_digest}")
        print(f"match directory   : {prepared.match_directory}")
        print(f"summary file      : {prepared.summary_file}")
        if status == 2:
            print(
                "The match replay passed, but at least one accepted move used the declared fallback path."
            )
        print("Provider/model/runtime/harness/match attestations remain false.")
    return status


def cmd_provider_catalog(_args) -> int:
    """Print current non-secret provider route facts without probing accounts."""

    for provider_id, entry in public_catalog():
        print(f"{provider_id} - {entry['display_name']}")
        print(f"  mode      : {entry['connection_mode']}")
        print(f"  transport : {entry['connection_transport']}")
        print(f"  execution : {'customer-local' if entry['local_execution'] else 'disabled'}")
        print(f"  custody   : {entry['credential_custody']}")
        print(f"  evidence  : {entry['evidence_date']}")
    print()
    print("This is policy and route discovery only. No account or credential was read.")
    return 0


def cmd_provider_connect_plan(args) -> int:
    """Print one current customer-owned setup plan without starting it."""

    plan = connect_plan(args.provider)
    entry = get_provider(args.provider)
    print(f"Provider route - {plan['provider']} ({plan['display_name']})")
    print(f"mode: {plan['connection_mode']}")
    print(f"transport: {entry['connection_transport']}")
    print(f"execution: {'customer-local' if entry['local_execution'] else 'disabled'}")
    print(f"evidence date: {entry['evidence_date']}")
    print()
    for step in plan["steps"]:
        print(step)
    print()
    print(plan["custody"])
    print(f"Status: {plan['status']}")
    if plan["limitations"]:
        print("Limitations:")
        for line in plan["limitations"]:
            print(f"  - {line}")
    print()
    print("No login, browser, network request, account probe, or credential read occurred.")
    return 0


def _read_request_body(path: str) -> bytes:
    if path == "-":
        raw = sys.stdin.buffer.read(MAX_BODY_BYTES + 1)
    else:
        candidate = Path(path)
        if candidate.is_symlink() or not candidate.is_file():
            raise RunnerClientError(
                "request body path must be one regular non-symlink file"
            )
        try:
            with candidate.open("rb") as handle:
                raw = handle.read(MAX_BODY_BYTES + 1)
        except OSError as error:
            raise RunnerClientError("request body file could not be read") from error
    if len(raw) > MAX_BODY_BYTES:
        raise RunnerClientError("request body exceeds 65536 bytes")
    return raw


def _write_response(path: str, raw: bytes):
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise RunnerClientError("refusing to overwrite an existing response file")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise RunnerClientError(
            "response output directory could not be created"
        ) from error
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = None
    created = False
    try:
        descriptor = os.open(target, flags, 0o600)
        created = True
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
    except BaseException as error:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if created:
            try:
                target.unlink()
            except OSError:
                pass
        if isinstance(error, OSError):
            raise RunnerClientError("response file could not be written") from error
        raise


def cmd_runner_request(args) -> int:
    store = RunnerStateStore(args.state_dir)
    profile = store.load_profile(args.challenge_id)
    if (
        profile["localState"] != "runner_id_recorded_unverified"
        or profile["runnerId"] is None
    ):
        raise RunnerClientError(
            "record the browser-issued runner id before signing a request"
        )
    passphrase = _existing_key_passphrase()
    key = store.load_key(profile, passphrase.reveal())
    signed = sign_runner_request(
        key,
        origin=profile["endpointOrigin"],
        method=args.method,
        path=args.path,
        body=_read_request_body(args.body_file),
        runner_id=profile["runnerId"],
    )
    status, _payload, raw = send_signed_request(
        origin=profile["endpointOrigin"],
        signed=signed,
        timeout_seconds=args.timeout,
    )
    if args.response_out:
        _write_response(args.response_out, raw)
    print(f"server returned HTTP {status} for the signed request")
    print(f"request body sha256 : {signed.body_sha256}")
    print(f"response bytes      : {len(raw)}")
    print(f"response sha256     : {hashlib.sha256(raw).hexdigest()}")
    if args.response_out:
        print(f"response written    : {args.response_out}")
    else:
        print(
            "response body not printed; use --response-out with a new path to retain it"
        )
    print(
        "A 2xx response is transport evidence only; the CLI cannot attest server implementation or model execution."
    )
    return 0


def cmd_runner_forget(args) -> int:
    store = RunnerStateStore(args.state_dir)
    profile = store.load_profile(args.challenge_id)
    if not args.yes:
        try:
            answer = input(
                f"Permanently delete the encrypted key for {profile['displayLabel']} "
                f"({profile['fingerprint'][-8:]})? Type DELETE: "
            )
        except EOFError as error:
            raise RunnerClientError(
                "an interactive DELETE confirmation or --yes is required"
            ) from error
        if answer != "DELETE":
            print("Local key retained.")
            return 1
    removed = store.forget(args.challenge_id)
    print(f"Deleted local encrypted key and profile for {removed['displayLabel']}.")
    print(
        "This local deletion cannot be recovered. Revoke the server runner separately if needed."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentwars",
        description="Customer-local AgentWars runner pairing and signed requests.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    provider = commands.add_parser(
        "provider", help="inspect customer-owned provider routes without connecting"
    )
    provider_commands = provider.add_subparsers(
        dest="provider_command", required=True
    )
    provider_catalog = provider_commands.add_parser(
        "catalog", help="list every known provider route and current availability"
    )
    provider_catalog.set_defaults(func=cmd_provider_catalog)
    provider_plan = provider_commands.add_parser(
        "connect-plan", help="show the current local setup or disabled state"
    )
    provider_plan.add_argument("provider", choices=PROVIDER_IDS)
    provider_plan.set_defaults(func=cmd_provider_connect_plan)

    runner = commands.add_parser(
        "runner", help="manage one customer-local signing runner"
    )
    runner_commands = runner.add_subparsers(dest="runner_command", required=True)

    pair = runner_commands.add_parser(
        "pair",
        help="claim a browser-created one-time secret with a new encrypted Ed25519 key",
    )
    pair.add_argument("--provider", choices=EXECUTABLE_PROVIDER_IDS, required=True)
    pair.add_argument("--display-label", required=True)
    pair.add_argument("--harness-id", required=True)
    pair.add_argument("--harness-version", required=True)
    pair.add_argument("--harness-file", required=True)
    pair.add_argument("--origin", default=PRODUCTION_ORIGIN)
    pair.add_argument("--state-dir")
    pair.add_argument("--timeout", type=_bounded_timeout, default=15)
    pair.set_defaults(func=cmd_runner_pair)

    activate = runner_commands.add_parser(
        "activate",
        help="record the public runner id shown after browser confirmation",
    )
    activate.add_argument("--challenge-id", required=True)
    activate.add_argument("--runner-id", required=True)
    activate.add_argument("--state-dir")
    activate.set_defaults(func=cmd_runner_activate)

    listing = runner_commands.add_parser(
        "list", help="show public local runner metadata"
    )
    listing.add_argument("--state-dir")
    listing.set_defaults(func=cmd_runner_list)

    probe = runner_commands.add_parser(
        "probe",
        help="verify that the configured server accepts the recorded active signing key",
    )
    probe.add_argument("--challenge-id", required=True)
    probe.add_argument("--state-dir")
    probe.add_argument("--timeout", type=_bounded_timeout, default=15)
    probe.set_defaults(func=cmd_runner_probe)

    work = runner_commands.add_parser(
        "work",
        help="poll and complete one closed deterministic fixture job",
    )
    work.add_argument("--challenge-id", required=True)
    work.add_argument(
        "--once",
        action="store_true",
        required=True,
        help="explicitly limit this invocation to at most one fixture job",
    )
    work.add_argument("--state-dir")
    work.add_argument("--timeout", type=_bounded_timeout, default=15)
    work.set_defaults(func=cmd_runner_work)

    prepare = runner_commands.add_parser(
        "prepare-match",
        help="write one exact non-executing customer-local source-match plan",
        description=(
            "Fetch one signed non-leasing private job declaration, verify its paired "
            "harness and optional Agent Passports, and write a new immutable local "
            "launch plan. This command never calls a provider or starts a subprocess."
        ),
    )
    prepare.add_argument("--challenge-id", required=True)
    prepare.add_argument("--plan-out", required=True)
    prepare.add_argument("--match-dir", required=True)
    prepare.add_argument("--summary-file", required=True)
    prepare.add_argument(
        "--backend-timeout", type=_bounded_backend_timeout, default=180.0
    )
    prepare.add_argument(
        "--agent-passports",
        nargs=2,
        metavar=("SEAT0_JSON", "SEAT1_JSON"),
        help="two public signed passport files when the job binds signed agent versions",
    )
    prepare.add_argument(
        "--once",
        action="store_true",
        required=True,
        help="explicitly limit this invocation to one non-leasing preparation request",
    )
    prepare.add_argument("--state-dir")
    prepare.add_argument("--timeout", type=_bounded_timeout, default=15)
    prepare.set_defaults(func=cmd_runner_prepare_match)

    run_prepared = runner_commands.add_parser(
        "run-prepared-match",
        help="validate and run one fixed customer-local source-match plan",
        description=(
            "Revalidate one digest-bound local plan, current fixed runner and harness, "
            "public Agent Passports, exact argv, and unused output paths before starting "
            "the fixed cross-provider fantasy runner. The plan cannot supply a command, "
            "entrypoint, environment, or execution consent."
        ),
    )
    run_prepared.add_argument("--plan", required=True)
    run_prepared.add_argument(
        "--once",
        action="store_true",
        required=True,
        help="explicitly limit this invocation to one prepared local match",
    )
    run_prepared.add_argument(
        "--customer-local-v1",
        action="store_true",
        required=True,
        help="confirm this match runs on a customer-controlled local machine",
    )
    run_prepared.add_argument(
        "--provider-usage-v1",
        action="store_true",
        required=True,
        help="accept that provider calls consume customer-owned quota or may incur charges",
    )
    run_prepared.add_argument(
        "--openrouter-pkce-v1",
        action="store_true",
        help=(
            "when the plan uses OpenRouter and no environment key exists, authorize "
            "one customer-owned key for one-match local use via a loopback browser callback"
        ),
    )
    run_prepared.add_argument(
        "--openrouter-provider-key-persists-v1",
        action="store_true",
        help=(
            "acknowledge that ending local key custody does not revoke the "
            "provider-side OpenRouter key; review or revoke it in the dashboard"
        ),
    )
    run_prepared.add_argument(
        "--openrouter-auth-timeout",
        type=_bounded_authorization_timeout,
        default=180,
        metavar="SECONDS",
        help="bounded loopback authorization wait (10-600 seconds; default 180)",
    )
    run_prepared.set_defaults(func=cmd_runner_run_prepared_match)

    submit = runner_commands.add_parser(
        "submit-match",
        help="privately submit one existing replay-verified customer-local fantasy match",
        description=(
            "Poll one exact competition evidence job and privately submit existing local "
            "summary/transcript files. This command does not invoke a provider, model, "
            "subprocess, or arbitrary harness and cannot publish or rank the result."
        ),
    )
    submit.add_argument("--challenge-id", required=True)
    submit.add_argument("--summary-file", required=True)
    submit.add_argument("--transcript-file", required=True)
    submit.add_argument(
        "--once",
        action="store_true",
        required=True,
        help="explicitly limit this invocation to at most one competition evidence job",
    )
    submit.add_argument(
        "--customer-local-v1",
        action="store_true",
        required=True,
        help="confirm that the evidence came from a customer-controlled local runner",
    )
    submit.add_argument(
        "--provider-usage-v1",
        action="store_true",
        required=True,
        help="confirm the customer accepted provider quota or charge implications when the match ran",
    )
    submit.add_argument(
        "--private-evidence-upload-v1",
        action="store_true",
        required=True,
        help="consent to upload the replay-safe transcript and summary for private review",
    )
    submit.add_argument("--state-dir")
    submit.add_argument("--timeout", type=_bounded_timeout, default=15)
    submit.set_defaults(func=cmd_runner_submit_match)

    request = runner_commands.add_parser(
        "request",
        help="send one exact JSON request signed by a recorded runner key",
    )
    request.add_argument("--challenge-id", required=True)
    request.add_argument(
        "--method", choices=("POST", "PUT", "PATCH", "DELETE"), required=True
    )
    request.add_argument(
        "--path", required=True, help="exact server pathname; query strings are refused"
    )
    request.add_argument(
        "--body-file",
        required=True,
        help="exact UTF-8 JSON object bytes, or - for stdin",
    )
    request.add_argument(
        "--response-out",
        help="new file for the bounded JSON response; never overwritten",
    )
    request.add_argument("--state-dir")
    request.add_argument("--timeout", type=_bounded_timeout, default=15)
    request.set_defaults(func=cmd_runner_request)

    forget = runner_commands.add_parser(
        "forget",
        help="irreversibly delete one local encrypted key and profile",
    )
    forget.add_argument("--challenge-id", required=True)
    forget.add_argument("--state-dir")
    forget.add_argument(
        "--yes", action="store_true", help="skip the DELETE confirmation prompt"
    )
    forget.set_defaults(func=cmd_runner_forget)
    return parser


def main(argv=None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if any(_PAIRING_SECRET_ARG_RE.search(str(argument)) for argument in raw_argv):
        print(
            "ERROR: pairing-secret-shaped argv is forbidden; use the no-echo prompt",
            file=sys.stderr,
        )
        return 2
    if any(_looks_like_secret_option(argument) for argument in raw_argv):
        print(
            "ERROR: secret and passphrase arguments are forbidden; use the no-echo prompt",
            file=sys.stderr,
        )
        return 2
    parser = build_parser()
    args = parser.parse_args(raw_argv)
    try:
        return args.func(args)
    except RunnerClientError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(
            "ERROR: operation cancelled; encrypted local state may already exist, and match "
            "output paths may already be reserved. Descendant-process cleanup was requested. "
            "Inspect runner state and exact outputs before retrying.",
            file=sys.stderr,
        )
        return 130
    except Exception:
        print("ERROR: unexpected internal runner failure", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
