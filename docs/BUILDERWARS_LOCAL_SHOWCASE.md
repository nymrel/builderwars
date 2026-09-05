# Local model/harness showcase

September5 follow-through: the final committed manual runner has twelve mocked
tests. The eight-test count in the09:37 section is its historical checkpoint.

## Predeclared experiment — September 5, 2026, 09:32 UTC

Status: prepared; no outcome asserted by this section. This is a small local-model
demonstration for the beta creative package, not a frontier benchmark or proof of
learning. The main engineering/review model is not being rerouted.

Use the already-installed Qwen2.5-Coder-1.5B-Instruct Q4_K_M GGUF through the
existing managed llama.cpp server on `127.0.0.1:8088`. No cloud route, downloads,
API keys, purchases or paid inference. Local electricity and hardware cost are
unknown, not zero. This is separate from protected customer-subscription clients.

Observed preflight:

- Runtime `llama-server` version9860, commit `fdb1db877`.
- Installed GGUF size1117320768 bytes; SHA256
  `cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046`.
- Runtime initially stopped; configured loopback-only, one slot, 8192 context,
  six threads, below-normal priority, no web UI. No other llama-server process
  found. GPU observed1374MiB used of16376MiB and0% utilization before startup.
- The root integrator starts the existing hidden helper only when needed, records
  its actual PID/model response, and stops only its owned process afterward.

Fixed design:

1. Two tic-tac-toe games, swapped seats, same declared model and stateless requests.
2. Plain harness receives the board, rules and legal moves. Assisted harness adds
   immediate wins and moves that do not allow an immediate opponent win, computed
   from BuilderWars' authoritative referee. This is disclosed engine assistance,
   not learned model weights or an unaided-model comparison.
3. Maximum18 total inference calls,64 output tokens each,15seconds per request,
   180seconds total, temperature0 and fixed seed. No retries, hidden move repairs,
   substitute bot moves or selective reruns after seeing results.
4. Malformed/illegal/failed responses abort that game and count as failures.
   Preserve valid partial records, original local response evidence and all
   attempted-call usage/latency. A partial game is not a win or rules-defined draw.
5. Report both seats, completion/failure counts and sample size. Report input/output
   tokens when returned and latency as observed; unreported usage and monetary
   costs remain unknown. More prompt context is not a provider reasoning-effort
   setting. Two games do not establish a statistically reliable improvement.
6. Export sanitized canonical replay links and independently replay each record.
   Tic-tac-toe has ordinary rules replay, not the stronger Connect Four portable
   proof class. Model labels/reports are not independent identity attestations.

No actual inference is made by importing or testing the manual runner. An explicit
local run is required. It cannot select a non-loopback provider. Test fixtures are
synthetic; only the separately saved execution receipt may support an actual
local-game narrative. Never relabel a fixture as an observed model decision.

## Observed result — September 5, 2026, 09:37 UTC

One execution only; no selective rerun. Both attempts stopped at the first
response because the model returned fenced JSON despite the strict JSON-only
instruction. Zero accepted moves, zero completed games, two failed attempts.
There is no winner, tactical comparison or learning-effect estimate.

| First-moving harness | Reported input tokens | Reported output tokens | Observed request ms |
| --- | ---: | ---: | ---: |
| Plain | 162 | 10 | 292.23 |
| Tactical observations | 219 | 10 | 55.28 |

These are two opening-position responses, not equal-length game costs. Startup,
warmup and order confound latency; the second response is not evidence of a faster
harness. Total reported usage: 401 tokens. Monetary and electricity cost unknown.
Both returned the same fenced decision, move `2`.

Important boundary: the production `models.ts` parser already accepts a JSON code
fence and would accept this opening move. The deliberately strict manual runner
does not. This result is **not a reproduced production parser bug**, nor evidence
that one harness plays better. Preserve this failed experiment rather than
silently changing its grader after observing the outcome. A future separately
predeclared gameplay comparison should use the production parser and report
format compliance separately from legal move acceptance.

Private local evidence directory:
`live-arena/output/playwright/local-model-showcase-2026-09-05T09-37-12-390Z-de78f689-8b01-4ae8-a07d-cd0d7d099add/`.
It retains intent, requests, original responses, the complete receipt and empty
partial replay exports. These are not publishable completed-game narratives.
Original responses contain a local model path; do not publish them unredacted.

Runtime custody: PID62816, created2026-09-05T09:36:58.2247Z, launched the preflight
GGUF with the configured loopback-only arguments. `/v1/models` reported that same
GGUF path and responses reported fingerprint `b9860-fdb1db877`. Requested alias,
runtime reports and observed executable/model bytes remain distinct evidence.
After the run, the root verified PID, creation time and executable before stopping
only that process, removed its matching PID-state file, and verified no8088
listener or PID62816 remained. Logs and experiment evidence were retained.

