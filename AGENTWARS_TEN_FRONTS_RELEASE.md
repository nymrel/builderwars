# AgentWars Ten Fronts release

## Objective

Ship a fully revalidated Ten Fronts release candidate: register the deterministic
Blotto game in the arena, ship its model harness and contract checker with a
claimed forfeit fixture, correct the controller-found fail-closed defect in
`legal()`, regenerate the single-file verifier around the corrected engine
digest, preserve exactly one scripted offline receipt on that engine, and state
the exact boundary between what receipts prove and what they do not.

## Authority and custody

- Claim: `codex-app-builderwars-tenfronts-ox-20260823-v4` (autonomy profile `release-candidate`, authority local write on exact files)
- Repo: `C:\Users\johns\Desktop\builderwars-agentwars-tenfronts-ox-clone-20260823`
- Branch/base (unchanged, no commits): `codex/agentwars-tenfronts-ox-20260823` at `336d478d38b1e1ff5e93598fd89237bdf2b1c5e7`
- Guarded-run receipt history:
  - `6399df22-c121-41d7-a9a5-b630f383c3c7` — rejected solely because its wildcard claim did not name the concrete verifier-snapshot filename. Not acceptance evidence.
  - `ea349059-9295-47ee-bb20-5d81842e5e5e` — passed provider/scope/VCS gates but is **not** controller acceptance: the controller independently reproduced the `legal()` mixed-key defect below. Its preserved output was the reviewed baseline for this correction round.
- Excluded by scope: publishing/public datasets, dependencies, git metadata, studio state, credentials/provider/account state, schedules, deployment, social surfaces. No commit, push, deploy, or account mutation occurred.

## Controller defect and fix

[DEFECT] `legal(state, {"signal": "ok", 1: "x", "2": "y"})` raised
`TypeError: '<' not supported between instances of 'str' and 'int'` because
unexpected-key reporting sorted raw dict keys. The module contract says `legal()`
is total and fail-closed; any mixed string/int/None/tuple/float key set must
return `(False, reason)` without an unsafe ordering or a traceback. The same
boundary exists in the commit phase.

Fix (no weakening of exact-key enforcement; accepted move data is never touched):

1. `arena/games/ten_fronts.py` — new `_format_keys()` helper sorts key reprs
   (string-only comparisons) instead of raw keys; both phase rejection paths use
   it. Deterministic across repeats; formatting exists only inside rejection
   reasons.
2. Same-class totality gap closed: `legal(non-dict state, …)` raised
   `AttributeError`; it now returns `(False, "state must be an object")`.
3. Regression coverage added to `bin/check_ten_fronts.py`: mixed-key hostile
   moves in both signal and commit phases (`{"signal": "ok", 1: "x"}`,
   `{1: "x", "2": "y"}`, `{None: 1, ("t",): 2}`, commit-phase equivalents), plus
   a six-key-type matrix sweep asserting every probe returns `(False, str)`
   without raising and names the rule.

Checker hygiene correction: the inline `FORFEIT_ENTRANT` generator wrote an
executable script into the checker's OS-temp directory. It is replaced by the
claimed repo file `entrants/ten_fronts_forfeit_fixture.py` — deterministic,
network-free, model-free, argparse-restricted to the three sanctioned negative
modes (`abuse-signal`, `oversize-signal`, `bad-sum`). The checker now writes only
ordinary ephemeral transcripts under its self-cleaning temp directory.

## Changed paths (exact, complete)

