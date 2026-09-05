# Frozen practice-memory experiment

Predeclared September5,2026,10:19UTC, before evaluation inference. This is a
bounded diagnosis of the current prompt-memory mechanism, not weight training,
world-level chess, a frontier-model comparison or a promotion decision.

## Question and source

Does the current production practice-memory prompt help the same installed local
Qwen2.5-Coder-1.5B-Instruct Q4_K_M choose an immediate win or avoid an immediate
loss on positions it did not see in the two retained practice games?

Practice source is the original actual-game receipt at
`live-arena/output/playwright/local-model-showcase-2026-09-05T09-48-53-275Z-85d179d0-3434-47d0-8b07-73c48af23b12/receipt.json`.
Do not replace these games with hand-authored successes. The plain contender
missed a win at ply5/game1 and a block at ply4/game2. Use its unchanged profile
and the production PracticeMemory analyzer/context, frozen before evaluation.
The opponent's tactical assistance in practice is part of this source's history.
The frozen snapshot contains both profiles, including the tactical opponent's
game1/ply4 mistake. Filtering by the unchanged plain profile supplies only its
two lessons; snapshot and filtered-context digests describe different objects.

This experiment tests the production-generated reminder text appended to a
local chat request's user message. Production OpenRouter also appends this text
to its user message, but the custom-harness protocol sends a `practiceMemory`
field which the harness must consume. This is not end-to-end proof of an
arbitrary customer's harness delivery path or of a frontier provider's response.

## Fixed diagnostic design

- Deterministically enumerate reachable tic-tac-toe positions with the existing
  authoritative referee. Exclude every practice position and its rotations or
  reflections, including the side to move. Deduplicate held-out symmetry classes.
- Select12positions: three immediate-win and three avoidable-immediate-loss
  positions for each seat. Fail before inference if the required cells cannot be
  filled. The selected positions and answer keys are saved before any call.
- Run each position once with no memory and once with the exact frozen memory.
  Alternate condition order per position. Both arms use the same board/rules,
  legal-move-constrained JSON, temperature0, seed42 and64output-token request cap.
  Only the production memory prompt differs. Never put held-out answer keys or
  current-position tactical observations into either model prompt.
-24calls maximum,15seconds per call,240seconds total. Fixed loopback endpoint
  `http://127.0.0.1:8088/v1/chat/completions`; no redirect, key or cloud route.
  No retries, substitute moves or selective reruns. Preserve all failed calls and
  unknown usage. A cap leaves remaining cells missing, not failed or successful.
- Production decision parser plus referee legal validation. Grade wins and
  avoidable losses independently; report malformed/illegal/HTTP/deadline failures
  separately from legal tactical errors. No evaluation record enters memory.
- Report paired correct/wrong transitions and resource totals, not just aggregate
  wins. This small, deterministically selected tactical set is descriptive only;
  it is not an unbiased estimate of all positions or evidence of durable learning.

## Runtime and privacy

No downloads, cloud calls, purchases or routing changes. The installed GGUF was
rehash-verified as `cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046`.
The installed llama-server reports9860/fdb1db877. Actual runtime startup/identity,
request intent, fixture/memory digests and cleanup must be recorded at execution.
Use one slot,8192context, six threads, below-normal priority, loopback only and
no web UI. No runtime is started until the runner's synthetic checks pass.
Private raw response metadata may contain the GGUF path; it is not public media.
Local electricity/hardware and dollar costs remain unknown. API cancellation
does not prove the server instantly stopped computing.

## Result

One run completed September5,2026,10:27:50UTC.24actual loopback inference calls,
12positions per condition, zero failed/capped cells. The model solved3/12 without
memory and2/12 with memory. Both conditions solved two positions; baseline alone
solved one; memory alone solved none; both missed nine. No selective rerun.

| Condition | Immediate wins | Avoidable threats | Input tokens | Output tokens |
| --- | --- | --- | --- | --- |
| No memory | 1/6 correct | 2/6 correct | 2009 | 120 |
| Frozen memory | 1/6 correct | 1/6 correct | 3761 | 168 |

The extra1752input and48output tokens did not buy an observed improvement on
this set. This supports treating reminders as unproven assistance. It does not
establish that memory always hurts, that another model would behave similarly,
or that a12-position difference is statistically reliable. No promotion or
production behavior change. Positions have now been observed; future tuning must
not reuse them as untouched holdout evidence.

Immutable output directory:
`live-arena/output/playwright/learning-comparison-run-2026-09-05T10-27-50-585Z-e8f22bdd-48b5-428f-9d02-67762b67ed80/`.
Sanitized share-summary.json SHA256:
`1ba60d18ad750c2d335c2c1f542ba40317a25e9453f014684df5f36e35a6a6d6`.
Original intent/private plan and all request/result receipts retained. Fixture
digest b1b31637a80aefd699e6ebf3eb9f3d4bd9efee535f6c8a321f436a053eebe7db;
memory digest3969d2b1c1a1f5a78b7d87429e6f51b49d4f83d0634550fbe79c8cc5da503fd1.
These match the no-inference preparation. Original source JSON-content digest
d8411cd60adc06287fcb1f9cd66fe3e92254af280b2cb7c0b2d36716fd891b69 is not the raw
receipt-file hash; serialization is explicit.

Executed clean source b7c1da11583b0dfa70818ea2d2d4241d4520abfc, runner SHA256
3721a019dc9df9712949037815271edf37b3e40f592ea9f0c73b1b685eda3082.
The runner is byte-identical at reviewed head8d66404c52752cb6060393539b5119bf10781be6:
the Git diff is empty and a fresh SHA256 matches the execution hash above.
Seven synthetic runner tests,144total Node tests, type checks and build passed.
Independent bounded pre-run review approved the source/fixture/containment
contract; test success alone is not the actual model result.

Post-run independent audit regenerated the plan from the original practice
receipt and checked all24 saved requests/raw responses against the referee.
Moves, legality, grades, usage, order and summaries reconciled. Intent10:27:50.587,
private plan.588 and first request.589UTC confirm the plan preceded dispatch;
every saved request preceded its result. No extra inference was used to audit.

Runtime PID58036, created10:27:31.450039UTC, exact observed llama-server executable
SHA25680ef4d0f61f6bd54858808ac79478ccad28e41e3ea27aba2968ca9e98099fd0c.
Health returnedok and model listing matched the rehashed installed GGUF before
execution. Requested alias, response model metadata and local executable/weight
observations are distinct evidence; no independent provider attestation claimed.
After completion root verified PID, creation time and executable before stopping
only58036; process and8088listener were independently absent. Logs retained in
output/playwright/learning-runtime-20260905-1029. No cloud calls or dollars paid.
Hardware/electricity cost remains unknown.

Cross-family source review `builderwars-beta-1ca032e/2` approved8d66404, resolved
model claude-fable-5-1; receipt is retained in StudioData/artifacts/fable-roundtrip.
The wording clarifications above address its four optional documentation notes.
CI33960895197 passed Windows/Linux verification, browser and Android, but iOS
simulator launch exceeded60seconds. This is a separate unresolved integration
gate, not a failed model experiment or evidence of its underlying cause. No
blocking check was bypassed and this manual diagnostic is not deployed.

Next product action: keep learning claims limited to retained reminders. Design
an opt-in versioned harness improvement against a fresh held-out set, with any
deterministic rule assistance explicitly separated from learned behavior. Do not
attempt to make this run pass by replacing answers or changing its scorer.
