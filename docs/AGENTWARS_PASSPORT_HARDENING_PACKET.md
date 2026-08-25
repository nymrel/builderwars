# AgentWars Passport acceptance hardening

Status: bounded implementation packet

Owner: Codex integration lane for Jalen

Ox route: `opencode-go/ox-alpha-free`, MAX effort, no fallback

Base commit: `a739de922b12759d1b3267a92125f2f9d07e116f`

Branch: `codex/agentwars-passport-hardening-20260825`

Claim: `codex-agentwars-passport-hardening-ox-v3-20260825`

[Objective]

Make the signed Agent Passport acceptance checker prove the two properties its current prose claims:

1. signing the same declaration twice with the same key yields the same content-addressed version identity; and
2. every hostile passport fixture is rejected through the controlled `PassportError` contract, while an uncontrolled exception fails the checker.

This is a verification-hardening slice. The production verifier already rejects non-object input with `PassportError`; do not change cryptographic or runtime semantics without stopping for a new claim.

[Scope]

- Ox may inspect the repository broadly and run focused tests.
- Ox may edit only `bin/check_agent_passport.py`.
- This packet, `docs/AGENTWARS_PASSPORT_HARDENING_PACKET.md`, is immutable input and must not be edited by Ox.

[Done when]

- The checker creates a second passport from the exact same logical declaration and key as the stable fixture.
- The checker explicitly requires the second `versionId` to equal the stable `versionId`.
- Changed harness, claimed model, parent, version label, and display name fixtures each remain distinct from the stable identity; diagnostics identify any failing field.
- Hostile fixtures count as controlled rejections only when `verify_passport` raises `PassportError`.
- `AttributeError`, `TypeError`, and every other unexpected exception are recorded separately and make the hostile-input check fail with actionable diagnostics.
- A hostile fixture that is accidentally accepted also makes the check fail and is named.
- No production source, generated verifier, snapshot, schema, dependency, lockfile, Git state, or documentation other than this already-authored packet changes.
- `git diff --check` passes and the lane diff contains only the claimed paths.

[Validation]

Run from the standalone lane root:

- `python bin/check_agent_passport.py`
- `python bin/build_verifier.py --check`
- `python bin/selfcheck.py`
- `python bin/check_fantasy_games.py`
- `python bin/check_agentwars_scale.py`
- `python bin/check_share_bundle.py`
- `python bin/check_agentwars_product.py`
- `git diff --check`
- `git status --short`

The full ladder must pass. Return exact command outcomes and changed paths. Codex will independently inspect and re-run validation.

[Non-goals]

- Do not change `arena/passport.py`, `agent_identity/passport.py`, `verify.py`, public verifier copies, or verifier snapshots.
- Do not change Passport schemas, cryptography, identity claims, replay semantics, provider support, UI, APIs, dependencies, or generated artifacts.
- Do not commit, push, merge, deploy, create or switch branches, stage files, alter remotes, or mutate accounts.
- Do not weaken a test, skip a failure, or convert an uncontrolled exception into an accepted rejection.

[Stop conditions]

- Stop and report if the requested behavior requires a production-code change or any path outside the exact claim.
- Stop and report if the base commit, branch, claim, or standalone-clone custody does not match this packet.
- Stop and report on any claim-scope or Git-custody violation, provider attestation failure, unavailable required dependency, or failing regression that cannot be fixed inside `bin/check_agent_passport.py`.

[Mandatory evidence]

- `bin/check_agent_passport.py`
- `arena/passport.py`
- `docs/AGENTBATTLES_AGENT_PASSPORT.md`
