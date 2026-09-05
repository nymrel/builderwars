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

Not run yet. A completed result must cite the immutable execution receipt and
all planned cells. No change to public learning claims is authorized by this
preparation document alone.
