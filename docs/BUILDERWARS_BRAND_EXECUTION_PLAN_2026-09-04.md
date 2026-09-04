# BuilderWars Brand Execution Plan

Status: **ACTIVE — owner-approved direction; evidence-gated execution**

## Outcome

Ship one coherent BuilderWars product whose first useful loop is:

`discover -> pick a side -> watch or play -> inspect proof -> run it back -> enter Forge -> publish a better entrant`

The nine categories organize that loop. They are not nine independent launch projects.

## Phase 0 — canonical contract

Exit criteria:

- adopted human-readable and machine-readable brand contracts;
- legacy-name and immutable-evidence rules are explicit;
- deterministic validator rejects category, domain, or status drift;
- exact-source tests pass on a clean worktree;
- change lands through normal review without modifying frozen foundation bytes.

## Phase 1 — finish the first playable wedge

Target: one “Publish the Duel” path using the existing deterministic local exhibition and builder showcase work.

Required path:

1. land the Builder Showcase change only after its cross-platform CI failures are diagnosed and fixed;
2. expose one clear mobile entry into Arena, Watch, and Forge;
3. preserve demo, local, verified, and official states as visibly different;
4. make one replay receipt understandable without requiring the source tree;
5. let a builder produce a versioned runback without surrendering provider credentials;
6. instrument only consented, privacy-safe activation events.

Stop if the environment is unconfined, provider access is unsupported, attribution outruns evidence, or the spectator path requires fabricated activity.

## Phase 2 — canonical origin and defensive redirect

Preconditions:

- exact approved BuilderWars source is deployed and healthy on a provider-owned preview;
- `builderwars.com` apex and `www` route to that exact source with valid TLS;
- host-aware auth, origin, CSP, CSRF, and metadata checks pass;
- existing Cloudflare DNS, Rulesets, Worker routes, and rollback state are captured;
- current provider authority can create the required proxied DNS records and redirect rule.

Then:

1. make the apex canonical and redirect canonical `www` once;
2. create proxied plural apex and `www` records;
3. activate one permanent path-and-query-preserving redirect from the plural zone;
4. prove the root and a non-root path with a query on both plural hosts;
5. prove there is no redirect chain or loop;
6. preserve the pre-change snapshot and one-command rollback.

Current status: **blocked** because the canonical zone has zero DNS records and the available token lacks Rulesets/Worker-route access.

## Phase 3 — category shell

After the Builder Showcase branch is integrated, introduce a compact mobile-first category shell:

- primary tabs: Arena, Watch, Forge;
- discovery menu: Games, Evals, Leagues;
- creation and progression: Studio, Academy, Passport.

Every route needs loading, empty, error, demo, local, and verified states where applicable. Do not publish dead navigation; reserve routes until each has a truthful destination.

## Phase 4 — private read alpha

Run a finite, consented cohort only after launch, auth, privacy, deletion, support, and isolation gates pass.

Measure:

- first verified duel viewed;
- proof panel opened;
- runback started and completed;
- first entrant version published;
- week-one verified return.

Do not infer retention from repeated internal runs. WVRB—Weekly Verified Returning Builders—remains the provisional North Star until a real cohort can falsify it.

## Phase 5 — governed creator beta

Enable game, eval, and league creation only with versioned rules, fixture custody, rights review, abuse controls, appeals, and rollback. Start with a small approved catalog and one official circuit; do not open a general marketplace first.

## 6–36 month direction

- 6 months: repeatable private seasons, portable Passports, and a creator SDK with reproducible local qualification.
- 12 months: governed public circuits across coding, strategy, fantasy sports, negotiation, and mixed human-agent games.
- 18–24 months: teams, persistent rivalries, verified harness histories, third-party games, and enterprise/private leagues.
- 24–36 months: a trusted cross-provider competition graph that builders and providers cite as evidence, while official ranking and certification remain operated and governed.

## Immediate ordered work

1. Merge the brand contract and validator.
2. Diagnose and repair Pull Request #24 CI; then integrate its builder-proof UX.
3. Implement the category shell against the merged source without dead routes.
4. Establish a source-bound canonical deployment preview.
5. Complete the canonical-host blocking checks.
6. Activate and verify the plural redirect.
7. Re-run the protected tester journey and ordered launch evidence pack.
8. Open the finite private read alpha only after every protected gate passes.
