# AgentWars tester ceremony and synthetic rehearsal

Status: local, credential-free readiness contract. No customer has completed
this ceremony, no human feedback has been collected, and no protected account,
provider, deployment, deletion, rollback, publication, or launch action is
authorized or attested by this work.

## Purpose

The first real BuilderWars tester session must be useful evidence rather than a
guided product demo whose missing steps are silently filled by the team. This
contract turns that future session into an ordered, fail-closed ceremony while
allowing the credential-free portions to be rehearsed now.

The executable module produces six digest-bound artifacts:

1. the exact ceremony contract;
2. a deterministic synthetic rehearsal;
3. the structured feedback rubric;
4. an explicitly uncollected feedback placeholder;
5. a local cleanup rehearsal; and
6. a held readiness decision plus a non-actionable operator packet.

All human and production authority fields remain false. Fixtures, mocks,
internal operator accounts, self-declared model labels, dashboard status, local
recovery drills, synthetic ratings, and logical tombstones are expressly
refused as substitutes for production evidence.

## Ordered 16-step journey

| Order | Step | Local rehearsal | Evidence required in the future protected ceremony |
| ---: | --- | --- | --- |
| 1 | Read the truth boundary | Required | Fresh customer acknowledgement and served disclosure digest |
| 2 | Bind the exact release and rollback target | Held | Deployment id, served-byte digest, rollback-target digest |
| 3 | Open supported mobile and desktop views | Required | Mobile and desktop session receipts |
| 4 | Sign up, sign out, and sign back in | Held | Redacted signup, signout, and signin receipts |
| 5 | Pair a customer-owned runner and recover after disconnect | Held | Pairing, disconnect, and recovery receipts |
| 6 | Create two distinct encrypted agent/harness passports | Held | Two passport digests and custody receipt |
| 7 | Build, qualify, and reach a receipt-linked learning action | Required | Builder, qualification, and learning receipts |
| 8 | Run one genuine sanctioned model/harness match | Held | Fresh provider consent, match receipt, and cost receipt |
| 9 | Replay and inspect the proof projection | Required | Replay receipt and proof-projection digest |
| 10 | Submit privately, receive independent review, then publish a bounded projection | Held | Submission receipt, detached review signature, publication receipt |
| 11 | Open the spectator share and start an exact runback | Required | Share transport, spectator probe, and runback receipt |
| 12 | Exercise failure, storage-denial, offline, reduced-motion, and accessibility paths | Required | Supported-device, accessibility, and offline/error receipts |
| 13 | Revoke the runner and remove local/provider artifacts | Held | Revocation plus local and provider cleanup receipts |
| 14 | Delete the account and prove tenant-scoped hosted cleanup | Held | Account deletion, webhook, and hosted-cleanup receipts |
| 15 | Execute rollback while preserving signed evidence | Held | Rollback receipt, post-rollback probe, evidence-chain verification |
| 16 | Collect structured feedback and triage severe confusion | Held | Feedback and blocker-triage receipts |

Only steps 1, 3, 7, 9, 11, and 12 are locally rehearsable. A passing local
rehearsal records every other step as `HELD_PROTECTED`; it cannot mark a human
observation, protected step, or production authority as passed.

## Feedback contract

The future tester rates each category from 1 to 5 after informed consent:

- orientation clarity;
- truth-boundary comprehension;
- receipt and replay trust;
- build and compete clarity;
- share and runback clarity;
- recovery and cleanup confidence;
- accessibility and usability; and
- return intent.

The rubric also accepts explicit blocker classes and severe-issue classes. It
must not collect identity fields, credentials, provider tokens, prompts, raw
model output, or unrestricted personal data. During local rehearsal, ratings,
blockers, severe issues, and notes are all empty and the status is
`NOT_COLLECTED_SYNTHETIC_REHEARSAL`. Any synthetic score or note is rejected as
fabricated human feedback.

The protected ceremony stops and routes a triage receipt when the tester cannot
understand the truth boundary, cannot recover or clean up, encounters an access
or safety blocker, sees evidence inconsistency, or cannot complete a required
step without staff performing it for them. A stopped session is valid learning;
it is not a launch pass.

## Cleanup matrix

The local rehearsal simulates cleanup for exactly four resource classes:

- browser-local blueprint;
- browser storage;
- service-worker cache; and
- synthetic rehearsal state.

Seven classes remain protected and unexecuted: runner pairing, encrypted
passports, provider artifacts, private submission, hosted tenant records,
customer account, and production test release. No local fixture may claim the
revocation, provider deletion, account deletion, hosted cleanup, or production
rollback receipts required by the real ceremony.

## Protected activation sequence

The real customer ceremony may start only after the following are independently
bound to the exact reviewed source:

1. stage 11 protected runtime configuration is verified;
2. stage 12 production deployment and served bytes are verified;
3. a tested rollback target is named;
4. a consent and redaction protocol is approved; and
5. support and incident ownership are staffed for the session.

Until all five prerequisites are proven, the generated operator packet remains
`NOT_ACTIONABLE_PROTECTED_GATES_HELD`, and its smallest human action is only a
conditional instruction: verify the prerequisite receipts, then schedule one
fresh consented tester. It contains no credentials and executes nothing.

After those prerequisites pass, the operator should:

1. bind the packet to the exact deployment, source, tree, and rollback target;
2. obtain fresh tester and provider consent without accepting terms on the
   tester's behalf;
3. let the tester perform all customer actions while the observer records only
   redacted receipt identifiers and digests;
4. stop on any severe issue rather than coach around it;
5. complete runner, provider, account, hosted-state, and release cleanup;
6. verify rollback and preserved evidence independently; and
7. obtain a detached review before any separate launch decision.

Passing the ceremony does not itself authorize public launch. Stage 13 remains
held until the consented journey, cleanup, detached review, and separate operator
launch decision are all present.

## Commands and evidence boundary

Run the local adversarial contract:

```powershell
python bin\check_agentwars_tester_readiness.py
```

The checker covers exact schemas and ordering, deterministic digests, malformed
and missing steps, protected-status drift, forged human observations, fabricated
feedback, cleanup escalation, cross-source binding, secret-bearing packets,
shortcut substitutions, and every production-authority field.

A green result proves only that reviewed local source can construct and verify a
synthetic ceremony rehearsal while refusing unsupported claims. It does not
prove a real tester, consent, identity, authentication, provider subscription,
paid compute, match, review, publication, deletion, rollback, deployment,
support response, audience, retention, revenue, or launch.
