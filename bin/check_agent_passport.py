#!/usr/bin/env python3
"""Deterministic, offline acceptance checker for the signed Agent Passport.

Eleven adversarial sections. Every check states what would happen if its guard
were absent. Exit 0 only when every attack is caught and every honest path
verifies. No network, no accounts, no persisted keys: every private key in this
suite is ephemeral and lives in a temp directory that is deleted on exit.

    python bin/check_agent_passport.py
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent_identity import (  # noqa: E402
    PROOF_SCOPE,
    KeyMaterialError,
    LineageError,
    PassportError,
    dumps,
    generate_private_key,
    lineage_edge,
    loads,
    save_private_key_encrypted,
    save_private_key_unencrypted,
    sign_passport,
    verify_passport,
)
import agent_identity as identity_contract  # noqa: E402
from arena import passport as arena_passport  # noqa: E402
from arena.canonical import GENESIS, chain  # noqa: E402
from arena.integrity import file_digest, script_digest  # noqa: E402
from arena.match import match_id_for, run_match  # noqa: E402
from arena.replay import verify  # noqa: E402
from entrants.backends import execution_claim_for_backend  # noqa: E402

RESULTS = []


def check(name, ok, expect_if_absent, detail=""):
    RESULTS.append((name, bool(ok), expect_if_absent))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def harness_sha(cmd):
    resolved = script_digest(cmd)
    if not isinstance(resolved, dict):
        raise AssertionError("checker fixture cmd must resolve to a real script file")
    return resolved["sha256"]


def make_entrant(script_name, display_seat_name, passport_path=None):
    cmd = [sys.executable, os.path.join(ROOT, "entrants", script_name), "--backend", "stub:v1"]
    entrant = {
        "name": display_seat_name,
        "cmd": cmd,
        "env": [],
        "claimed_model": "stub:v1",
        "execution_claim": execution_claim_for_backend("stub:v1"),
    }
    if passport_path is not None:
        entrant["agent_passport"] = passport_path
    return entrant


def write_passport(directory, filename, key, **kwargs):
    sha = kwargs.pop("harness_sha256")
    passport = sign_passport(key, harness_sha256=sha, **kwargs)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dumps(passport))
    return path, passport


def rechain(path, mutate):
    """Repair the hash chain after editing records: the capable attacker."""
    with open(path, "r", encoding="utf-8") as fh:
        records = [json.loads(line) for line in fh if line.strip()]
    mutate(records)
    prev = GENESIS
    out = []
    for i, record in enumerate(records):
        body = {"kind": record["kind"], "seq": i, "body": record["body"]}
        h = chain(prev, body)
        line = dict(body)
        line["prev"] = prev
        line["hash"] = h
        out.append(line)
        prev = h
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for line in out:
            fh.write(json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n")


def verify_without_crypto(work, transcript_path):
    """Run replay with an import blocker ahead of site-packages."""
    blocker = os.path.join(work, "blocked-dependency")
    package = os.path.join(blocker, "cryptography")
    os.makedirs(package, exist_ok=True)
    with open(os.path.join(package, "__init__.py"), "w", encoding="utf-8") as fh:
        fh.write("raise ImportError('blocked by Agent Passport acceptance test')\n")
    env = dict(os.environ)
    inherited = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (blocker, ROOT, inherited) if part
    )
    code = (
        "import json,sys; from arena.replay import verify; "
        "print(json.dumps(verify(sys.argv[1]), sort_keys=True))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code, transcript_path],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = {}
    return proc, report


def standalone_verify(transcript_path):
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "verify.py"), transcript_path, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = {}
    return proc, report


def main():
    work = tempfile.mkdtemp(prefix="agentbattles-passport-check-")
    try:
        key_a = generate_private_key()
        key_b = generate_private_key()
        solver_cmd = [sys.executable, os.path.join(ROOT, "entrants", "solver_harness.py"), "--backend", "stub:v1"]
        real_harness = harness_sha(solver_cmd)
        fake_harness = "ab" * 32

        print("\n=== 1. key creation, signing, deterministic serialization, offline verification ===")
        solver_script = solver_cmd[1]
        resolved_harness = script_digest(solver_cmd)
        check("interpreter-first commands bind the entrant script, not python.exe",
              resolved_harness == {
                  "path": os.path.basename(solver_script),
                  "sha256": file_digest(solver_script),
              }
              and resolved_harness["sha256"] != file_digest(sys.executable),
              "a signed passport could cover the interpreter while leaving the harness unbound")
        check("ambiguous interpreter commands never back-scan a later script token",
              script_digest([sys.executable, "-c", "print('not the harness')", solver_script]) is None,
              "a misleading later path could be selected as the signed harness")
        key_dir = os.path.join(work, "keys")
        encrypted = os.path.join(key_dir, "a.key.pem")
        save_private_key_encrypted(encrypted, key_a, b"correct horse battery")
        reloaded_ok = True
        try:
            from agent_identity import load_private_key_file, private_to_public_raw

            same = private_to_public_raw(load_private_key_file(encrypted, b"correct horse battery"))
            reloaded_ok = same == private_to_public_raw(key_a)
            wrong_rejected = False
            try:
                load_private_key_file(encrypted, b"wrong")
            except KeyMaterialError:
                wrong_rejected = True
        except Exception:
            reloaded_ok = False
        check("encrypted PKCS#8 round-trips; wrong passphrase refused",
              reloaded_ok and wrong_rejected,
              "keys would be unusable after storage, or a wrong passphrase would pass")

        p1 = sign_passport(key_a, display_name="Alpha", version_label="v1",
                           harness_sha256=real_harness, claimed_model="stub:v1")
        p1_again = sign_passport(key_a, display_name="Alpha", version_label="v1",
                                 harness_sha256=real_harness, claimed_model="stub:v1")
        text_a = dumps(p1)
        text_b = dumps(sign_passport(key_a, display_name="Alpha", version_label="v1",
                                     harness_sha256=real_harness, claimed_model="stub:v1"))
        check("same content signs to byte-identical passports (no wall clock in IDs)",
              text_a == text_b and p1["versionId"] == p1_again["versionId"],
              "identical declarations could fork into different versions")
        normalized = verify_passport(json.loads(text_a))
        check("offline verification passes on an honest passport",
              normalized["claimedModel"] == "stub:v1"
              and normalized["proofScope"]["modelAttested"] is False,
              "the core property — a verifiable signed declaration — would not hold")
        arena_sources = []
        for directory, _dirs, files in os.walk(os.path.join(ROOT, "arena")):
            for filename in files:
                if filename.endswith(".py"):
                    with open(os.path.join(directory, filename), encoding="utf-8") as fh:
                        arena_sources.append(fh.read())
        check("public identity API re-exports the exact in-engine verifier objects",
              identity_contract.verify_passport is arena_passport.verify_passport
              and identity_contract.PassportError is arena_passport.PassportError,
              "the product API and digest-bound referee could drift into two verifiers")
        check("arena has no reverse dependency on the external agent_identity package",
              all("agent_identity" not in source for source in arena_sources),
              "the standalone verifier could require files outside its engine digest")
        unsafe_path = os.path.join(key_dir, "agent.unsafe-test-only.key.pem")
        save_private_key_unencrypted(unsafe_path, key_b)
        check("unsafe unencrypted key helper writes only the explicitly named test-only file",
              os.path.exists(unsafe_path) and not os.path.exists(os.path.join(key_dir, "b.unsafe-test-only.key.pem")),
              "automation without a TTY would have no escape hatch, or it would leak into defaults")
        cli_dir = os.path.join(work, "cli-e2e")
        cli_key = os.path.join(cli_dir, "cli-agent.unsafe-test-only.key.pem")
        cli_passport = os.path.join(cli_dir, "cli-v1.agent.json")
        cli = os.path.join(ROOT, "bin", "create_agent_passport.py")
        cli_runs = [
            subprocess.run(
                [sys.executable, cli, "create-key", "--out-dir", cli_dir,
                 "--name", "cli-agent", "--insecure-unencrypted-key"],
                capture_output=True, text=True, timeout=30,
            ),
            subprocess.run(
                [sys.executable, cli, "create-version", "--key", cli_key,
                 "--key-is-unencrypted", "--display-name", "CLI Agent",
                 "--version-label", "v1", "--harness-file",
                 os.path.join(ROOT, "entrants", "solver_harness.py"),
                 "--claimed-model", "stub:v1", "--out", cli_passport],
                capture_output=True, text=True, timeout=30,
            ),
        ]
        cli_runs.append(subprocess.run(
            [sys.executable, cli, "verify", cli_passport],
            capture_output=True, text=True, timeout=30,
        ))
        check("CLI creates, signs, and independently verifies one bounded test passport",
              all(run.returncode == 0 for run in cli_runs)
              and os.path.exists(cli_key)
              and os.path.exists(cli_passport)
              and "signature : PASS" in cli_runs[-1].stdout,
              "the documented entrant onboarding path could fail despite lower-level APIs passing",
              "; ".join(run.stderr.strip()[:80] for run in cli_runs if run.stderr.strip()))

        print("\n=== 2. version identity: same content -> same id; changed field -> different id ===")
        stable = p1["versionId"]
        check("same declaration and key reproduce the same version address",
              p1_again["versionId"] == stable,
              "identical declarations could fork into different version identities",
              f"first={stable}; repeated={p1_again['versionId']}")
        changed = {}
        variants = [
            ("harness", dict(display_name="Alpha", version_label="v1", harness_sha256=fake_harness)),
            ("model", dict(display_name="Alpha", version_label="v1", harness_sha256=real_harness, claimed_model="stub:v2")),
            ("parent", dict(display_name="Alpha", version_label="v1", harness_sha256=real_harness, parent_version_id=stable)),
            ("label", dict(display_name="Alpha", version_label="v2", harness_sha256=real_harness)),
            ("name", dict(display_name="Alpha Two", version_label="v1", harness_sha256=real_harness)),
        ]
        for label, kw in variants:
            other = sign_passport(key_a, **kw)
            changed[label] = other["versionId"] != stable
        unchanged = sorted(label for label, differs in changed.items() if not differs)
        check("changed harness/model/parent/label/name each produce a new version address",
              all(changed.values()),
              "silent mutation of ranked history would look like training",
              "all changed fields produced distinct addresses" if not unchanged
              else f"unchanged addresses: {', '.join(unchanged)}")

        print("\n=== 3. adversarial passports are rejected (wrong key, mutation, encodings, bounds) ===")
        controlled_rejects = []
        accepted = []
        fixture_errors = []
        uncontrolled_errors = []
        expect_reject = [
            ("wrong key", lambda: dict(p1, publicKey=base64.b64encode(
                bytes(range(32))).decode())),
            ("signature mutation", lambda: dict(p1, signature=(
                "A" + p1["signature"][1:] if p1["signature"][0] != "A" else "B" + p1["signature"][1:]))),
            ("malformed base64", lambda: dict(p1, signature="not+valid/base64!!")),
            ("short signature", lambda: dict(p1, signature=base64.b64encode(b"\x00" * 63).decode())),
            ("extra key", lambda: {**p1, "extra": 1}),
            ("missing key", lambda: {k: v for k, v in p1.items() if k != "claimedModel"}),
            ("bad agentId", lambda: dict(p1, agentId="ff" * 32)),
            ("uppercase digest", lambda: dict(p1, harnessSha256=real_harness.upper())),
            ("oversized displayName", lambda: dict(p1, displayName="x" * 65)),
            ("oversized versionLabel", lambda: dict(p1, versionLabel="x" * 81)),
            ("oversized claimedModel", lambda: dict(p1, claimedModel="x" * 121)),
            ("non-NFC name", lambda: dict(p1, displayName="A\u0301lpha")),
            ("tampered proofScope", lambda: dict(p1, proofScope=dict(PROOF_SCOPE, modelAttested=True))),
            ("bad parent reference", lambda: dict(p1, parentVersionId="zz" * 32)),
            ("wrong schema", lambda: dict(p1, schema="agentbattles.agent-version.v2")),
            ("non-object", lambda: ["not", "an", "object"]),
        ]
        for label, build in expect_reject:
            try:
                hostile = build()
            except Exception as error:
                fixture_errors.append(f"{label}:{type(error).__name__}")
                continue
            try:
                verify_passport(hostile)
            except PassportError:
                controlled_rejects.append(label)
            except Exception as error:
                uncontrolled_errors.append(f"{label}:{type(error).__name__}")
            else:
                accepted.append(label)
        hostile_contract_ok = (
            len(controlled_rejects) == len(expect_reject)
            and not accepted
            and not fixture_errors
            and not uncontrolled_errors
        )
        hostile_detail = (
            f"controlled: {', '.join(controlled_rejects)}; "
            f"accepted: {', '.join(accepted) or 'none'}; "
            f"fixture errors: {', '.join(fixture_errors) or 'none'}; "
            f"uncontrolled errors: {', '.join(uncontrolled_errors) or 'none'}"
        )
        check(f"{len(expect_reject)} hostile passport shapes fail closed through PassportError",
              hostile_contract_ok,
              "an attacker could impersonate an agent or smuggle unbounded fields into IDs",
              hostile_detail)
        loads_rejects = False
        try:
            loads("{not json")
        except PassportError:
            loads_rejects = True
        check("passport JSON loader refuses malformed text", loads_rejects,
              "a crash instead of a refusal is denial-of-verification")
        duplicate_keys_rejected = False
        try:
            loads('{"schema":"first","schema":"second"}')
        except PassportError:
            duplicate_keys_rejected = True
        check("passport JSON loader refuses duplicate object keys", duplicate_keys_rejected,
              "different JSON parsers could verify different declarations from one file")

        print("\n=== 4. passport/harness mismatch is refused before any entrant starts ===")
        mismatch_dir = os.path.join(work, "mismatch")
        _, bad_binding = write_passport(
            work, "bad-binding.json", key_a,
            display_name="Alpha", version_label="v1", harness_sha256=fake_harness,
        )
        bad_path = os.path.join(work, "bad-binding.json")
        refused = None
        try:
            run_match(game_name="nim", seed=7,
                      entrants=[make_entrant("solver_harness.py", "Alpha", bad_path),
                                make_entrant("naive_harness.py", "Naive")],
                      out_dir=mismatch_dir)
        except ValueError as e:
            refused = str(e)
        check("mismatched harnessSha256 fails before play",
              refused is not None and "harnessSha256" in refused,
              "an entrant could play under a harness its own signature does not cover")
        check("refusal leaves no transcript, output dir, or started processes",
              not os.path.exists(mismatch_dir),
              "a half-started match would leave records that never happened")
        invalid_dir = os.path.join(work, "invalid-passport")
        tampered_path = os.path.join(work, "tampered.json")
        tampered_record = dict(json.loads(text_a), displayName="Mallory")
        with open(tampered_path, "w", encoding="utf-8") as fh:
            json.dump(tampered_record, fh)
        refused_invalid = None
        try:
            run_match(game_name="nim", seed=7,
                      entrants=[make_entrant("solver_harness.py", "Alpha", tampered_path),
                                make_entrant("naive_harness.py", "Naive")],
                      out_dir=invalid_dir)
        except ValueError as e:
            refused_invalid = str(e)
        check("an unverifiable passport file is refused before play",
              refused_invalid is not None and "invalid entrant passport" in refused_invalid,
              "invalid identity evidence could reach the transcript at all")

        conflicting_path, _ = write_passport(
            work, "conflicting-claim.json", key_a,
            display_name="Alpha", version_label="v1", harness_sha256=real_harness,
            claimed_model="different:model",
        )
        conflict_refused = False
        try:
            run_match(game_name="nim", seed=7,
                      entrants=[make_entrant("solver_harness.py", "Alpha", conflicting_path),
                                make_entrant("naive_harness.py", "Naive")],
                      out_dir=os.path.join(work, "conflicting-claim"))
        except ValueError as error:
            conflict_refused = "claimedModel" in str(error)
        check("signed and manifest model self-declarations cannot contradict", conflict_refused,
              "one receipt could present two incompatible model claims for one seat")

        print("\n=== 5. version-aware automatic match ids; legacy ids untouched ===")
        v1_path, v1 = write_passport(work, "alpha-v1.json", key_a,
                                     display_name="Alpha", version_label="v1",
                                     harness_sha256=real_harness, claimed_model="stub:v1")
        v2_path, v2 = write_passport(work, "alpha-v2.json", key_a,
                                     display_name="Alpha", version_label="v2",
                                     harness_sha256=real_harness, claimed_model="stub:v1",
                                     parent_version_id=v1["versionId"])
        names = ("Alpha", "Naive")
        legacy_id = match_id_for("nim", 42, list(names))
        seat_alpha_v1 = make_entrant("solver_harness.py", "Alpha", v1_path)
        seat_naive = make_entrant("naive_harness.py", "Naive")
        m_v1 = run_match(game_name="nim", seed=42, entrants=[seat_alpha_v1, seat_naive],
                         out_dir=os.path.join(work, "id-v1"))
        m_v2 = run_match(game_name="nim", seed=42,
                         entrants=[dict(seat_alpha_v1, agent_passport=v2_path), seat_naive],
                         out_dir=os.path.join(work, "id-v2"))
        check("two versions of the same agent under same game/seed/names get different automatic ids",
              m_v1["match_id"] != m_v2["match_id"],
              "a republished version would overwrite the previous record's address")
        explicit = run_match(game_name="nim", seed=42, entrants=[dict(seat_alpha_v1, agent_passport=v2_path), seat_naive],
                             out_dir=os.path.join(work, "id-explicit"), match_id="Explicit_Callers_Retain_Control")
        check("explicit caller-supplied match ids keep current behavior",
              explicit["match_id"] == "Explicit_Callers_Retain_Control",
              "fixture tooling depending on explicit ids would break")

        print("\n=== 6. a valid passport match replay-verifies AND identity-verifies ===")
        r_v1 = verify(m_v1["transcript"])
        seats = r_v1.get("identity_seats", [])
        seats_verified = (
            len(seats) == 2
            and seats[0].get("identityStatus") == "verified_signed"
            and seats[1].get("identityStatus") == "self_declared_legacy"
        )
        check("replay PASS labels mixed signed and legacy seats exactly",
              r_v1["verdict"] == "PASS"
              and r_v1["identity_status"] == "mixed_verified_and_legacy"
              and seats_verified,
              "signed matches would be indistinguishable from unsigned ones")
        scope_false = all(
            r_v1["identity"][field] is False
            for field in ("modelAttested", "runtimeAttested", "personAttested", "executionClaimsAttested")
        )
        check("identity report keeps model/runtime/person/execution attestation false",
              scope_false,
              "signature proof would silently inflate into attestation it cannot provide")

        naive_cmd = [sys.executable, os.path.join(ROOT, "entrants", "naive_harness.py"), "--backend", "stub:v1"]
        naive_harness = harness_sha(naive_cmd)
        naive_path, _naive = write_passport(
            work, "naive-v1.json", key_b,
            display_name="Naive", version_label="v1",
            harness_sha256=naive_harness, claimed_model="stub:v1",
        )
        m_signed = run_match(
            game_name="nim", seed=45,
            entrants=[seat_alpha_v1, make_entrant("naive_harness.py", "Naive", naive_path)],
            out_dir=os.path.join(work, "both-signed"),
        )
        r_signed = verify(m_signed["transcript"])
        check("two independently keyed signed seats produce verified_signed replay identity",
              r_signed["verdict"] == "PASS"
              and r_signed["identity_status"] == "verified_signed"
              and all(row.get("identityStatus") == "verified_signed"
                      for row in r_signed.get("identity_seats", [])),
              "the ranked all-signed trust tier would have no honest success path")

        same_key_naive_path, _ = write_passport(
            work, "naive-same-key.json", key_a,
            display_name="Naive", version_label="same-owner-test",
            harness_sha256=naive_harness, claimed_model="stub:v1",
        )
        same_agent_refused = False
        try:
            run_match(
                game_name="nim", seed=46,
                entrants=[seat_alpha_v1,
                          make_entrant("naive_harness.py", "Naive", same_key_naive_path)],
                out_dir=os.path.join(work, "same-agent-both-seats"),
            )
        except ValueError as error:
            same_agent_refused = "same signed agentId" in str(error)
        check("one signed agentId cannot occupy both seats",
              same_agent_refused,
              "one owner could manufacture ranked wins against itself")

        blocked_proc, blocked_report = verify_without_crypto(work, m_signed["transcript"])
        check("signed replay without cryptography fails closed as dependency_missing",
              blocked_proc.returncode == 0
              and blocked_report.get("verdict") == "FAIL"
              and blocked_report.get("identity_status") == "invalid"
              and "dependency_missing" in blocked_report.get("identity", {}).get("errorCodes", []),
              "a verifier missing crypto could silently downgrade signed identity to legacy",
              blocked_proc.stderr.strip()[:180])

        standalone_proc, standalone_report = standalone_verify(m_signed["transcript"])
        check("current standalone verifier embeds passport.py and passes a signed receipt",
              standalone_proc.returncode == 0
              and standalone_report.get("effective_verdict") == "PASS"
              and standalone_report.get("signed_passport_present") is True
              and standalone_report.get("signed_verifier_capable") is True
              and standalone_report.get("verifier_snapshot_match") is True,
              "the shareable verifier would advertise a signature it cannot verify",
              standalone_proc.stderr.strip()[:180])

        print("\n=== 7. repaired chain + tampered passport evidence still fails identity ===")
        forged = os.path.join(work, "forged.jsonl")
        shutil.copy(m_v1["transcript"], forged)

        def tamper_identity(records):
            for rec in records:
                if rec["kind"] == "header":
                    rec["body"]["entrants"][0]["agent_passport"]["displayName"] = "Mallory"

        rechain(forged, tamper_identity)
        r_forged = verify(forged)
        check("re-chained forgery with edited passport FAILS replay",
              r_forged["verdict"] == "FAIL" and r_forged["identity_status"] == "invalid"
              and r_forged["chain_ok"] is True,
              "an attacker who can repair the ordinary chain could rewrite who played")
        swapped_key = os.path.join(work, "forged-key.jsonl")
        shutil.copy(m_v1["transcript"], swapped_key)
        other_public = base64.b64encode(bytes(range(32))).decode()

        def swap_key(records):
            for rec in records:
                if rec["kind"] == "header":
                    rec["body"]["entrants"][0]["agent_passport"]["publicKey"] = other_public

        rechain(swapped_key, swap_key)
        r_key = verify(swapped_key)
        check("swapped public key inside repaired evidence fails identity too",
              r_key["verdict"] == "FAIL" and r_key["identity_status"] == "invalid",
              "identity could be laundered by swapping the key the ID claims to derive from")

        duplicate_transcript = os.path.join(work, "duplicate-key.jsonl")
        with open(m_signed["transcript"], "r", encoding="utf-8") as fh:
            duplicate_lines = fh.readlines()
        duplicate_lines[0] = duplicate_lines[0].replace(
            '"kind":"header"', '"kind":"header","kind":"header"', 1
        )
        with open(duplicate_transcript, "w", encoding="utf-8", newline="\n") as fh:
            fh.writelines(duplicate_lines)
        duplicate_report = verify(duplicate_transcript)
        duplicate_standalone_proc, duplicate_standalone = standalone_verify(duplicate_transcript)
        check("duplicate transcript object keys fail package and standalone verification",
              duplicate_report.get("verdict") == "FAIL"
              and any("duplicate object key" in error for error in duplicate_report.get("errors", []))
              and duplicate_standalone_proc.returncode == 1
              and duplicate_standalone.get("effective_verdict") == "FAIL"
              and "duplicate object key" in str(duplicate_standalone.get("transcript_preflight_error")),
              "different JSON parsers could interpret one hash-valid receipt differently")

        legacy_snapshot_digest = None
        snapshot_dir = os.path.join(ROOT, "bin", "verifier_snapshots")
        for filename in sorted(os.listdir(snapshot_dir)):
            if not filename.endswith(".json"):
                continue
            with open(os.path.join(snapshot_dir, filename), "r", encoding="utf-8") as fh:
                snapshot = json.load(fh)
            if "passport.py" not in snapshot.get("sources", {}):
                legacy_snapshot_digest = snapshot.get("engineDigest")
                break
        downgraded = os.path.join(work, "signed-old-engine.jsonl")
        shutil.copy(m_signed["transcript"], downgraded)

        def select_legacy_snapshot(records):
            for rec in records:
                if rec["kind"] == "header":
                    rec["body"]["engine"]["digest"] = legacy_snapshot_digest

        if legacy_snapshot_digest:
            rechain(downgraded, select_legacy_snapshot)
            downgrade_proc, downgrade_report = standalone_verify(downgraded)
        else:
            downgrade_proc, downgrade_report = None, {}
        check("signed receipt cannot downgrade through a pre-passport engine snapshot",
              downgrade_proc is not None
              and downgrade_proc.returncode == 1
              and downgrade_report.get("effective_verdict") == "FAIL"
              and downgrade_report.get("signed_passport_present") is True
              and downgrade_report.get("signed_verifier_capable") is False
              and any("unsupported_verifier_for_signed" in error
                      for error in downgrade_report.get("effective_errors", [])),
              "a signed block could be ignored by a historical legacy verifier")

        print("\n=== 8. legacy unsigned matches still PASS with unchanged automatic ids ===")
        m_legacy = run_match(game_name="nim", seed=42,
                             entrants=[make_entrant("solver_harness.py", "Alpha"),
                                       make_entrant("naive_harness.py", "Naive")],
                             out_dir=os.path.join(work, "legacy"))
        r_legacy = verify(m_legacy["transcript"])
        check("legacy replay PASS with identity_status='self_declared_legacy'",
              r_legacy["verdict"] == "PASS" and r_legacy["identity_status"] == "self_declared_legacy",
              "existing receipts and fixtures would stop verifying")
        check("legacy automatic match id equals the historical formula exactly",
              m_legacy["match_id"] == legacy_id,
              "every recorded match address would change")
        legacy_blocked_proc, legacy_blocked_report = verify_without_crypto(work, m_legacy["transcript"])
        check("unsigned legacy replay remains stdlib-only when cryptography is unavailable",
              legacy_blocked_proc.returncode == 0
              and legacy_blocked_report.get("verdict") == "PASS"
              and legacy_blocked_report.get("identity_status") == "self_declared_legacy",
              "an optional signed feature would strand historical unsigned receipts",
              legacy_blocked_proc.stderr.strip()[:180])

        print("\n=== 9. public projection prefers verified stable ids; legacy keeps name hashes ===")
        from publishing.projection import PublicationError, public_entrants, _entrant_id

        with open(m_v1["transcript"], "r", encoding="utf-8") as fh:
            header_signed = json.loads(fh.readline())["body"]
        rows_signed = public_entrants(header_signed)
        alpha_row = next(row for row in rows_signed if row["name"] == "Alpha")
        check("passport entrant projects under key-derived agentId with version + status + proof scope",
              alpha_row["entrantId"] == v1["agentId"]
              and alpha_row["agentVersionId"] == v1["versionId"]
              and alpha_row["identityStatus"] == "verified_signed"
              and alpha_row["proofScope"]["modelAttested"] is False
              and alpha_row["claimedModelSelfDeclared"] == "stub:v1",
              "display-name identity would leak back into public artifacts")
        naive_row = next(row for row in rows_signed if row["name"] == "Naive")
        check("legacy seat in a mixed match keeps the name-hash identity shape",
              naive_row["entrantId"] == _entrant_id("Naive")
              and "agentVersionId" not in naive_row
              and "identityStatus" not in naive_row,
              "legacy entrant rows would gain fields consumers never agreed to")
        null_passport_header = json.loads(json.dumps(header_signed))
        null_passport_header["entrants"][0]["agent_passport"] = None
        null_projection_refused = False
        try:
            public_entrants(null_passport_header)
        except PublicationError:
            null_projection_refused = True
        check("present-but-null passport evidence cannot project as a legacy entrant",
              null_projection_refused,
              "invalid signed evidence could cross the public boundary as unsigned")
        with open(m_legacy["transcript"], "r", encoding="utf-8") as fh:
            header_legacy = json.loads(fh.readline())["body"]
        rows_legacy = public_entrants(header_legacy)
        check("legacy projection is byte-for-byte the existing receipt shape",
              [row["entrantId"] for row in rows_legacy] == [_entrant_id(n) for n in names]
              and all("identityStatus" not in row for row in rows_legacy),
              "every previously published receipt digest would change")

        print("\n=== 10. career: deterministic, version-separated, lineage-aware, refuse-invalid ===")
        from publishing.career import CareerError, build_career

        m_v2_repeat = run_match(game_name="nim", seed=43,
                                entrants=[dict(seat_alpha_v1, agent_passport=v2_path), seat_naive],
                                out_dir=os.path.join(work, "career-v2b"))
        corpus = [m_v1["transcript"], m_v2["transcript"], m_v2_repeat["transcript"]]
        doc_one = build_career(corpus)
        doc_two = build_career(corpus)
        basis = doc_one["basis"]
        versions_by_label = {row["versionLabel"]: row for row in basis["versions"]}
        check("career output is deterministic across builds",
              json.dumps(doc_one, sort_keys=True) == json.dumps(doc_two, sort_keys=True)
              and doc_one["basisDigest"] == doc_two["basisDigest"],
              "career comparisons would depend on dict ordering")
        check("versions stay separate lines with per-version counts and opponents",
              set(versions_by_label) == {"v1", "v2"}
              and versions_by_label["v1"]["games"] == 1
              and versions_by_label["v2"]["games"] == 2
              and all(row["opponents"] for row in versions_by_label.values()),
              "training comparisons across versions would blur into one opaque number")
        check("lineage edge accepted within one key and reported",
              basis["lineageEdges"] == [{"parentVersionId": v1["versionId"],
                                         "childVersionId": v2["versionId"],
                                         "agentId": v1["agentId"]}],
              "version history could not be audited against the signing key")
        edge_refused = False
        try:
            child_wrong_key = sign_passport(key_b, display_name="Alpha", version_label="impostor",
                                            harness_sha256=real_harness, claimed_model="stub:v1",
                                            parent_version_id=v1["versionId"])
            lineage_edge(v1, child_wrong_key)
        except LineageError:
            edge_refused = True
        check("cross-key parent lineage refused", edge_refused,
              "an impostor key could claim another agent's history")
        career_cross = False
        v3_impostor_path, _ = write_passport(work, "impostor-v3.json", key_b,
                                             display_name="Alpha", version_label="v3-impostor",
                                             harness_sha256=real_harness, claimed_model="stub:v1",
                                             parent_version_id=v2["versionId"])
        try:
            build_career([m_v2["transcript"],
                          run_match(game_name="nim", seed=44,
                                    entrants=[dict(seat_alpha_v1, agent_passport=v3_impostor_path), seat_naive],
                                    out_dir=os.path.join(work, "career-cross"))["transcript"]])
        except CareerError:
            career_cross = True
        check("career refuses a corpus whose declared lineage crosses keys", career_cross,
              "a forged family tree would aggregate under the victim's agentId")
        duplicate_receipt_refused = False
        try:
            build_career([m_v1["transcript"], m_v1["transcript"]])
        except CareerError:
            duplicate_receipt_refused = True
        check("career refuses duplicate receipts", duplicate_receipt_refused,
              "one verified win could be counted repeatedly to fabricate a record")
        tampered_copy = os.path.join(work, "career-tampered.jsonl")
        shutil.copy(m_v1["transcript"], tampered_copy)
        with open(tampered_copy, "r", encoding="utf-8") as fh:
            tlines = fh.readlines()
        t0 = json.loads(tlines[0])
        t0["body"]["seed"] += 1
        tlines[0] = json.dumps(t0, sort_keys=True, separators=(",", ":")) + "\n"
        with open(tampered_copy, "w", encoding="utf-8", newline="\n") as fh:
            fh.writelines(tlines)
        career_invalid = False
        try:
            build_career([tampered_copy])
        except CareerError:
            career_invalid = True
        check("career refuses any transcript that fails replay verification", career_invalid,
              "losses could be laundered out of a career by feeding it broken transcripts")

        print("\n=== 11. no private key material anywhere it must not be ===")
        with open(unsafe_path, "rb") as fh:
            unsafe_pem = fh.read()
        secret_markers = {
            "pem-body-chunk": unsafe_pem.split(b"\n")[1][:44],
            "full-pem-prefix": b"-----BEGIN " + b"PRIVATE KEY-----",
        }
        outputs = []
        for dirpath, _dirs, files in os.walk(work):
            for name in files:
                if name.endswith((".jsonl", ".json", ".diagnostics.jsonl")):
                    outputs.append(os.path.join(dirpath, name))
        leaked = []
        for path in outputs:
            blob = open(path, "rb").read()
            for label, marker in secret_markers.items():
                if marker and marker in blob:
                    leaked.append((os.path.basename(path), label))
        repo_blob = b""
        git_ls = subprocess.run(
            ["git", "-C", ROOT, "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
        tracked = [p for p in git_ls.split("\0") if p.endswith((".py", ".md", ".json", ".txt"))]
        for rel in tracked:
            full = os.path.join(ROOT, rel)
            try:
                repo_blob += open(full, "rb").read()
            except OSError:
                pass
        repo_leak = any(marker and marker in repo_blob for marker in secret_markers.values())
        check("no key material in any transcript, passport, career output, or repo file",
              not leaked and not repo_leak,
              "the identity system would publish the very secret it exists to protect",
              f"leaked: {leaked or 'none'}; repo leak: {repo_leak}")

    finally:
        shutil.rmtree(work, ignore_errors=True)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{'=' * 62}\n{passed}/{total} checks passed")
    if passed != total:
        print("\nFAILED:")
        for name, ok, expect in RESULTS:
            if not ok:
                print(f"  - {name}\n      absent-guard consequence: {expect}")
        return 1
    print("every passport guarantee above held under attack.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback

        traceback.print_exc()
        print(f"\n{'=' * 62}\nPASSPORT CHECK CRASHED before reaching a verdict — treat as FAIL.")
        sys.exit(2)
