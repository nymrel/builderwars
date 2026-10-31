# Portable evidence for a shared world

`world-evidence.mjs` provides one concrete integration surface for the [agent-directed world](AGENT_DIRECTED_EVOLUTION.md). It derives a portable evidence object from an original Relay Commons recording using the existing strict replay verifier, quest projector and Hive ledger. This first adapter allows another system to receive inspectable visit evidence without copying the game engine into a second proof system.

## Use

In Node:

```js
import { projectWorldEvidence } from './world-evidence.mjs';
const evidence = projectWorldEvidence(replayText);
```

The CLI accepts recording JSON on stdin and emits one JSON object. In PowerShell, from the repository root:

```powershell
Get-Content -Raw -Encoding utf8 replay.json | node experiments/agentworld/world-evidence.mjs
```

Malformed, tampered, duplicate-key, invalid-UTF8 or oversized input produces an error and no export. CLI input is bounded to 128 KiB before accumulating it. The exported function uses the existing parser's input bounds.

## Contract

Schema: `builderwars.agentworld.world-evidence.v1`.

| Field | Meaning |
| --- | --- |
| `rules` | Existing rules version used to reconstruct the recording |
| `recordingSha256` | SHA-256 of the canonical configuration and accepted actions |
| `sourceSha256` | Exact engine, ledger, quest projector and exporter file hashes |
| `replay` | Recording packed from the reconstructed configuration and actions |
| `quests` | Existing replay-derived quest projection |
| `hive` | Existing descriptive one-recording ledger with a fixed representative label |
| `boundaries` | Limits of the evidence and its interpretation |

Reformatting a recording or changing JSON property order produces the same export. The identity describes recording content, not a unique attested execution. Different accepted actions remain different evidence even when the final result is the same. Capped visits retain an incomplete final quest; crew-comparison visits have no cooperative quest completion.

A receiver should reconstruct the original replay using its supported rules/verifier and compare derived fields. It should select trusted source code independently: a hash or an imported claim does not authenticate an actor, model, provider, or verifier. Source labels remain self-declared. The export carries no authority to execute code, register an identity, promote a skill or change another system.

## Validation and remaining integration

Run the focused checks with the existing suites:

```sh
node --test experiments/agentworld/test.mjs experiments/agentworld/consumer-quests.test.mjs experiments/agentworld/world-evidence.test.mjs
```

The exporter has no network, storage, provider or ingestion interface. Destination adapters and their own acceptance evidence remain separately owned. Shared rooms, live human/agent clients, automatic capability discovery and ongoing agent reasoning require additional implementation. This portable interface is a building block for the flagship world experience and for services that create and operate additional worlds.
