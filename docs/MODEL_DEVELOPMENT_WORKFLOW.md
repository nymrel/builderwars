# Connected-model development workspace

Implemented in draft [PR68](https://github.com/nymrel/builderwars/pull/68), pending
independent review and release. This slice connects immutable frontier versions to
real browser model execution. It does not restart the retired numeric campaigns.

Visual thesis: the existing quiet Evals workspace, a compact version list and one
operation status. Content: connect/freeze, inspect/edit, explicitly practice or
compare, inspect retained results, select or roll back. Interaction: immediate
busy/cancel status, version-selection feedback, reduced-motion-safe expansion of
run details; no decorative motion or new design system.

## Contract

- A consented one-move probe records actual returned identity before freezing a
  baseline. Connection checks alone cannot establish that identity.
- Version selection and rollback start no inference. A version freezes provider,
  requested/reported identity, effort, prompt, memory and limits. Unsupported
  tools, sampling or a different browser adapter source cannot execute silently.
- Keys and endpoint addresses remain in the connected seat's transient memory.
  They never enter the version or result. The adapter is source-bound; a hash is
  not independent execution, identity or provider billing attestation.
- One operation at a time. Practice runs two seat-swapped games; comparison runs
  four games against the unchanged bundled Tactician, one game per version/seat.
  The board starts empty in every game. These public development games are not
  held-out admission and never automatically promote a version.
- Model-memory practice uses only its own completed connect-game records, never
  imported/evaluation games. Chess/checkers support manual strategy/memory versions
  and comparison; automated chess engine error-to-memory adaptation is still open.
  Saving a reminder is not training model weights or evidence of improved play.
- Cancel stops local acceptance and further requests. A remote provider may still
  finish/bill an already submitted request. Preserve failed/cancelled attempts and
  unknown usage; no retry or automatic resume.
- Versions/results remain in the tab unless explicitly downloaded. Import validates
  versions, does not restore credentials, and never starts an operation.

## Verified implementation gates

The following results belong to PR68 head
`0d1e5b35a7d76f2cbb6ba2f9b50ff6f113622ee6`, not to a later commit or production:

- The September 22 Codex rebase review approved the conflict resolution and
  recorded 36 passing focused games/development/transport tests. It requested this
  status correction and an independent Fable review before ready/merge.
- All seven hosted checks completed successfully on September 23. The
  [Live Arena run](https://github.com/nymrel/builderwars/actions/runs/35820404628)
  passed Ubuntu and Windows verification, browser journeys (including model
  development and packaged native assets), Android debug/WebView recovery and
  iOS simulator checks.
- The [Release Evidence run](https://github.com/nymrel/builderwars/actions/runs/35820404642)
  passed rules roundtrip, real PeerJS recovery and duel journeys. The
  [AgentWars integrity run](https://github.com/nymrel/builderwars/actions/runs/35820404623)
  also passed. These checks do not attest real provider identity/billing,
  physical-device readiness, release signing or app-store acceptance.

## Remaining gates

Independent Fable review is still pending; the Codex rebase review does not fulfill
it. The final candidate also needs documentation confirmation, required CI at its
exact published source, merge and canonical deployment with production journey
checks. Existing production main does not establish release of this PR's new
model-development workspace.

This document does not assert release or full Phase 4 completion. The
engine-assisted complex-game training loop, held-out two-family gains, complete
four-family event, creator task adapter and native/store/third-party gates remain
separate campaign requirements.
