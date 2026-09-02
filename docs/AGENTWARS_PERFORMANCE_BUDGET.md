# AgentWars Mobile Arena performance budget v1

Status: executable local-source regression budget. Not production performance,
Core Web Vitals, a real-user measurement, a service-level objective, or launch
authorization.

## Purpose

The Mobile Arena is a compact static shell, but “small enough” is not a durable
release contract. This gate measures the exact reviewed asset set and prevents
unnoticed source growth from being folded into a launch candidate.

The budget follows the same deterministic compressed-wire pattern used by the
Nymrel build gate, adapted to BuilderWars' static shell. It reads tracked files
only and uses gzip level 9 with `mtime=0`, so the receipt is reproducible. It
opens no browser, socket, provider, account, deployment, or analytics source.

## Exact tracked asset set

| Asset | Role | Raw limit | Deterministic gzip limit |
| --- | --- | ---: | ---: |
| `index.html` | HTML | 24,000 B | 9,000 B |
| `styles.css` | Style | 45,000 B | 12,000 B |
| `data-adapter.js` | Script | 285,000 B | 45,000 B |
| `app.js` | Script | 230,000 B | 40,000 B |
| `ten-fronts.html` | Route HTML | 4,096 B | 2,048 B |
| `ten-fronts-blitz.css` | Route style | 8,192 B | 3,072 B |
| `ten-fronts-blitz.js` | Route script | 20,000 B | 8,192 B |
| `sw.js` | Worker | 8,000 B | 4,000 B |
| `manifest.webmanifest` | Manifest | 4,096 B | 2,048 B |
| `assets/arena-mark.svg` | Image | 4,096 B | 2,048 B |
| `data/arena-read-model.v1.json` | Data | 65,536 B | 12,000 B |
| `data/demo-state.json` | Data | 16,384 B | 8,000 B |
| `data/creator-game-lab.v1.json` | Data | 16,384 B | 8,000 B |

Unknown, missing, empty, or non-byte assets fail closed. The HTML, read adapter,
and runtime must continue to reference their budgeted stylesheet, scripts,
manifest, icon, reviewed corpus, demo fallback, and service worker.

## Aggregate limits

| Metric | Limit |
| --- | ---: |
| Tracked assets | 13 |
| Total raw bytes | 670,000 B |
| Total deterministic gzip bytes | 132,000 B |
| Core shell raw bytes | 570,000 B |
| Core shell deterministic gzip bytes | 96,000 B |
| Core script raw bytes | 515,000 B |
| Core script deterministic gzip bytes | 86,000 B |
| Lazy route raw bytes | 32,000 B |
| Lazy route deterministic gzip bytes | 12,000 B |
| Data raw bytes | 116,000 B |
| Data deterministic gzip bytes | 26,000 B |

The core shell is `index.html`, `styles.css`, `data-adapter.js`, and `app.js`.
The lazy route is `ten-fronts.html`, `ten-fronts-blitz.css`, and
`ten-fronts-blitz.js`; it is cached for direct and offline navigation but does
not inflate the main page's core-script subtotal.
The limits intentionally leave bounded headroom; raising one requires a reviewed
contract change rather than silently normalizing growth.

The 2026-09-01 semantic read-model hardening intentionally widened only the
readable raw-source ceilings. The accepted local receipt is 258,653 raw / 39,017
gzip bytes for `data-adapter.js`, 533,622 / 86,043 for the core shell, and
478,647 / 74,158 for scripts. All transfer-oriented gzip ceilings and the total
raw/gzip ceilings remain unchanged. The added source validates channel,
rules-week, rivalry, fixture, participant, seat, timestamp, and summary
relationships before rendering; the budget change does not waive compressed
size or production-performance proof.

The 2026-09-02 Ten Fronts Blitz slice adds a separately loaded, minified local
game route while preserving the existing 660,000-byte aggregate ceiling. The
accepted 13-asset receipt is 659,604 raw / 114,065 deterministic gzip bytes;
the core shell is 563,110 / 92,825, core scripts are 497,359 / 78,969, and the
lazy route is 27,983 / 9,415. This is deliberately tight. New route growth must
be paid for by source reduction or a separately reviewed budget decision.

The later 2026-09-02 proof-inspector slice makes Replay, Build binding, and
Attribution legible at first glance while retaining every exact predicate in a
native disclosure. The prior ceiling correctly caught the readable source
growth. After review, only the `app.js` raw limit moved from 225,000 to 230,000
bytes and the total raw limit moved from 660,000 to 670,000 bytes; every gzip,
core-shell, script, lazy-route, and data limit remains unchanged. The accepted
v40 receipt is 664,908 raw / 115,238 deterministic gzip bytes; the core shell is
568,414 / 93,999, core scripts are 500,124 / 79,761, the lazy route is 27,983 /
9,414, and `app.js` is 227,725 / 37,183. This is a reviewed source-maintainability
adjustment, not a transfer-performance waiver or production measurement.

## Receipt and adversarial gate

`build_receipt` produces content hashes, raw/gzip sizes, aggregate totals,
failure attribution, contract and asset-set digests, and a deterministic receipt
digest. The checker proves:

- the real tracked source fits every budget;
- a repeated build produces the same receipt;
- missing, unknown, empty, and non-byte assets are refused;
- per-file raw and gzip overruns fail and identify their asset;
- aggregate data-gzip growth fails and identifies its metric;
- only relative asset paths enter the receipt;
- the checker imports no network, browser, database, process, or analytics
  dependency; and
- production data, network, timing, performance, user-experience, and launch
  flags remain false.

Run the human summary or inspect the deterministic receipt:

```powershell
python bin\check_mobile_arena_performance_budget.py
python bin\check_mobile_arena_performance_budget.py --json
```

## Evidence boundary

A passing receipt proves only that the exact local tracked assets fit this
declared source budget. It does not prove compression at an external CDN,
cache behavior, device CPU cost, hydration or interaction latency, LCP, INP,
CLS, network quality, availability, production browser behavior, or user
experience.

Production performance remains stage 12 protected evidence. It requires an
authorized source-bound deployment, served-byte parity, cache/header checks,
mobile and desktop lab runs, consented real-user or approved synthetic
observation, explicit budgets, observability, and a verified rollback target.
