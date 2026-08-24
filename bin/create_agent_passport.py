#!/usr/bin/env python3
"""Create and verify AgentBattles signed Agent Passports.

    python bin/create_agent_passport.py create-key --out-dir keys/alpha
    python bin/create_agent_passport.py create-version --key keys/alpha/agent.key.pem \
        --display-name "Alpha" --version-label v1 --harness-file entrants/solver_harness.py \
        --out passports/alpha-v1.json
    python bin/create_agent_passport.py verify passports/alpha-v1.json

Private keys are written as encrypted PKCS#8 (passphrase prompted twice, never
accepted from argv, never echoed). Automation may opt into the explicitly named
unsafe test-only unencrypted key file; production use should not.

Nothing this tool prints contains private key material.
"""

import argparse
import getpass
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent_identity import (  # noqa: E402
    KeyMaterialError,
    MIN_PASSPHRASE_CHARACTERS,
    PassportError,
    UNSAFE_KEY_SUFFIX,
    dumps,
    generate_private_key,
    load_private_key_file,
    save_private_key_encrypted,
    save_private_key_unencrypted,
    sign_passport,
    verify_passport_file,
)
from arena.canonical import file_digest  # noqa: E402

_KEY_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _prompt_passphrase(confirm=True):
    first = getpass.getpass(
        f"passphrase for the private key (min {MIN_PASSPHRASE_CHARACTERS} chars): "
    )
    if len(first) < MIN_PASSPHRASE_CHARACTERS:
        raise SystemExit("passphrase too short")
    if not confirm:
        return first.encode("utf-8")
    second = getpass.getpass("repeat passphrase: ")
    if first != second:
        raise SystemExit("passphrases do not match")
    return first.encode("utf-8")


def _refuse_overwrite(path, force):
    if os.path.exists(path) and not force:
        raise SystemExit(f"refusing to overwrite existing file: {path} (pass --overwrite to allow)")


def cmd_create_key(args):
    if _KEY_NAME_RE.fullmatch(args.name) is None:
        raise SystemExit("key --name must be 1-64 ASCII letters, digits, underscores, or hyphens")
    key = generate_private_key()
    os.makedirs(args.out_dir, exist_ok=True)
    if args.insecure_unencrypted_key:
        # Explicit automation escape hatch; clearly named, never the default.
        unsafe_path = os.path.join(args.out_dir, f"{args.name}{UNSAFE_KEY_SUFFIX}")
        _refuse_overwrite(unsafe_path, args.overwrite)
        save_private_key_unencrypted(unsafe_path, key, overwrite=args.overwrite)
        print(f"UNSAFE unencrypted test-only key written: {unsafe_path}")
        print("this file must never leave this machine or be committed")
        return 0
    key_path = os.path.join(args.out_dir, f"{args.name}.key.pem")
    _refuse_overwrite(key_path, args.overwrite)
    try:
        saved = save_private_key_encrypted(
            key_path,
            key,
            _prompt_passphrase(confirm=True),
            overwrite=args.overwrite,
        )
    except KeyMaterialError as e:
        raise SystemExit(str(e))
    print(f"encrypted private key written: {saved}")
    print("the matching public identity is derived when you create a version")
    return 0


def _resolve_harness_sha256(args):
    if args.harness_sha256 and args.harness_file:
        raise SystemExit("use either --harness-sha256 or --harness-file, not both")
    if args.harness_file:
        value = file_digest(args.harness_file)
    elif args.harness_sha256:
        value = args.harness_sha256
    else:
        raise SystemExit(
            "a harness digest is required: --harness-file PATH, or --harness-sha256 "
            "computed exactly like arena.integrity.script_digest does for your cmd"
        )
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise SystemExit("harness sha256 must be exactly 64 lowercase hex characters")
    return value


