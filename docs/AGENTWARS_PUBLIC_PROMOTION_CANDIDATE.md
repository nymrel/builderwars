# AgentWars offline public-promotion candidate

This is a candidate bridge, not a publish action. It moves one exact private
reviewer-case export across the repository boundary only far enough to support
another human-reviewable source-control decision.

The bridge never signs in, fetches a case, contacts Nymrel, invokes a provider,
edits the publication manifest, copies a transcript into `matches/`, regenerates
the public product, commits, deploys, ranks a provider, or authorizes any of
those actions.

## Input and protected handoff

The input is the exact JSON response from the protected reviewer-detail route:

```text
GET /api/builderwars/competitions/review?runnerId=awr1_...
```

Obtaining that response remains an operator-present account action. An
allowlisted reviewer must authenticate, inspect the private result, and record
the immutable `approved` decision through the reviewer rail before exporting
the detail response. Store the downloaded response in a direct local regular
file outside source control. Do not place the private export in this repository.

The downloaded JSON is not signed by Nymrel. Its `reviewerAccess` and approval
fields are therefore claims in an offline file, not cryptographic proof of
server origin or reviewer identity. The candidate records all four of these as
false:

```text
reviewerExportOriginAttested
reviewerIdentityAttested
serverSignatureVerified
authenticatedTransportVerifiedOffline
```

Source-control review is the authority that decides whether the candidate may
enter the explicit BuilderWars allowlist.

## Prepare a candidate

Choose a new output directory outside the BuilderWars repository. All four
acknowledgements are required:

```bash
python bin/prepare_publication_candidate.py \
  --reviewer-export PATH_TO_EXACT_REVIEWER_DETAIL.json \
  --out PATH_TO_NEW_EXTERNAL_CANDIDATE_DIRECTORY \
  --reviewer-approved-export-v1 \
  --candidate-only-v1 \
  --no-publication-v1 \
  --source-control-review-required-v1
```

The destination must not exist. The tool rejects repository-local output,
UNC/reparse traversal, symlink or multiply linked input, duplicate JSON keys,
floats, unknown fields, oversized data, and overwrite attempts. It stages on
the destination volume and atomically renames the completed directory.

## Independent verification

Before any candidate is written, the bridge requires all of the following:

Both job provider claims must also belong to the current executable,
non-arbitrary provider subset derived from the provider catalog. The
customer-local `claude_code` route is eligible only with its exact
`claude_code:claude -p` claim; arbitrary `custom_agent` execution is refused
before any candidate directory is staged. An old self-declared label cannot
bypass current provider policy merely because replay still verifies.

1. The outer response is the exact reviewer-detail schema, includes private
   evidence, and carries an `approved` but still-not-published decision.
2. Every provider, account, plan, billing, model, person, runtime, harness, and
   match attestation flag is exactly `false`; ranking and promotion authority
   are also `false`.
3. Job, request, decision, private-result, and evidence-body ids, timestamps,
   consent fields, and commitments agree exactly.
4. The evidence body is canonical ASCII JSON. Its raw-body, job, summary,
   evidence-bundle, compressed-transcript, transcript, projection, and chain
   commitments all recompute.
5. Base64url is canonical and the zlib payload is exactly one complete bounded
   frame. Concatenated frames, trailing bytes, truncation, and expansion past
   the transcript limit fail closed.
6. BuilderWars runs its current snapshot-aware standalone verifier against the
   decompressed transcript. Replay, effective verdict, engine digest, and
   verifier snapshot must all pass.
7. BuilderWars independently rebuilds the public receipt. Its projection
   digest, game, seed, entrants, harness digest, score pair, winner, move-source
   counts, transcript hash, chain head, and identity coverage must match the
   Nymrel evidence.
8. Ready and move replies have the fixed sanitized harness shape; raw provider
   output, prompts, stdout/stderr, diagnostics, secret fields, and
   high-confidence credential patterns are refused before the byte-exact
   transcript is staged.
9. Every accepted move must remain self-declared `model` source while
   `modelAttested` stays false. This supports
   `model_influenced_unattested`, never provider/model ranking.
10. The chain head and transcript hash are not already represented in the
   current publication manifest.
11. The publication manifest bytes and generated public artifact tree are
    unchanged before and after preparation.

## Candidate directory

The atomic output contains exactly four files:

| File | Purpose |
|---|---|
| `transcript.jsonl` | Byte-exact decompressed transcript that independently replayed. |
| `public-receipt-preview.json` | Safe BuilderWars public projection; not a public route. |
| `manifest-entry-candidate.json` | Suggested source path and an `eligible_for_review` entry without a sequence. |
| `candidate.json` | Export, review, evidence, file, truth, and false-authority commitments. |

