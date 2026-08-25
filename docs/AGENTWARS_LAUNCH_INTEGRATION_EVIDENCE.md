# AgentWars launch integration evidence

Status: local candidate; deterministic and signed-live controls pass. Independent
review, integration approval, push, deployment, publication, customer access, and
public launch remain open gates.

## Integrated source line

- provider transport and fantasy evidence base: `034045472bb9aff976a61c85c8bddaddc62ad093`
- signed Agent Passport candidate ancestry: `f87ed81191736e1f584284d449845e83cc6e8b99`
- Competition Matrix candidate ancestry: `94468a7a1682481efe7d027d1014540f2da2e164`
- launch North Star candidate ancestry: `0e3b899bd28a060b988769d63a7bd20e3a224d27`
- generated combined verifier: `694cf56fda1f24c63dbc11416811bbef949e2ccc`
- signed-control runner: `d111e73a3c52a3e3e5c4b0cb0946b0181162d44f`
- primary-harness custody repair and live code tip:
  `a1b0b7fef5ac6844a86c47dced212c35b7f7c082`
- preserved signed-control engine snapshot:
  `bin/verifier_snapshots/c71eacfbeb9756186804f9b13cb1ebe13f2dec7f269a45b132ff51e4705d73d0.json`

All four immutable candidate tips are ancestors of the integrated source line.
The withdrawn provider parent `1742226` is not an eligible integration verdict;
its superseding transport line remains independently reviewed.

## Integration defect caught by the signed control

The first signed launch attempt failed before either entrant started. The legacy
`script_digest` selected the absolute `python.exe` token before the actual
fantasy harness, so a correctly signed harness passport could not pass preflight.
No output directory or transcript was created.

The repair makes primary-harness selection explicit:

- an allowlisted interpreter at `argv[0]` binds a real harness exactly at
  `argv[1]`;
- a direct harness at `argv[0]` remains supported;
- known interpreters are never mistaken for direct entrants;
- ambiguous commands such as `python -c ... later-script.py` are not back-scanned;
- absolute interpreter paths stay launch infrastructure while the competition
  harness must remain repository-owned.

The new adversarial checks prove both the honest interpreter-first command and
the ambiguous-token refusal. Historical engine snapshots remain available to the
standalone verifier; signed receipts cannot downgrade through a pre-passport
snapshot.

## Deterministic acceptance

The exact source later committed as `a1b0b7f` passed:

- provider hub: all 10 sections, including the six-provider catalog, strict
  envelopes, HMAC pairing, offline PKCE, mocked adapters, closed environment,
  arena purity, and the complete regression ladder;
- Agent Passport: 45/45 adversarial checks;
- Competition Matrix: 4 entrants, 6 pairs, 24 exact-engine replay receipts, and
  all 4 contrast classes;
- standalone verifier: 43/43 historical/current transcript parity;
- preserved `c71e...` engine snapshot: 16 byte-exact arena sources, snapshot
  SHA-256 `d84a72931802545a4d273265be7010139f08864d6ef3bd15903f9031d29f50d9`;
  a simulated future-engine source set still replayed the signed transcript as
  `PASS` through the preserved snapshot;
- self-check, fantasy games, scale, share bundle, public product, and Ten Fronts;
- targeted `py_compile` and `git diff --check`.

## Signed Ox Alpha MAX control

External evidence bundle label:
`agentwars-evidence/20260825-ox-signed-redraft-d111e73-9421`.

| Field | Result |
| --- | --- |
| game / seed | `fantasy_redraft` / `9421` |
| match | `ca24ce8823dd2552` |
| chain head | `f47d9f22cd605acee7657f73e757a45c72b438608657b970a1281327698bb29b` |
| transcript SHA-256 | `0b5d70ea3328eee039974f7ab44269c58debbd08dc5d42f1e875df43d923b8b9` |
| provenance SHA-256 | `81690887a35283d63af22ec0624c0327d653dccd25c6bff9768702b5f04eb97c` |
| engine digest | `c71eacfbeb9756186804f9b13cb1ebe13f2dec7f269a45b132ff51e4705d73d0` |
| harness SHA-256 | `628c5062d8682f46edf91d0e84e87ded672787805c81e70051732ac23a5aed1e` |
| result | Ox Sunday Machine 1724; Ox Future Proof 1517 |
| source claims | 12 model, 0 fallback; all 12 first attempt |
| replay | package `PASS`; standalone `PASS`; exact engine digest |
| signed identity | both seats `verified_signed`; distinct agent/version IDs |
| persisted private keys | none; keys existed only in process memory |
| persisted raw model output | none; no raw/prompt/response-output transcript keys |
| diagnostics | 12 latency rows, 2 empty stderr tails, 1 notice |

`verified_signed` proves that two different key holders signed the recorded
version declarations and that both declarations bind the exact recorded fantasy
harness digest. It does **not** prove provider identity, model identity, runtime
identity, person or legal ownership, continuous post-preflight bytes, execution
fairness, or causal authorship of a move. The 12 `source=model` notes remain
entrant-authored claims. Accordingly `modelAttested`, `providerAttested`,
`runtimeAttested`, `personAttested`, and `executionClaimsAttested` all remain
false.

## Remaining gates

- transport review `review-agentwars-opencode-transport-0340454-20260825` is
  acknowledged by Claude but has no approval verdict yet;
- the earlier Passport, Competition Matrix, and North Star candidate review
  verdicts remain blocked and are not upgraded by local integration;
- P0 review `review-agentwars-launch-integration-25cae71-20260825` produced no
  verdict and auto-blocked when the stale Claude surface missed its acknowledgement
  window; the snapshot descendant requires a fresh independent review;
- no push, merge to `main`, deploy, provider login, hosted secret custody,
  publication, customer beta, arbitrary-code execution, billing, DNS, or outreach
  has occurred.

The next eligible move is independent review of the combined exact tip and this
evidence bundle. Integration or public-beta work may proceed only after the
reviewer returns an explicit approval and the separate protected launch gates are
satisfied.
