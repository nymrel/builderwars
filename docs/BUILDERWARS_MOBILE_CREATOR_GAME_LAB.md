# BuilderWars mobile Creator Game Lab

Status: **local read-only launch candidate; no creator game admitted**.

The mobile Build and Learn destinations now expose one source-reviewed
declarative creator-game candidate without exposing a code-upload or execution
surface. Signal Siege is compiled from the canonical creator-game registry,
manifest, and deterministic replay into
`mobile-arena/data/creator-game-lab.v1.json`.

## User experience

- **Build** shows the exact held candidate, fixed rule family, bounded rounds,
  allocation budget, weighted fronts, deterministic replay result, and four
  visible authority denials.
- **Learn** explains the eight separate admission gates between valid data and
  an admitted exhibition.
- A missing, malformed, rehashed, or cryptographically unverifiable snapshot
  withholds both projections. The app fabricates no fallback game or adoption
  claim.
- The current service worker caches the exact snapshot for offline inspection.

The lab is an education and source-inspection surface. It has no manifest
editor, upload, code field, runtime selector, queue action, provider pairing,
publication action, or ranking action.

## Source and integrity contract

`bin/build_mobile_creator_game_lab.py`:

1. loads the source-controlled held registry;
2. reuses the trusted declarative manifest, registry, and replay validators;
3. requires exactly the reviewed Signal Siege v1 candidate;
4. requires the registered manifest and replay SHA-256 digests;
5. requires a deterministic replay PASS with every model, provider, runtime,
   harness, execution, publication, and ranking authority false; and
6. emits one canonical projection plus its digest.

The browser adapter pins that exact projection digest in executable source,
recomputes it with Web Crypto, validates exact nested fields and bounds, and
rejects internally consistent but unreviewed rehashes.

## Local verification

```bash
python -B bin/build_mobile_creator_game_lab.py --check
python -B bin/check_mobile_arena_creator_game.py
python bin/check_mobile_arena_exchange.py
python bin/check_mobile_arena_browser.py
python bin/check_mobile_arena_performance_budget.py
```

The dedicated adversarial gate attacks authority inflation, unknown rule
families, code-shaped fields, external URLs, replay drift, gate removal,
admission promotion, ordinary digest tampering, reviewed-pin bypass, missing
source, and unavailable SHA-256.

## What this does not prove

- an external creator used the SDK;
- creator identity, authorship, license, asset provenance, or moderation review;
- an admitted exhibition, sanctioned runtime, model play, community result,
  ranking, publication, deployment, or creator-market demand;
- public arbitrary-code isolation; or
- protected launch authority.

The governing creator-game security and admission contract remains
[`AGENTWARS_CREATOR_GAME_SDK.md`](AGENTWARS_CREATOR_GAME_SDK.md).
