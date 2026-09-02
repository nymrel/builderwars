# AgentWars launch integration packet

Status: local integration candidate only; not approved for push, merge, deploy,
public execution, or launch.

## Objective

Integrate the frozen provider-transport candidate with the existing signed Agent
Passport, Competition Matrix identity, and launch North Star candidates. Resolve
their shared-file and verifier-artifact conflicts into one locally testable source
line without weakening any truth boundary.

## Immutable inputs

- integration base: `034045472bb9aff976a61c85c8bddaddc62ad093`
- provider code commit: `4710e873f58970b24b48dfbeaab835e06cd3b545`
- Agent Passport range: `336d478d38b1e1ff5e93598fd89237bdf2b1c5e7..f87ed81191736e1f584284d449845e83cc6e8b99`
- Competition Matrix range: `336d478d38b1e1ff5e93598fd89237bdf2b1c5e7..94468a7a1682481efe7d027d1014540f2da2e164`
- North Star commit: `0e3b899bd28a060b988769d63a7bd20e3a224d27`

The provider parent `1742226` is withdrawn; only its superseding descendants in
the integration base are eligible. Passport, Competition Matrix, North Star, and
provider release reviews remain independent gates. Combining them locally does not
convert any pending or blocked verdict into approval.

## Required integration

1. Preserve provider runtime-intent, closed environment, direct OpenCode binary,
   stateless one-retry, and live-evidence truth boundaries from the base.
2. Add signed Agent Passports with harness digest binding, fail-closed crypto and
   replay behavior, lineage/career projection, and standalone verifier parity.
3. Add Competition Matrix v2 launch-spec commitments, primary harness resolution,
   source-label parsing, replay-verified round robins, and public redaction.
4. Add the North Star human/JSON pair without upgrading its hypothesis or launch
   claims.
5. Resolve `README.md`, `publishing/projection.py`, `verify.py`, engine snapshots,
   and any generated public artifacts by preserving the union of contracts. Never
   discard one branch's checks merely to make another pass.
6. Run a signed two-seat provider control only after deterministic integration
   gates pass. Keys and private material must remain ephemeral and outside the
   repository. The resulting identity may be `verified_signed`; model, provider,
   runtime, person, and execution attestation must remain false unless separately
   proven.
7. Keep rivalry surfaces `unplayed_challenge` by default. The sole local upgrade
   path is `agentbattles.runback-surface-admission.v1`: independently replay both
   exact transcripts, reconstruct one accepted lineage edge, require stored
   acceptance byte equality, and bind product/share projections to the same
   admission digest. External lineage-state compare-and-swap remains mandatory
   and outside the compiler.

## Validation floor

- `python bin/check_provider_hub.py`
- `python bin/check_agentwars_runner.py`
- `python bin/check_agent_passport.py`
- `python bin/check_competition_matrix.py`
- `python bin/build_verifier.py --check`
- `python bin/selfcheck.py`
- `python bin/check_fantasy_games.py`
- `python bin/check_agentwars_scale.py`
- `python bin/check_mobile_arena_exchange.py`
- `python -B bin/check_runback_lineage.py`
- `python -B bin/check_runback_surface_admission.py`
- `python bin/check_share_bundle.py`
- `python bin/check_agentwars_product.py`
- `python bin/check_ten_fronts.py`
- targeted `py_compile` for integrated Python modules
- `git diff --check`
- clean committed worktree before any live control

## Done when

- all four immutable input lines are present in one ancestry;
- every conflict has an explicit union-preserving resolution;
- all deterministic validation passes on the exact integration tip;
- current and historical verifier snapshots remain usable without silent identity
  downgrade;
- no private key, credential, raw model output, auth file, absolute public path, or
  environment value is added;
- a local evidence packet names remaining review and isolation gates precisely;
- any live signed provider transcript replay-verifies while keeping model and
  execution identity unattested.

## Non-goals

- No push, merge to `main`, deploy, publication, account action, provider login,
  hosted secret custody, billing change, DNS, outreach, or public arbitrary code.
- No claim that a signed harness passport proves which provider/model produced a
  move or that sampled bytes stayed unchanged throughout execution.
- No deletion or rewriting of historical transcripts to force current-engine
  parity.
- No weakening of duplicate-key rejection, redaction, replay, environment, path,
  runtime-intent, or sandbox truth.

## Stop conditions

Stop on an overlapping write claim, unexpected source outside the claimed paths,
unresolved generated-artifact divergence, missing crypto dependency that would
require an unapproved dependency change, any credential/private-key appearance,
or a failing gate that can only be hidden by dropping a contract. Preserve the
exact conflict and failing command as evidence.
