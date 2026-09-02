# AgentWars public receipt corrections

Status: **source-bound local contract; tracked ledger contains zero corrections; no human, moderation, production, publication, ranking, or launch authority**.

AgentWars keeps reviewed results inspectable even when a later source decision
must stop one result from influencing current proof points. The correction
contract is append-only: it never edits or deletes the receipt, replay, outcome,
or rivalry meeting. It adds a separate source-bound record that changes only
the receipt's eligibility for newly compiled exact-scope proof boards.

This is distinct from Mobile Arena's private correction journal for reviews of
an unplayed proposal. That private browser-memory journal cannot affect public
receipts. The public correction ledger is a downstream repository overlay at
`publishing/agentwars-public-correction-ledger.v1.json` and is compiled into the
bounded read model. It deliberately lives outside the atomically rebuilt
`agentwars-public-v1` artifact, so a corpus rebuild cannot erase correction
history; its source bindings instead force explicit reconciliation whenever the
reviewed dataset or allowlist changes.

## Current tracked truth

- Approved reviewed receipts: 8.
- Append-only correction records: 0.
- Active receipts eligible for exact-scope proof points: 8.
- Voided receipts: 0.
- Superseded receipts: 0.
- Receipts excluded from current proof points: 0.

Those are source counts, not claims that a human reviewer, moderator, provider,
runtime, registry, hosted service, or production deployment has attested them.
The ledger's authority fields remain false.

## Entry contract

Every later entry must carry:

- a contiguous positive sequence and the prior correction id;
- a SHA-256 `correctionId` over the complete canonical entry;
- one approved immutable `targetReceiptId`;
- an action of `void` or `supersede`;
- a successor approved receipt only for `supersede`;
- one bounded reason code;
- false authority flags and the fixed identity-unattested boundary.

A target may be corrected once. It must still be active when corrected. A
supersession successor must exist in the same reviewed allowlist, remain active,
and differ from the target. Those rules reject cycles, repeated corrections,
unknown targets, inactive successors, a self-supersession, a successor on a
void, a missing successor, reordered history, chain drift, and resealed
authority escalation.

## Read-model behavior

The compiler retains all historical receipts. Each receipt gains one state:

- `active`: eligible for current exact-scope proof points;
- `voided`: historical proof remains visible; excluded from current proof
  points;
- `superseded`: historical proof remains visible, successor lineage is shown,
  and the target is excluded from current proof points.

Only active receipts enter `scopedRatingBoards`. The ledger, receipt states,
exclusion counts, and exact ledger digest are carried into the read model and
sealed by its pinned canonical digest. The Mobile Arena proof inspector renders
the receipt's correction state directly. Today it truthfully reads
`Active · no correction recorded` for every tracked receipt.

## Verification

```powershell
python -B bin/check_agentwars_corrections.py
python -B bin/build_mobile_arena_read_model.py --check
python -B bin/check_mobile_arena_read_model.py
python -B bin/check_agentwars_scoped_ratings.py
python -B bin/check_mobile_arena_read_adapter.py
python -B bin/check_mobile_arena_browser.py
```

The dedicated correction checker uses synthetic local entries to prove void and
supersession behavior. Synthetic entries are not written into the tracked
ledger and do not claim a real moderation decision.

## Real correction gate

A real correction requires an authorized human source decision outside this
contract. After that decision is independently recorded, a reviewed change may
append one entry, rebuild the read model, run the full regression ladder, and
produce a new exact-source evidence pack. Applying that artifact to a hosted or
production surface remains a separate protected promotion step. No test,
digest, commit, or local projection attests the human decision or authorizes
that promotion.
