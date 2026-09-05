# AgentWars source-promotion decision lane

- Claim: `codex-builderwars-agentwars-source-promotion-decision-v2-20260826`
- Branch: `codex/agentwars-launch-integration-20260825`
- Base: `7183940ccf55a04bba1aeb7b8fe4bb927d8ac1ca`
- Writer: Codex (`gpt-5.6-sol`, high)
- Goal thread: `01a02d52-c41a-7521-aee3-e595101d6447`
- Scope: deterministic validation and source-only staging for one separately
  reviewed offline promotion candidate.
- Never: apply a real candidate in this implementation lane; edit the live
  publication manifest or public corpus; regenerate public artifacts; contact a
  provider; mutate an account; commit a reviewer decision; deploy; rank; or
  attest server, reviewer, provider, model, harness, or execution identity.

## Acceptance contract

1. Require one exact external four-file candidate and its full digest.
2. Independently replay and project the candidate transcript with the current
   fixed engine, preserving every false identity/authority boundary.
3. Require the exact clean source head, publication-manifest SHA-256, and
   protected generated-tree digest before any source write.
4. Accept only `approved_for_publication` or `held`, force
   `titleEligible:false`, and stage only the exact transcript plus one
   next-contiguous manifest row.
5. Serialize decisions across repo worktrees; refuse concurrent invocation,
   unrelated dirty state, conflicting identities or bytes, path indirection,
   candidate/projection/count drift, and missing acknowledgements.
6. Prove response-loss idempotency, safe exact-orphan resume, protected-artifact
   non-mutation, and no provider/network dependency in temporary repositories.
7. Keep successful state named `source_decision_staged_not_built`; later source
   commit, generated-artifact rebuild, export, deployment, and public proof stay
   separate gates.

## Ox Alpha Max boundary

The required broker route remains fail-closed at provider-contract preflight
receipt `2a4a4d8e-192d-4d7c-bf27-c5c7b39689cb`. It acquired no seat and sent no
private code. No bypass, fallback, or repeat retry is permitted until the
external provider contract materially changes, so this slice claims no fresh Ox
verdict.

## Acceptance receipt

- Python 3.13.7: `bin/check_publication_source_decision.py` passed 56 checks;
  one candidate-directory symlink check skipped because this Windows host
  denies creating the test symlink.
- Python 3.11.15: the same checker passed the same 56 checks with the same one
  host-capability skip.
- The final integrated `bin/check_provider_hub.py` gate compiled 42 claimed
  Python files and passed every provider, runner, evidence, prepared-match,
  publication, replay-safety, sharing, creator-SDK, product, promotion-candidate,
  and source-decision section in 117.3 seconds.
- Supporting regression receipts remained green: 287 cross-provider cases,
  159 runner cases, 84 evidence cases, 54 source-match cases, 114 prepared-match
  cases, 18 scale matches, 24 matrix receipts, 140 plan-harness cases with two
  expected skips, 45 Passport cases, 17 dependency cases across 43 wheels, 42
  runner-bundle cases, 87 replay-safety cases, 46 creator-SDK cases, 45 build
  verification cases, and 8 approved product capabilities with 3 held for a
  future release.
- Targeted Ruff check and format verification passed for the three new Python
  files. Targeted Bandit found zero medium/high findings and six expected low
  subprocess-import/call notices; Git is resolved to an absolute executable,
  arguments are arrays, and no shell is used.
- Repository-wide Ruff remains a documented pre-existing baseline of 33
  unrelated lint findings and 89 unrelated unformatted files; this lane did not
  bulk-rewrite them.
- Protected-state inspection remained at source head
  `7183940ccf55a04bba1aeb7b8fe4bb927d8ac1ca`, publication-manifest SHA-256
  `d9ce44dbb0c9e8d37865165b91b816ce5c9f456a69116d302a0a6a810970637b`, and
  generated-artifact tree digest
  `f62db7e2054b437dbf1a03a2cd3366abe04e47786a2d22c6afe2cfe0487e9200` with
  10 existing publication entries and no decision lock present.
- All mutation tests used temporary Git repositories. The real publication
  manifest, public match corpus, generated artifacts, provider/network state,
  accounts, rankings, releases, and deployments remained unchanged.