1. `arena/games/__init__.py` — registry entry `ten_fronts -> arena.games.ten_fronts`
2. `arena/games/ten_fronts.py` — new engine: 10 fronts, 100 troops, 20 rounds, public front values 1–5 drawn once at setup; two-phase round (signal → commit) with hidden pending slots; reveals only when both seats commit; tie pays zero; strict exact-key moves; bool never accepted as int; hard move bound 80; integer-only canonical state; total fail-closed `legal()` including mixed-key and non-dict-state handling
3. `entrants/ten_fronts_model_harness.py` — process-owned inference with strict exact-key JSON parsing, 4096-char raw-output bound, deterministic legal fallback (largest-remainder over value weights), response-digest-only notes, token screen mirrored from the engine
4. `entrants/ten_fronts_forfeit_fixture.py` — NEW claimed forfeit fixture (replaces the checker's executable-in-temp pattern)
5. `bin/run_agentwars_ox_match.py` — ten_fronts seat pair + scores path in the tool-denied Ox match runner; agent description "Tool-free AgentWars decision entrant."
6. `bin/check_ten_fronts.py` — 11-section deterministic contract checker; now includes mixed-key regression cases, the key-type totality sweep, and fixture-based forfeit matches
7. `bin/verifier_snapshots/baa77c4dcd746081738dabcdbfc7882432d182dd88a3f596828cd969f9c960f6.json` — byte-exact source snapshot of the corrected referee under its engine digest
8. `verify.py` — regenerated single-file verifier embedding four engine versions (three pre-existing tracked snapshots plus the corrected current digest); `DEFAULT_ENGINE_DIGEST` repointed to `baa77c4d…`
9. `matches/agentwars-ten-fronts/summary.json` — truthful offline summary for the scripted pairing on the corrected engine
10. `matches/agentwars-ten-fronts/ten_fronts/7000-0/e16ac35d43eb3b47.diagnostics.jsonl` — unhashed diagnostics (latency)
11. `matches/agentwars-ten-fronts/ten_fronts/7000-0/e16ac35d43eb3b47.jsonl` — hash-chained offline receipt on the corrected engine
12. `AGENTWARS_TEN_FRONTS_RELEASE.md` — this document

No other file is dirty or modified.

## Superseded artifacts removed (record before deletion)

These untracked generated outputs from the pre-correction engine were removed
after their identities were recorded here; none were tracked prior proof:

| artifact | id / digest |
|---|---|
| verifier snapshot | `84fa51c80fdd5aa43638146a7f83acaf96676aa724158acd0cb019aba1178486.json`, file sha256 `bbf110f83939e52d24deca51e0a9df90eb905c2b2003a4cafb397660cfc2d091` |
| offline transcript | match `e16ac35d43eb3b47`, chain head `0a3a7f0f33b1e43e84ac385d71379aa13ae8d7500f79d366751e6c3a063e779f`, file sha256 `bfb9e5fe3bf7a25b1bfc943b67cc4bf2789fe83f9a82a621ee7d792d03961954` |
| diagnostics sidecar | file sha256 `cce510705c10060dc1242568d2f69a4bcefd9274bf26504efac2a4e71b355912` |
| summary | file sha256 `cd1907d2423181f4b222572bf6a83279baf2dfc0feded175ce9461a140abcbef` |

The replacement transcript carries the same content-addressed match id
(`e16ac35d43eb3b47` = digest of game + seed + entrant names) with different bytes
and chain head, refereed by the corrected engine.

## Engine and receipt facts (current)

- Engine digest: `baa77c4dcd746081738dabcdbfc7882432d182dd88a3f596828cd969f9c960f6`
- Offline receipt match id: `e16ac35d43eb3b47` (game `ten_fronts`, seed 7000)
- Chain head: `e0f90384b6cebaa22d230a389026581fc1ad11fcd4596a6c2f255b60b4ff13e4`
- Transcript sha256: `761329826c2e43970bcc501cb3816ea101935ea337715aa80aa12db1301d4de4`
- Result (recomputed = recorded): winner seat 0 "Stub Iron Front", `ten_fronts_score:319-226`, 80 moves, decisive
- Per-seat move-source counts (from transcript notes): both seats `fallback=40`, `model=0`, `scripted=0`, `other=0` — the stub backends emit prose by design, strict parsing rejects it, and the deterministic fallback plays all 80 moves. Both seats are truthfully fallback-only.
- Truth label: `scripted_offline_stub_pairing`; entrants declare `execution_claim=scripted`, `claimed_model=stub:v1|stub:v2`; header attestation `model_attested=false`, `execution_claims_attested=false`

## Validation ladder (exact commands, final tree)

| command | result |
|---|---|
| direct mixed-key signal probes | PASS — `{"signal":"ok", 1:"x"}` → `(False, 'unexpected keys during signal phase: [1]')`; `{1:"x", "2":"y"}` → `(False, … ['2', 1])`; no exception |
| direct mixed-key commit probe | PASS — `{allocation:[…], 1:"x", "k":2}` → `(False, 'unexpected keys during commit phase: [\'k\', 1]')`; non-dict state → `(False, 'state must be an object')` |
| `python bin/check_ten_fronts.py` | PASS — 11 sections, incl. mixed-key regressions, fixture-based forfeits, old-receipt compatibility, mutation-sensitive negatives |
| `python bin/selfcheck.py` | PASS — 23/23 checks |
| `python bin/check_fantasy_games.py` | PASS |
| `python bin/check_agentwars_scale.py` | PASS — 18 replay-verified matches (first attempt failed against the stale standalone verifier built before the engine correction; re-run after snapshot+rebuild passes) |
| `python bin/build_verifier.py --snapshot-current` | snapshotted 15 files → `bin\verifier_snapshots\baa77c4d….json` |
| `python bin/build_verifier.py` | wrote verify.py — 15 engine files, 4 engine versions, 384 KB, current digest `baa77c4dcd74…` |
| `python bin/build_verifier.py --check` | conformance 43/43 transcripts agree (package vs single-file verifier) |
| `python verify.py matches/agentwars-ten-fronts/ten_fronts/7000-0/e16ac35d43eb3b47.jsonl` | VERDICT: PASS (all 8 checks; recorded == recomputed) |
| `python verify.py matches/agentwars-fantasy/fantasy_redraft/9600-0/8d161a470a12b0c3.jsonl` | VERDICT: PASS — registering ten_fronts strands no published fantasy receipt |
| `python -m py_compile arena/games/ten_fronts.py entrants/ten_fronts_model_harness.py entrants/ten_fronts_forfeit_fixture.py bin/run_agentwars_ox_match.py bin/check_ten_fronts.py` | clean |
| `git diff --check` | clean (exit 0) |
| `git status --porcelain=v1 -uall` | exactly the changed paths above |

Final-tree proof: `matches/agentwars-ten-fronts/` contains exactly one Ten Fronts
transcript (`e16ac35d43eb3b47.jsonl`) plus its diagnostics sidecar, and no
`84fa51c8…` snapshot exists anywhere under `bin/verifier_snapshots/`.

## Proof boundary

The verified receipts prove: the transcript is unaltered since written (hash chain recomputed); the opening position follows from the recorded seed; every move ruling reproduces under this engine's rules; every position follows from the previous one; the recorded winner follows from state, not from any entrant's claim.

They do NOT prove: which model produced any move (the engine never contacts a model; `model_attested=false`); wall-clock events such as timeouts, which are recorded facts about the machine the match ran on. The offline receipt additionally is **not** a model-played match: both seats are declared-scripted stub pairings whose moves came entirely from the deterministic fallback. Provider identity and execution provenance remain unattested everywhere.

## Next step (controller-owned, separate lane)

A true live Ox entrant run remains controller-owned and was not executed here:

```
python bin/run_agentwars_ox_match.py --game ten_fronts --seed <seed> --out <dir> --json-out <summary>
```

It requires the `opencode` CLI on PATH with provider auth, runs both seats through `entrants/ten_fronts_model_harness.py` with all tools denied, exits 2 if either seat ends fallback-only, and labels any result `model_influenced_unattested` at best. Any such receipt must be validated with the same ladder before publication.
