# AgentWars Scale Phase 2 — Model Entrants + League Scheduler

## Objective

Build the smallest honest progression from the scripted two-GM preseason to scalable agent competition: a fail-closed fantasy model harness and a deterministic multi-entrant round-robin scheduler. Preserve every historical replay and produce one locally runnable model-vs-model match path without moving credentials into the arena engine.

## Authority and custody

- Repo: `C:\Users\johns\Desktop\builderwars-agentwars-scale-ox-20260823`
- Base: `f7033aee878220b004569b29e8c7c8e7775dd01c`
- Claim: `codex-app-agentwars-scale-phase2-20260823b`
- Allowed writes: `AGENTWARS_SCALE_PHASE2.md`, `arena/**`, `bin/**`, `entrants/**`, `verify.py`
- Do not commit, push, merge, deploy, post publicly, mutate Git custody, edit outside the claim, touch credentials, or launch child agents.
- Do not relabel scripted results as model-played or claimed model identity as attested identity.

## Required implementation

1. Add a fantasy model entrant that speaks `arena/1`, uses entrant-side backends, accepts a named strategy, renders a bounded decision prompt, extracts only a strict `{"player_id": integer}` decision, validates it against the observation, and uses a deterministic legal fallback on empty, malformed, unavailable, or roster-overflow output. Its response note must distinguish `model` from `fallback` without recording raw private model output.
2. Bind an explicit entrant execution claim (`scripted`, `model`, or `hybrid`) into manifest digest and transcript header. Keep `model_attested: false` and explain that replay proves adjudication, not provider/model identity. Invalid execution-claim values must fail closed before play.
3. Add a deterministic round-robin league runner for 2–16 entrant manifests. It must schedule every pair, both seat orders, one or both fantasy formats, and bounded integer seeds; verify every transcript; produce deterministic standings and a JSON summary with per-match receipt identifiers and honest overall status (`scripted_preseason`, `model_claimed_unattested`, or `mixed_unattested`). Reject duplicate names, invalid commands, invalid entrant kinds, invalid seed bounds, and unsafe/ambiguous config.
4. Keep the existing scripted season working and explicitly mark its manifests `scripted`.
5. Add focused contract coverage for hostile model output, fallback legality, execution-claim validation, deterministic schedule order, duplicate-name rejection, replay verification, model-attestation falsehood, and historical verifier preservation. Regenerate the standalone verifier if the engine digest changes.

## Validation floor

- `python bin/selfcheck.py`
- `python bin/check_fantasy_games.py`
- new Phase 2 contract command covering adapter and scheduler
- `python bin/build_verifier.py --check`
- run a small 3-entrant mixed league twice and prove byte-identical schedule/results for deterministic entrants
- verify one legacy Nim transcript and one new fantasy transcript with `python verify.py`

## Done when

The claimed source contains a bounded adapter and scalable scheduler, every changed contract passes, historical receipts still verify through digest-selected snapshots, and a human can supply their own already-authorized CLI/API backend to run a model-claimed match without the referee reading or storing the credential.

## Stop conditions

Stop and return exact evidence on any claim-scope or Git-custody violation, inability to preserve historical verification, need for a provider credential, or two matching failures. Do not substitute a scripted/stub match for the requested model-play path and call it genuine.

## Return / outcome

- The bounded Ox implementation run (`4b228ffb-ead5-450e-9fa5-5c09b9f328f8`) was rejected in full after the custody guard reported a raw Git index-hash change. Its source output was not adopted. Codex independently implemented and validated this phase in the claimed direct clone.
- Added strict manifest execution claims, a fail-closed fantasy model harness, OpenCode entrant transport, a deterministic 2–16 entrant round-robin scheduler, and focused hostile-output/replay contracts.
- Live proof: one tool-denied Ox Alpha redraft at seed 9300 replayed with chain head `f5d57926c84ed09e7dc0576e52b68c62dbe82b89b12c3aa43e784df041a13b93`. Entrant-authored source notes report 4 model picks for Ox Sunday Machine and 3 for Ox Future Proof; the remaining 5 picks used legal deterministic fallback after invalid JSON. Sunday Machine won 1746–1537.
- Truth boundary: this is `model_influenced_unattested`, not provider/model attestation. The receipt proves accepted moves, state, scoring, and result; `model_attested` and `execution_claims_attested` remain false.
- Acceptance: scale contracts PASS (12 deterministic league matches), engine self-check 21/21, fantasy contracts PASS, standalone live receipt verification PASS, and historical verifier conformance 36/36.
- No deployment, merge, account mutation, public post, or growth claim was made.
