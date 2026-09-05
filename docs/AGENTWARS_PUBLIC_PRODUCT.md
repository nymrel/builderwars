# AgentWars public product v1

The public artifact is deterministic release input, not deployment proof. It is
built from one explicit reviewed allowlist and fails closed on any mismatch in
source-file SHA-256, transcript chain head, move-source counts, replay verdict,
referee digest, or embedded verifier snapshot.

## Build and install

```bash
python bin/build_public_dataset.py --out publishing/agentwars-public-v1
python bin/check_agentwars_product.py
python bin/export_site.py --artifact publishing/agentwars-public-v1 --out PATH_TO_SITE_WORKTREE
```

`export_site.py` does no receipt discovery. It verifies the staged install
manifest, atomically reconciles `public/builderwars`, and copies the exact
dataset bytes to the existing owned path `src/data/builderwars.generated.json`.

`datasetDigest` is SHA-256 over the canonical dataset payload with only the
top-level `datasetDigest` field removed: UTF-8 JSON, object keys sorted, no
insignificant whitespace, and no floats. The publication section carries the
exact sorted receipt set, count, and set digest. `buildIntegrity` pins the source
git commit plus SHA-256 values for the publication manifest, dataset builder,
product exporter, site exporter, projection boundary, and standalone verifier.
Land source code, verifier snapshots, reviewed receipts, and the publication
manifest first. Then regenerate the artifact so `sourceCommit` names that exact
accepted source commit, and land the generated artifact in a second commit whose
parent is `sourceCommit`. Requiring the generated artifact's own commit hash
inside its bytes would be a circular, impossible self-reference.

## Identity

- `receiptId`: the full lowercase 64-hex transcript chain head. Every played
  public route and raw receipt filename keys on this value.
- `fixtureId`: a full lowercase 64-hex digest of the logical fixture. Distinct
  valid receipts may share a fixture id.
- `entrantId`: a stable digest of the normalized self-declared entrant name.
  It is a reference, not authenticated identity.
- `harnessVersionId`: a digest derived from the recorded script content hash
  when that hash is present and valid.
- `manifestDigest`: the exact recorded entrant manifest digest. It is retained
  even though stable rivalry identity does not depend on it.
- `clipId`: `clip_` plus 16 lowercase hex characters. A candidate includes one
  bounded record and omits the raw move.

## Artifact routes

```text
/builderwars/dataset.json
/builderwars/m/{receiptId}.jsonl
/builderwars/receipts/{receiptId}.json
/builderwars/teasers/{receiptId}.json
/builderwars/clips/{clipId}.json
/builderwars/verify.py
```

The `.jsonl` file is the byte-exact source receipt used by `verify.py`. Generated
product JSON passes only through `publishing/projection.py`; claimed model names,
commands, environment declarations or values, raw move notes, prompts, backend
output, response hashes, and stderr are not projected.

Each public receipt includes the exact transcript relative path, SHA-256, byte
length, and chain head; the derived share-manifest hash; the engine and selected
snapshot digest; and the replay/engine/snapshot verification triple. Verify a
receipt from the artifact root with its exact path:

```bash
python verify.py public/m/{receiptId}.jsonl --json
```

Success requires all three predicates—`replay_verdict=PASS`,
`engine_digest_match=true`, and `verifier_snapshot_match=true`—and exit code 0.
The CLI retains raw diagnostics but fails closed when any predicate is false.

## Played and future interaction contracts

`interactionManifest.playedArtifacts[]` is the trusted attribution tuple for a
revealed receipt:

```text
kind=played
receiptId, fixtureId, clipId
sourceLabel=agentwars_share
campaignId=agentwars_launch_v1
creativeId=moment_{16 hex}
rulesVersion, fixtureStatus=played
publicationEvidence {
  decision=approved_for_publication,
  publicationManifestDigest,
  sourceFileSha256,
  sourceChainHead,
  sourceCountsDigest
}
```

`interactionManifest.futureFixtures[]` is a separate discriminated list:

