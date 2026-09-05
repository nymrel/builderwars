# Local model/harness showcase

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
