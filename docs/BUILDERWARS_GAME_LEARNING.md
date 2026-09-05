# Practice feedback and evaluation

Candidate base: `6eaaba1edcc9afcdd5f26810e7ec2f310277b747`. This is agent context adaptation, not model weight training or evidence of market leadership.

## Diagnosed disconnect

Previously each browser/bridge move received the current board plus a fixed builder strategy. Series aggregation verified results and swapped seats but supplied no cross-game feedback. The local bridge also explicitly discarded unrecognized request fields. The Python arena-engine series and independent fantasy/ten-fronts harnesses remain separate execution paths; this candidate does not silently change them.

## Implemented loop

A newly created, locally played, rule-complete practice game is replayed with the unchanged referee. For Connect Four, tic-tac-toe and custom connect boards up to 42 cells, the analyzer identifies missed immediate wins and moves permitting an immediate opponent win when a safe alternative existed. Forced losses are excluded. Imported records, watched matches, incomplete/capped games and evaluation outcomes cannot create practice lessons. Chess/checkers and fixed built-in opponents do not learn from this module.

Each connected contender receives up to four recent examples in subsequent requests. The local bridge forwards the bounded optional `practiceMemory` string (maximum 4000 characters); legacy requests omit it. The bridge labels its request object as game data, so an external harness can still ignore lessons; forwarding is not behavioral compliance. No extra model call or automatic move replacement is made. Illegal responses still pause the match. The request receipt proves context inclusion, not that an external harness obeyed it or that a model improved.

Device memory retains at most 64 contender-game episodes with eight mistakes per episode. Contender configuration and source-game identities are hashed. Keys, endpoint text, strategy text and model comments are not stored in this memory. Hashes are local isolation/provenance aids, not identity attestations. Different fresh game IDs can record the same repeated mistake; replaying the same ID is deduplicated. A storage failure falls back to this tab. Clearing memory cancels pending admission. Local storage is editable by its owner and is not a trusted tournament authority.

## Evaluation contract

Baseline mode sends no practice memory. The optional assisted mode snapshots memory at series start, keeps that copy through seat swaps, and exports its schema, source examples and context digests alongside accepted-request receipts. Evaluation never updates memory. Clearing device memory during an evaluation preserves its existing frozen snapshot. The referee, portable proof and replay record schemas are unchanged; learning details are a separate evaluation field.

Read-only tactical diagnostics count missed wins and avoidable immediate losses per contender, with accepted decisions as the explicit denominator. Unsupported, incomplete and invalid attempts are excluded and counted. These are narrow one-ply error diagnostics, not an overall strategy rating. Current series use standard starts and uncontrolled model sampling; they do not constitute a matched-seed or held-out benchmark.

## Acceptance and remaining measurement

Tests cover a completed game producing lessons, next-request inclusion in OpenRouter and the local bridge, reload, profile/rules isolation, duplicates, pending clear, forced losses, frozen snapshots, seat swaps and baseline omission. Browser fixtures deliberately return fixed scripted mistakes; their passing results demonstrate plumbing, not model performance.

Before claiming learning improves a named model, freeze an external practice corpus and separate unseen test positions, provider/model/harness revisions, both seats, opponents and identical output/effort budgets. Compare no-memory and frozen-memory arms, count illegal responses and provider failures, report one-ply error rates with sample counts and uncertainty, and record actual latency/token costs. Reject a candidate that only memorizes its practice positions. No such live provider performance result is claimed by this change.

Research context: [Reflexion](https://arxiv.org/abs/2303.11366) studies feedback held in episodic memory for later decisions. It supports testing explicit memory as a mechanism; its published results are not evidence for BuilderWars.

Rollback: revert this candidate's learning module, main/model/bridge integrations and tests. Referee verification and prior native sharing remain on the parent source. Production and store adoption are owned by the BuilderWars integration lane.

## Candidate validation receipt (2026-09-05 UTC)

- 103 Node tests passed, including 15 learning tests; 9 Python bridge tests passed.
- Web and packaged-native builds/typechecks passed.
- Twelve Chromium journeys covered the regression set across the initial full run and focused repair runs. Final learning and Academy flows were rechecked after diagnostics changes. Firefox/WebKit portable-proof checks passed. Four packaged synthetic native journeys passed. These are browser/plugin mocks, not physical-device acceptance.
- Fable5.1 turn2 approved the learning delta on base6eaaba1 with no blocking findings. Receipt: `C:/Users/johns/StudioData/artifacts/fable-roundtrip/builderwars-learning-20260905-turn-2.json`; resolved model `claude-fable-5-1`. Review scope excludes unrelated native parent changes and production adoption.
- Referee source files are unchanged; generated digest remains `d5135878ce69345f5e8ee214c03d53cd1593052b9bcb97d1a96363f9b6dfa823`.
- No live move-provider calls were made in validation. No named-model performance improvement, production release, store submission or store publication is claimed.
