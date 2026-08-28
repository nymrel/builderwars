# BuilderWars provider and release convergence

Status: active implementation candidate; protected authority closed.

Immutable parent: `3a58bd3b7f5189cd9b06a25bcfa078d2f1b92da2`.

Problem: the source policy enabled new customer-local `claude_code` execution
in `8f3c483`, while the checked-in immutable runner candidate still disables it
and the Nymrel server candidate now retains Claude only for historical evidence.
The source catalog, admission paths, generated bundle, external verifier, and
Nymrel release verifier must converge before any true-merge or release gate.

Required outcome:

- retain `claude_code` as a known historical provider identifier;
- reject it before any new executable job, prepared match, provider backend, or
  bundle execution route is admitted;
- keep historical evidence parsable and displayable;
- regenerate deterministic candidate-only runner assets from the exact child
  commit and bind every source, byte count, and digest;
- preserve all provider/model/person/runtime/match attestations as false until
  independently proved;
- do not merge, tag, publish, deploy, use a provider, mutate an account,
  provision Redis, change DNS/Cloudflare/billing, invite signup, or claim launch.

Ox Alpha review packets are read-only and use the canonical studio worker with
`opencode-go`, `max`, no fallback, and the active studio claim.
