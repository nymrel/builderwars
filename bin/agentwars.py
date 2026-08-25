#!/usr/bin/env python3
"""AgentWars customer-local runner CLI.

Install ``bin`` on PATH and use:

    agentwars runner pair ...
    agentwars runner activate --challenge-id ... --runner-id ...
    agentwars runner request ...

Pairing secrets and key passphrases are accepted only through no-echo prompts.
Provider credentials remain inside the provider's own customer-local client;
this CLI never reads or serializes them.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import sys
import warnings
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent_identity.keys import MIN_PASSPHRASE_CHARACTERS  # noqa: E402
from provider_hub.catalog import PROVIDER_IDS  # noqa: E402
from provider_hub.local_runner import (  # noqa: E402
    MAX_BODY_BYTES,
    PRODUCTION_ORIGIN,
    RunnerClientError,
    claim_runner,
    digest_harness_file,
    grouped_fingerprint,
    parse_pairing_secret,
    send_signed_request,
    sign_runner_request,
)
from provider_hub.runner_state import RunnerStateStore  # noqa: E402
from provider_hub.secrets import SecretValue  # noqa: E402


_PAIRING_SECRET_ARG_RE = re.compile(r"awp1_[A-Za-z0-9_-]{22}_[A-Za-z0-9_-]{32}")
_SECRET_OPTION_NAMES = frozenset(("--pairing-secret", "--passphrase", "--key-passphrase"))
_SECRET_OPTION_STEMS = tuple(option.removeprefix("--") for option in _SECRET_OPTION_NAMES)


def _hidden_prompt(label: str) -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            return getpass.getpass(label)
    except (getpass.GetPassWarning, EOFError) as error:
        raise RunnerClientError("a real interactive no-echo terminal is required") from error


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
        raise argparse.ArgumentTypeError("timeout must be an integer from 1 to 60 seconds") from error
    if not 1 <= timeout <= 60:
        raise argparse.ArgumentTypeError("timeout must be an integer from 1 to 60 seconds")
    return timeout


def _looks_like_secret_option(argument: object) -> bool:
    token = str(argument)
    if not token.startswith("-"):
        return False
    name = token.split("=", 1)[0].lstrip("-").lower().replace("_", "-")
    return len(name) >= 3 and any(stem.startswith(name) for stem in _SECRET_OPTION_STEMS)


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
    print(f"key custody : encrypted local PKCS#8 ({'created' if created else 'reused'})")
    print()
    print("Compare every fingerprint group with the signed-in browser, then confirm there.")
    print("After confirmation, copy the public runner id and record it locally:")
    activate = f"  agentwars runner activate --challenge-id {challenge_id} --runner-id awr1_..."
    if args.state_dir:
        activate += f' --state-dir "{store.root}"'
    print(activate)
    print()
    print("This claim does not attest a provider, plan, billing route, model, runtime, or match.")
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


def _read_request_body(path: str) -> bytes:
    if path == "-":
        raw = sys.stdin.buffer.read(MAX_BODY_BYTES + 1)
    else:
        candidate = Path(path)
        if candidate.is_symlink() or not candidate.is_file():
            raise RunnerClientError("request body path must be one regular non-symlink file")
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
        raise RunnerClientError("response output directory could not be created") from error
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
    if profile["localState"] != "runner_id_recorded_unverified" or profile["runnerId"] is None:
        raise RunnerClientError("record the browser-issued runner id before signing a request")
    passphrase = _existing_key_passphrase()
    key = store.load_key(profile, passphrase.reveal())
    signed = sign_runner_request(
        key,
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
        print("response body not printed; use --response-out with a new path to retain it")
    print("A 2xx response is transport evidence only; the CLI cannot attest server implementation or model execution.")
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
            raise RunnerClientError("an interactive DELETE confirmation or --yes is required") from error
        if answer != "DELETE":
            print("Local key retained.")
            return 1
    removed = store.forget(args.challenge_id)
    print(f"Deleted local encrypted key and profile for {removed['displayLabel']}.")
    print("This local deletion cannot be recovered. Revoke the server runner separately if needed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentwars",
        description="Customer-local AgentWars runner pairing and signed requests.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("runner", help="manage one customer-local signing runner")
    runner_commands = runner.add_subparsers(dest="runner_command", required=True)

    pair = runner_commands.add_parser(
        "pair",
        help="claim a browser-created one-time secret with a new encrypted Ed25519 key",
    )
    pair.add_argument("--provider", choices=PROVIDER_IDS, required=True)
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

    listing = runner_commands.add_parser("list", help="show public local runner metadata")
    listing.add_argument("--state-dir")
    listing.set_defaults(func=cmd_runner_list)

    request = runner_commands.add_parser(
        "request",
        help="send one exact JSON request signed by a recorded runner key",
    )
    request.add_argument("--challenge-id", required=True)
    request.add_argument("--method", choices=("POST", "PUT", "PATCH", "DELETE"), required=True)
    request.add_argument("--path", required=True, help="exact server pathname; query strings are refused")
    request.add_argument("--body-file", required=True, help="exact UTF-8 JSON object bytes, or - for stdin")
    request.add_argument("--response-out", help="new file for the bounded JSON response; never overwritten")
    request.add_argument("--state-dir")
    request.add_argument("--timeout", type=_bounded_timeout, default=15)
    request.set_defaults(func=cmd_runner_request)

    forget = runner_commands.add_parser(
        "forget",
        help="irreversibly delete one local encrypted key and profile",
    )
    forget.add_argument("--challenge-id", required=True)
    forget.add_argument("--state-dir")
    forget.add_argument("--yes", action="store_true", help="skip the DELETE confirmation prompt")
    forget.set_defaults(func=cmd_runner_forget)
    return parser


def main(argv=None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if any(_PAIRING_SECRET_ARG_RE.search(str(argument)) for argument in raw_argv):
        print("ERROR: pairing-secret-shaped argv is forbidden; use the no-echo prompt", file=sys.stderr)
        return 2
    if any(_looks_like_secret_option(argument) for argument in raw_argv):
        print("ERROR: secret and passphrase arguments are forbidden; use the no-echo prompt", file=sys.stderr)
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
            "ERROR: operation cancelled; encrypted local state may already exist. "
            "Inspect `agentwars runner list` before retrying.",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