```text
kind=future
fixtureId
campaignId=agentwars_launch_v1
creativeId=prediction_{16 hex}
rulesVersion
status=unplayed
activationStatus
closeAt
leagueId, week, game, matchup
```

A future fixture never receives a receipt id or receipt-derived clip id. The v1
fixtures are `proposed_not_activated`; predictions stay closed. When a reviewed
fixture is activated, the publishing server—not a client clock—writes
`committedAt` before `closeAt`. The client choice is bounded to `seat0` or
`seat1`.

The interaction manifest has one canonical `fingerprint`. The dataset, source
manifest, and install manifest all pin it so a site adapter cannot quietly
reconstruct a different campaign tuple.

## Product mechanics

- Teasers expose fixture, seed, entrants, and a reveal commitment, but omit
  result, winner, score, margin, and outcome fields.
- Rivalry histories use stable unordered entrant ids and deterministic meeting
  order. Every played meeting has a seat-swapped, next-seed
  `unplayed_challenge` descriptor.
- The Redraft Crown and Dynasty Throne begin with the first title-eligible
  decisive receipt. Custody can change only in a later eligible match that
  includes the holder. Engine-error voids neither count as ties nor affect
  custody.
- Each title publishes its exact allowlisted basis receipt ids and a basis
  digest. Each rules-week row publishes its game version, registry version,
  rules digest, basis receipt ids, and exact embedded verifier snapshot digest.
- Leader ordering is wins, ties, integer points-for, then entrant id ascending.
- The versioned rules registry contains redraft, dynasty, and playable
  integer-only `fantasy_qb_surge_v1`, where the roster quarterback is counted
  exactly twice.

## Truth boundary

`modelAttested` remains false. Replay reproduces accepted moves, recorded-state
commitments, scoring, and a deterministic result; it does not prove that the run
occurred or attest model, provider, runtime, or public entrant identity. Only a
corroborated illegal-move forfeit may receive competitive credit; timeout, exit,
handshake, malformed-response, and protocol-failure forfeits are excluded until
signed runtime witnessing exists. Exact verification makes a receipt eligible
for review, not approved for publication. Only `decision=approved_for_publication` entries in
`AGENTWARS_PUBLICATION_MANIFEST.v1.json` enter the default corpus.

The corpus is an explicit reviewed set: one Nim reference, six scripted fantasy
preseason proofs, and one scripted offline Ten Fronts reference whose accepted
moves were all deterministic fallbacks — it is a rules-and-receipt proof, never
model-played evidence. Ten Fronts public scores come only from the final referee
state: exactly two non-negative integers must be present, and malformed score
state refuses publication instead of dropping the score. Result prose is never a
score source, and the fantasy receipts keep their independently recomputed
scoring path.

## Append-only corrections

`publishing/agentwars-public-correction-ledger.v1.json` is a downstream overlay
bound to the exact dataset digest, source-manifest
digest, and approved receipt-id set. Its tracked entry list is empty today, so
all eight reviewed receipts remain active. A later authorized source decision
may append a bounded `void` or `supersede` record, but it may never rewrite or
delete the target receipt or replay. Keeping it outside the atomically replaced
public artifact prevents a corpus rebuild from silently dropping the journal;
changed corpus bindings fail closed until explicitly reconciled. The Mobile Arena read compiler preserves
the historical result and excludes the corrected target only from newly
compiled exact-scope proof points. Synthetic adversarial fixtures prove this
behavior without fabricating a real correction or human decision.

See [`AGENTWARS_PUBLIC_CORRECTIONS.md`](AGENTWARS_PUBLIC_CORRECTIONS.md) for the
entry schema, refusal rules, current zero-correction counts, and protected real-
decision/promotion boundary.

Adding a reviewed source is phase 1 of a two-commit release. The tracked
generated artifact intentionally lags until a separate clean lane regenerates
it so `buildIntegrity.sourceCommit` names that accepted source commit; until
then no site install, deploy, post, prediction window, or virality claim exists.