def cmd_create_version(args):
    _refuse_overwrite(args.out, args.overwrite)
    if args.key_is_unencrypted and not args.key.endswith(UNSAFE_KEY_SUFFIX):
        raise SystemExit(
            f"--key-is-unencrypted requires a key filename ending in {UNSAFE_KEY_SUFFIX}"
        )
    passphrase = None if args.key_is_unencrypted else _prompt_passphrase(confirm=False)
    try:
        key = load_private_key_file(args.key, passphrase)
    except KeyMaterialError as e:
        raise SystemExit(str(e))
    harness_sha256 = _resolve_harness_sha256(args)
    try:
        passport = sign_passport(
            key,
            display_name=args.display_name,
            version_label=args.version_label,
            harness_sha256=harness_sha256,
            claimed_model=args.claimed_model,
            parent_version_id=args.parent_version_id,
        )
        text = dumps(passport)  # refuses to serialize anything invalid
    except PassportError as e:
        raise SystemExit(str(e))
    directory = os.path.dirname(os.path.abspath(args.out))
    if directory:
        os.makedirs(directory, exist_ok=True)
    mode = "w" if args.overwrite else "x"
    with open(args.out, mode, encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"passport written: {args.out}")
    print(f"agentId   : {passport['agentId']}")
    print(f"versionId : {passport['versionId']}")
    if args.parent_version_id:
        print(f"parent    : {args.parent_version_id}")
    return 0


def cmd_verify(args):
    try:
        normalized = verify_passport_file(args.passport)
    except PassportError as e:
        print(f"FAIL: {e}")
        return 1
    checks = []
    if args.expect_agent_id:
        checks.append(("agentId", normalized["agentId"] == args.expect_agent_id))
    if args.expect_version_id:
        checks.append(("versionId", normalized["versionId"] == args.expect_version_id))
    if args.expect_harness_sha256:
        checks.append(("harnessSha256", normalized["harnessSha256"] == args.expect_harness_sha256))
    failed = [name for name, ok in checks if not ok]
    print(f"signature : PASS ({normalized['schema']})")
    print(f"agentId   : {normalized['agentId']}")
    print(f"versionId : {normalized['versionId']}")
    print(f"harness   : {normalized['harnessSha256']}")
    print(f"claimedModel (self-declared): {normalized['claimedModel']}")
    print("proofScope: model/runtime/person/execution attestation all false")
    if failed:
        print(f"FAIL: expected mismatch on {', '.join(failed)}")
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="AgentBattles signed Agent Passport CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    k = sub.add_parser("create-key", help="generate an Ed25519 key (encrypted PKCS#8)")
    k.add_argument("--out-dir", required=True)
    k.add_argument("--name", default="agent")
    k.add_argument("--overwrite", action="store_true")
    k.add_argument(
        "--insecure-unencrypted-key",
        action="store_true",
        help="UNSAFE test-only: write an unencrypted key instead of an encrypted one",
    )
    k.set_defaults(fn=cmd_create_key)

    v = sub.add_parser(
        "create-version", help="sign one tamper-evident, version-addressed declaration"
    )
    v.add_argument("--key", required=True, help="path to the PKCS#8 PEM private key")
    v.add_argument("--display-name", required=True, help="1-64 characters")
    v.add_argument("--version-label", required=True, help="1-80 characters")
    v.add_argument("--harness-file", help="hash this script file with sha256")
    v.add_argument("--harness-sha256", help="exact lowercase sha256 of the harness binding")
    v.add_argument(
        "--claimed-model",
        default=None,
        help="self-declared label; recorded as a claim, never attested",
    )
    v.add_argument(
        "--parent-version-id",
        default=None,
        help="parent versionId for lineage (must be published under the same key)",
    )
    v.add_argument("--out", required=True, help="output passport JSON path")
    v.add_argument("--overwrite", action="store_true")
    v.add_argument(
        "--key-is-unencrypted",
        action="store_true",
        help="declare that --key is the explicit unsafe-test-only file (no passphrase)",
    )
    v.set_defaults(fn=cmd_create_version)

    c = sub.add_parser("verify", help="offline verification of a passport JSON")
    c.add_argument("passport")
    c.add_argument("--expect-agent-id")
    c.add_argument("--expect-version-id")
    c.add_argument("--expect-harness-sha256")
    c.set_defaults(fn=cmd_verify)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
