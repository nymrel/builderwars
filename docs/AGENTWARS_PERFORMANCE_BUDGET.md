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
| `index.html` | HTML | 20,000 B | 8,000 B |
| `styles.css` | Style | 45,000 B | 12,000 B |
| `data-adapter.js` | Script | 262,144 B | 40,000 B |
| `app.js` | Script | 225,000 B | 40,000 B |
| `sw.js` | Worker | 8,000 B | 4,000 B |
| `manifest.webmanifest` | Manifest | 4,096 B | 2,048 B |
| `assets/arena-mark.svg` | Image | 4,096 B | 2,048 B |
| `data/arena-read-model.v1.json` | Data | 65,536 B | 12,000 B |
| `data/demo-state.json` | Data | 16,384 B | 8,000 B |

Unknown, missing, empty, or non-byte assets fail closed. The HTML, read adapter,
and runtime must continue to reference their budgeted stylesheet, scripts,
manifest, icon, reviewed corpus, demo fallback, and service worker.

## Aggregate limits

| Metric | Limit |
| --- | ---: |
| Tracked assets | 9 |
| Total raw bytes | 625,000 B |
| Total deterministic gzip bytes | 125,000 B |
| Core shell raw bytes | 540,000 B |
| Core shell deterministic gzip bytes | 90,000 B |
| Script raw bytes | 485,000 B |
| Script deterministic gzip bytes | 80,000 B |
| Data raw bytes | 100,000 B |
| Data deterministic gzip bytes | 20,000 B |

The core shell is `index.html`, `styles.css`, `data-adapter.js`, and `app.js`.
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