After the sole run, a privacy-only runner correction keeps absolute local model
paths out of future replay events, using an explicitly declared alias while
retaining original runtime reports in private receipts. The strict grader and
historical run artifacts are unchanged; inference was not rerun. Eight mocked
tests now include Windows/Unix path-leak regressions.

Validation: eight network-free deterministic runner tests pass. No application
source/configuration, provider settings, paid calls, downloads or stores changed.

## Predeclared gameplay experiment v2 — September 5, 2026, 09:46 UTC

This is a new experiment, not a rerun replacing the strict-format failures above.
Exactly one two-game, seat-swapped execution is planned, regardless of outcomes.
Same installed model/runtime and the same18-call,64output-token,15second-per-call,
180second-total ceilings, temperature0,seed42. No paid/cloud inference, downloads
or configuration changes.

Both harnesses receive an identical JSON output schema constrained to the current
referee's legal move strings. The model still selects the move; no code replaces
an illegal response or forces a tactical win. This is disclosed constrained
decoding assistance, not unaided model play. The tactical variant additionally
receives the existing referee-computed immediate tactical observations. Use the
production `parseDecision` function for acceptance and retain failed attempts.
No lessons are collected or retrieved, weights remain fixed, and no candidate is
promoted by this two-game exhibition.

Primary protocol reference verified before implementation: llama.cpp server's
[chat-completion documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#post-v1chatcompletions-openai-compatible-chat-completions-api)
documents `response_format` with `type: json_object` and a JSON `schema`. Actual
runtime response acceptance remains an empirical check, not inferred from docs.

Report every attempt and both seat assignments. If completed games occur, use
sanitized replay links for the requested same-model/harness and resource-tradeoff
creative drafts. If they fail, keep the exact failure and do not manufacture
completed-game narratives. The genuine existing free Connect Four demo can anchor
a human-challenge invitation; it is not a fabricated human-played result.

### Gameplay v2 observed result — 09:48:54 UTC

One execution, two completed games,12 actual inference calls, zero failed/capped
games. Game1: plain harness won as first seat in7plies (`2,1,4,5,0,3,6`). Game2:
tactical harness won as first seat in5plies (`2,4,1,5,0`). Series1–1; the first seat
won both games. This is no demonstrated overall tactical-assistance advantage.

| Harness | Actual requests | Reported input tokens | Reported output tokens |
| --- | ---: | ---: | ---: |
| Plain, legal-move constrained | 6 | 995 | 60 |
| Tactical, legal-move constrained | 6 | 1282 | 60 |

Total2397 reported tokens. Tactical consumed287more input tokens in this pair;
different game lengths/positions and a tiny sample prevent broad efficiency
inferences. Measured request latency totals394.23ms plain/376.86ms tactical are
warmup/order-confounded, not a speed ranking. Costs remain unknown. Both model
weights and harness logic stayed fixed; no practice memory was used.

Private evidence: `live-arena/output/playwright/local-model-showcase-2026-09-05T09-48-53-275Z-85d179d0-3434-47d0-8b07-73c48af23b12/`.
Original receipt SHA256 `da417495b803ae5967d2d1e1ab877385ae75ac93756bad37379fe30e507e7e2f`;
executed runner SHA256 `de2dbe612aaee543c479d0aaaa74d6bd33381229eb7218cdd7d2474891fd8a50`.
Runtime PID51944, created09:48:49.954235UTC, same executable and GGUF as preflight.
Exact PID/creation/executable checked at cleanup; process stopped, matching PID
state removed, and subsequent process/listener check confirmed stopped.

Both sanitized replays independently opened in fresh390px browser contexts on
canonical production; observed main asset matched the local production build.
Outcome, ply count, full stepping, no horizontal overflow, disabled execution and
not-attested evidence labels passed; zero provider requests/page errors. Retained
`canonical-replays/` contains mobile screenshots, PNG cards, replay WebMs and a
hashed capture receipt. Replay video is450ms-per-move playback, not live latency.

Visual review: full mobile result titles are readable. The downloaded long-name
PNG headline truncates before the winner suffix; do not select that crop as the
lead outcome graphic. Use the previously verified short-name Connect Four card
for the lead and these full-title mobile replays for the model comparison. Keep
long-name artwork wrapping as a ranked polish item, not a false failure of rules
replay or an unreported reason to regenerate a preferred game outcome.
