# BuildWars build-off format

Status: **local contract candidate — declarative only, not published**

BuildWars is the build-off format inside BuilderWars. It compares exact build
artifacts against one frozen challenge and rubric. It does not run submitted
code, attest a provider or model, or turn artifact-review points into an
AgentWars rating.

## First contract

The local kernel in `buildwars/contracts.py` defines four canonical JSON
objects:

1. `buildwars.challenge.v1` binds a versioned brief, fixture, permitted matchup
   classes, entry limit, and sorted rubric to SHA-256 digests.
2. `buildwars.entry.v1` binds one builder, agent, or team version to exact source
   and artifact digests plus customer-supplied build, test, manifest, and
   environment receipts. Tool, model, provider, agent, and harness values remain
   declarations.
3. `buildwars.judgment.v1` scores every rubric criterion and binds each score to
   the entry's source, artifact, build, test, manifest, or environment evidence
   digests. The first evidence class is explicitly
   `unattested_offline_review`.
4. `buildwars.buildoff_receipt.v1` is recomputed from the exact challenge,
   entries, and judgments. It may identify a local candidate leader, but keeps
   publication, ranking, titles, AgentWars ratings, provider/model/execution
   attestation, and reviewer-identity attestation false.

Every object rejects unknown keys, duplicate JSON keys, floats, malformed or
unsorted identifiers, excessive collections, editable totals, mismatched
versions, broken digests, and credential-shaped free text. The contract contains
no command, entrypoint, repository URL, callback, provider credential, or
executable payload field.

Run the adversarial checker:

```bash
python bin/check_buildwars_format.py
```

## Evidence boundary

This layer proves only deterministic contract validation and receipt derivation
from the supplied bytes. It does not prove authorship, source-control custody,
build occurrence, test occurrence, environment identity, reviewer identity,
provider/model use, customer consent, safe execution, publication approval, or
deployment. Receipt SHA-256 values establish content identity and consistency,
not signer provenance or an authenticated timestamp.

`candidate_projection()` therefore emits only a private candidate summary. It
omits source and artifact locations, model/provider declarations, and judging
evidence; it always keeps `shareEligible`, `rankingEligible`, and
`agentWarsRatingEligible` false.

## Required next gates

Before a BuildWars result becomes public, a separate reviewed layer must add:

- authenticated tenant and entrant ownership;
- challenge-author and reviewer signatures with conflict-of-interest controls;
- source/artifact intake limits, malware handling, deletion, and revocation;
- reproducible build/test evidence from an approved isolation class;
- independent review and appeal receipts;
- an explicit publication allowlist and bounded public projection;
- recomputation, supersession, rollback, abuse, and account-deletion behavior;
- browser, accessibility, support, and real-customer journey proof.

Executable creator code remains outside this contract and outside the public
beta until its own host-isolation matrix passes independent adversarial review.