`manifest-entry-candidate.json` is intentionally not directly insertable. It
has no sequence, keeps `titleEligible:false`, and remains
`eligible_for_review`. A source-control reviewer must assign the next contiguous
sequence and explicitly choose either `approved_for_publication` or `held`.

## Stage the separately reviewed source decision

Do not run this step merely because candidate preparation succeeded. First
inspect the private export, all four candidate files, and the candidate digest.
Use a fresh claimed BuilderWars worktree at the exact reviewed commit. The
read-only state command returns only the full source SHA, clean/dirty count,
publication-manifest SHA-256, and protected generated-tree digest:

```bash
python -B bin/apply_publication_candidate.py --inspect-protected-state-v1
```

If the reviewer explicitly selects a decision, bind those exact values again:

```bash
python -B bin/apply_publication_candidate.py \
  --candidate-dir PATH_TO_EXACT_EXTERNAL_CANDIDATE_DIRECTORY \
  --expected-candidate-digest FULL_CANDIDATE_SHA256 \
  --expected-head FULL_REVIEWED_BUILDERWARS_GIT_SHA \
  --expected-manifest-sha256 FULL_CURRENT_MANIFEST_SHA256 \
  --expected-generated-tree-digest FULL_CURRENT_GENERATED_TREE_DIGEST \
  --decision approved_for_publication \
  --label "REVIEWED_SOURCE_DECISION_LABEL" \
  --source-control-decision-v1 \
  --title-ineligible-v1 \
  --no-generated-artifact-mutation-v1 \
  --no-deploy-v1
```

`--decision held` is the only other accepted decision. The tool never accepts
`eligible_for_review` as the final source decision and always forces
`titleEligible:false`. It requires the four-file candidate outside the repo,
direct regular files, canonical JSON, the exact candidate digest, false
offline-origin and identity attestations, a current-engine replay PASS, exact
projection/source counts, only self-declared model moves, a clean exact source
head, and unchanged protected hashes. A byte-identical orphan transcript can
resume after response loss. One exclusive lock in the repository's common Git
directory serializes decisions across worktrees; concurrent invocation and any
other dirty or conflicting state fail closed.

The inspect response includes `sourceDecisionLockPresent`. A live lock contains
only the schema version and owning process id. If a process is killed mid-step,
do not auto-delete the marker: first prove that exact process is absent, verify
the marker is one regular file in the repository's common Git directory, and
inspect the source and manifest state before removing only that stale marker.
Then rerun inspect and the digest-bound command; its orphan/idempotency rules
decide whether staging may resume.

The command stages only:

1. the byte-exact transcript at the candidate's constrained
   `matches/agentwars-review-candidates/...` path; and
2. one next-contiguous source manifest row with the explicit reviewed decision.

It does not rebuild `publishing/agentwars-public-v1`, create public bytes,
commit, deploy, rank, contact a provider, or prove the unsigned export's server
or reviewer origin. Its successful status is
`source_decision_staged_not_built`; an exact response-loss rerun returns
`source_decision_already_staged_not_built`.

## Separate release actions

A candidate does not change the public corpus. Promotion remains a reviewed
multi-stage release:

1. Independently inspect the candidate and private export.
2. In a separately claimed write lane, run the digest-bound source-decision
   command above and review its exact transcript plus manifest diff.
3. Run the complete product checks and commit that source decision.
4. In a separate clean lane, regenerate the public artifact so
   `buildIntegrity.sourceCommit` names the accepted source commit.
5. Review and commit the generated bytes.
6. Export to the product worktree, deploy only through an authorized release
   gate, and externally prove the exact served bytes and replay route.

Until every applicable step has its own receipt, the status remains
`candidate_prepared_not_published`.

## Adversarial check

The checker creates a fresh current-engine fantasy match using two deterministic
local test harnesses. It makes no provider or network call. It proves the valid
path and attacks rejection, true attestation, a fully re-bound projection swap,
the arbitrary-command provider route, concatenated zlib frames, request substitution,
duplicate JSON keys, missing acknowledgements, overwrite, deterministic output,
and protected-artifact non-mutation:

```bash
python -B bin/check_publication_candidate.py
python -B bin/check_publication_source_decision.py
```

The source-decision checker uses only temporary Git repositories and never
applies its fixture candidate to the real publication manifest or generated
artifact tree. It covers both decisions, response-loss idempotency, exact orphan
resume, exclusive-lock contention, stale source/manifest/artifact commitments,
dirty worktrees, ignored source targets, candidate and projection tampering,
path traversal, identity collisions, conflicting pre-existing bytes, missing
acknowledgements, and protected-artifact non-mutation.
