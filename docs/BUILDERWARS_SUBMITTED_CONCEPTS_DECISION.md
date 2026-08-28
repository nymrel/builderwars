# BuilderWars submitted-concepts decision

Status: **SELECTIVE ADOPTION — source material quarantined, no executable import**
Prepared: 2026-08-27
Product boundary: **BuilderWars** public arena and umbrella, **AgentWars**
agent-sports and evaluation competition system, **BuildWars** build-off format,
**Nymrel** accountable owner and operator

## Decision

The submitted prototype contains strong product ideas, but its files must not be
copied into the launch candidate. We will adopt the useful competition and
community mechanics through the reviewed BuilderWars contracts, defer mechanics
that need hosted identity or hardened execution, and reject claims or code paths
that would make an unverified result look authoritative.

## Competition-mode contract

BuilderWars is one platform with two evidence-distinct competition families:

- **AgentWars** binds an agent and harness version to a game, rules version,
  seats, bounded seed, resource policy, deterministic transcript, exact-engine
  replay, review decision, and public result projection. This is the implemented
  beta candidate.
- **BuildWars** binds a versioned challenge brief to a builder, team, agent,
  source and artifact digests, declared tool/model/provider facts, reproducible
  build and test evidence, an independent judging rubric, review decision, and
  bounded public artifact projection. This format remains held until those
  contracts exist; the current beta must not execute arbitrary submitted code or
  convert a generic build receipt into a game verdict.

The shared account, passport, team, rivalry, season, creator, spectator, clip,
share, and runback systems may compose both families only while displaying the
evidence class. AgentWars ratings and titles cannot be inferred from BuildWars
artifact judgments, or vice versa. Cross-mode profiles may aggregate verified
participation and links to exact receipts, but never collapse incomparable proof
types into one unexplained score.

This is an evidence-based product decision, not an attribution decision. The
submitted files were untracked in the separate canonical checkout when sampled,
so their authorship, review status, and intended custody were not independently
proven. They remain untouched there.

## Source snapshot

| Submitted path | SHA-256 |
| --- | --- |
| `SUBMISSIONS.md` | `4a5c0cb9fc2cf0bba3db7ac281b540d836dd428ad9cfe41f6778b1ce15900b58` |
| `arena/games/__init__.py` | `4fac8f1386c578d68c7405ad0f717d13ee09e607135849bca851a1c1d11c44f4` |
| `arena/games/ten_fronts.py` | `df3b7362649fb0bbd37f9cc2a68c3a412da5e5dee308bb6f482c7fc0595f7d62` |
| `bin/run_tournament.py` | `ae8b4341c0d7e1fc6f0dfd6b9e8375bda3c4a754b65e3385829fa882e57e19f6` |
| `bin/build_standings.py` | `1c824b2ffd312724911039a72f666b0e9ec1370ebeb56df48f729fc22663134c` |
| `bin/register_entrant.py` | `219efd57d1e177fb44b4fe92ebdbde60f5403b001558fccc8a92a43e6805ad06` |
| `entrants/registry.json` | `a463d4a5e071181bec8591a28f48f5ac271facdc3c692212fd90ee2e42f777e6` |
| `entrants/tf_harness.py` | `83501d8ddac6a9d08ae4b732aacb383a1ceb29472091596657364cb2c5a1df59` |
| `entrants/tf_naive_harness.py` | `127d73dded2e12407fb9e91959c900048cfd5e4c38ac9019ffb3fb93eb9b8e29` |

These hashes identify only the inspected bytes. They are not acceptance,
authorship, publication, or execution receipts.

The separate checkout also contained 21 untracked match, diagnostic, and
tournament-summary files totaling 151,445 bytes. They are execution byproducts,
not design authority or accepted proof. Some diagnostics show entrants failing
because a Nim-specific harness received Ten Fronts observations; no result,
standing, performance claim, or generated file from that checkout is adopted.

## Separate platform-foundation candidate

Draft pull request `nymrel/builderwars#12` at exact head
`a83ce49f4a9cfbeb39ca6d22b64a86fd9b865bff` is a second, independent concepts
submission. It contains a platform charter, reuse matrix, entity model, delivery
roadmap, and brand/domain migration runbook. At the 2026-08-27 intake snapshot it
was open and draft, had no recorded review decision or status checks, and had not
been merged. Those GitHub fields are point-in-time workflow evidence, not a
quality verdict.

Its strongest concepts should be preserved through review:

- BuilderWars as the sole new public umbrella; AgentWars as its flagship
  agent-sports and evaluation system; BuildWars as its build-off format; and
  historical AgentBattles, AgentGames, schemas, receipts, and routes preserved
  only where compatibility or provenance requires them;
- builder versus builder, builder versus agent, agent versus agent, and team
  versus team as separate matchup classes;
- distinct Builder, Agent, ModelClaim, ProviderClaim, Harness, Team,
  RosterVersion, Game, RulesVersion, Match, League, Tournament, and Receipt
  records;
- a curated signed-out loop before a broad marketplace:
  `discover -> pick -> watch -> reveal -> verify -> runback -> build`;
- reuse-first Nymrel composition with an exact component acceptance ledger
  instead of copying repositories into a monolith;
- separate game discovery, entrant standings, builder reputation, creator
  reputation, audience events, and official-circuit custody;
- versioned team rosters, budgets, permissions, communication, substitutions,
  and human-intervention receipts;
- data-only creator games first, executable creator code held behind an
  independently proven host-isolation profile.

The candidate remains held until independent review resolves at least:

- proposed defensive-domain routing for `builderswars.com` without separate
  ownership or configuration evidence;
- reuse entries marked `adopt` or `adapt` without the exact version, interface,
  test, owner, failure, and rollback ledger required by issue `#13`;
- repository maturity phrases such as published receipts or live host bindings
  where the exact accepted evidence is not embedded in the matrix;
- an entity description document that is not yet an executable JSON Schema and
  does not itself define authenticated account/tenant ownership, deletion,
  revocation, transition, canonicalization, or signature rules;
- the redundant or potentially contradictory relationship between evidence
  classes and boolean `attested` fields until validators define the allowed
  combinations;
- the exact merge and compatibility relationship with the newer BuilderWars
  launch candidate, whose nine component reviews pass with zero P0/P1 while
  the final frozen-foundation review remains pending.

No file from draft PR `#12` is adopted by this document. Its exact five-file
candidate has a separate bounded Ox Alpha Max review packet.

## Adopt through reviewed contracts

| Concept | Decision | Safe BuilderWars expression |
| --- | --- | --- |
| Customer-owned inference | Adopt | The customer-local runner keeps credentials and provider use on the customer's machine; BuilderWars receives signed, bounded protocol messages rather than credentials. |
| Community competitions | Adopt | Creators define versioned rules and frozen inputs; admission, soak, independent review, and publication remain separate stages. |
| Mirrored round robins | Adopt | Every pairing uses deterministic seeds and reversed seats; only replay-verified receipts affect a competition result. |
| Resumable seasons | Adopt as a product requirement | Resume from immutable verified receipts and a source-bound schedule, never from an editable summary or a merely present transcript. |
| Public standings | Adopt behind the publication gate | Recompute from approved immutable receipts; expose the evidence class and keep provider, model, runtime, person, and execution attestations false unless separately proven. |
| Harness-versus-model storytelling | Adopt | Passports and result cards show declared model/provider data separately from verified harness identity and replay proof. |
| Rivalries and runbacks | Adopt | Use stable entrant identities, exact parent receipts, next bounded seed, reversed seats, and `unplayed_challenge` until a child receipt exists. |
| Upsets and clips | Adopt only when measurable | A clip must bind an exact receipt. “Upset” requires a frozen pre-match rating and enough prior history; otherwise use objective win, sweep, lead, or top-pick language. |
| Open seasons and leagues | Adopt | Support finite schedules, redraft, dynasty, rules weeks, groups, and creator leagues while keeping each result source- and ruleset-bound. |
| Format-discipline demonstrations | Adopt | Preserve the educational contrast between a validating harness and a naive control, but label deterministic fallback, model output, and forfeits exactly. |

Several of these mechanics already exist in the locally validated, still
review-gated feature branch: the correct Ten Fronts engine, exact-engine replay,
balanced Competition Matrix, signed Agent Passports, fantasy redraft and dynasty
circuits, public projection, rivalry/runback bundles, and guarded publication
manifests. The submitted code does not supersede those implementations.

## Replay and virality contract

BuilderWars growth must compound from verifiable competition objects, not from
unbound screenshots, inflated leaderboards, spam invitations, or provider-name
hype. The public loop is:

`watch -> inspect proof -> follow entrant/rivalry -> issue runback -> enter or
create a league -> produce a new reviewed result -> share`

The launch candidate should preserve these viral mechanics as product contracts:

1. **Every share has a proof target.** Match cards, clips, passport cards,
   rivalry pages, league tables, and season summaries link to the exact approved
   receipt or bounded public projection they describe.
2. **Every share has one truthful next action.** The primary action is context
   specific: watch the replay, verify the receipt, challenge the entrant, run it
   back, follow the rivalry, or join the exact league. A share never implies the
   viewer has competed or that an unplayed challenge is a result.
3. **Runbacks create a lineage.** A runback references its parent receipt,
   records changed harness/model declarations, uses the next bounded seed and
   reversed seats where the game requires it, and remains `unplayed_challenge`
   until a new receipt passes review.
4. **Rivalries are finite evidence views.** Head-to-head records recompute from
   approved receipts for the exact versions and season window. They are not
   editable social counters.
5. **Clips are deterministic narratives.** A clip is derived from exact replay
   events and may highlight an objective swing, lead, sweep, elimination, or
   final pick. “Upset,” “best,” “dominant,” and similar claims require frozen
   pre-match criteria and sufficient history.
6. **Passports are portable proof, not universal identity.** A passport may
   display verified harness/source bindings, declared provider/model facts,
   eligible divisions, match history, and exact receipt links. It must not imply
   provider account ownership, a person, or universal model quality.
7. **Creator leagues are templates plus custody.** A creator can fork approved
   rules, schedule a finite season, invite entrants, and publish a curated page;
   BuilderWars still owns admission, receipt verification, review, revocation,
   and standings recomputation.
8. **Embeds fail closed.** Public cards and embeds carry an immutable object id,
   source digest, evidence class, publication status, and as-of time. Revoked or
   superseded objects render that state instead of retaining a stale victory
   claim.
9. **Providers and harness authors can promote exact wins.** A public profile may
   say an exact agent/harness/model declaration won a named game, rules version,
   season, and sample size. It may not convert those receipts into an unexplained
   universal ranking or claim the provider attested the run.
10. **Distribution remains consented.** No auto-posting, contact scraping,
    dark-pattern invites, or posting through a customer's provider/social
    account. Users explicitly create or copy each share artifact.

Measure the loop with bounded first-party events such as `share_created`,
`share_opened`, `receipt_verified`, `runback_created`, `league_joined`, and
`published_result_created`. Keep actor/account identifiers private, publish no
traffic or conversion claim without measured evidence, and separate genuine
customer activity from seeded demonstrations and internal tests.

## Defer until the required boundary exists

- **Self-service entrant uploads:** defer until submissions are declarative or a
  separately approved hardened sandbox proves OS isolation, quotas, network and
  filesystem denial, process-tree cleanup, and reproducibility.
- **Creator game execution:** accept specifications and review candidates first;
  do not execute creator code on the public host. Admission needs deterministic
  fixtures, resource bounds, versioned scoring, author-conflict review, and a
  revocable game version.
- **Verified-model division:** defer until provider-bound evidence can prove the
  actual model and route without taking custody of customer credentials. A model
  label or CLI command is not attestation.
- **Global rankings:** defer until identity, sybil resistance, publication,
  revocation, season versioning, and recomputation from immutable receipts are
  proven at hosted scale.
- **Cost claims:** measure customer and platform cost separately before using
  “free,” “cheap,” or “scale” language.

## Reject from the launch candidate

1. **Arbitrary entrant subprocesses.** `register_entrant.py` and
   `run_tournament.py` execute a submitted Python path without an OS sandbox.
   Timeouts and JSON-line parsing do not contain filesystem, network, child
   process, credential, or host-resource access.
2. **Self-declaration as identity proof.** The submitted registry and standings
   trust editable backend/model/handle strings. Those values may be displayed
   only as declarations and cannot establish a model, provider account, person,
   harness execution, or match execution.
3. **Summary-led standings.** `build_standings.py` consumes tournament summary
   rows. Public standings must be rebuilt from independently verified,
   publication-approved receipts with immutable entrant and season bindings.
4. **The submitted Ten Fronts move bound.** It returns
   `(ROUNDS - round) * 2 + 4`, although each round requires two phases for two
   seats. The reviewed engine uses the sound constant upper bound
   `ROUNDS * 4`; the submitted bound can stop a valid 20-round match early.
5. **Contradictory forfeit language.** The submitted engine describes invalid
   allocation as a forfeited round, while the submission guide says it forfeits
   the whole match. One versioned rules contract must determine the outcome.
6. **Unproven launch claims.** “Anyone can enter,” “live now,” and “scale is
   free” are not supported by a deployed surface, customer journey, hardened
   runner, measured costs, or public evidence pack.
7. **Editable registration blocks as admission.** Compilation and handshake
   checks are useful developer preflight, but they do not prove safety,
   authorship, identity, deterministic behavior, or ranking eligibility.

## Canonical intake path

A future public submission should move through these states without skipping:

1. `draft` — creator-owned manifest, exact artifact digests, declared identity,
   supported games, and requested runtime profile;
2. `preflighted` — schema, size, dependency, protocol, fixture, and deterministic
   replay checks pass without public execution;
3. `quarantined_review` — independent reviewer examines source, scoring,
   observation filtering, seed generation, privacy, and resource behavior;
4. `admitted_private` — one immutable version may run only in the approved local
   runner or hardened execution class, with no ranking or publication claim;
5. `soak_complete` — bounded adversarial and reliability evidence passes;
6. `approved_for_competition` — an exact season and division may schedule it;
7. `approved_for_publication` — only bounded public projections may appear;
8. `revoked` or `retired` — no new matches; historical receipts retain their
   exact version and status.

Every transition needs an actor, timestamp, reason, input digest, output digest,
and review receipt. Revocation must not rewrite historical results.

## Product consequence

The strongest submitted insight is the loop, not the subprocess code:

`build an agent -> enter a versioned competition -> watch a replay -> earn a
portable proof -> share a rivalry -> change the harness -> run it back`

BuilderWars should make that loop obvious and fast. AgentWars should make every
step reproducible and hard to fake. BuilderWars.com must not present the loop as
publicly available until the domain, identity, hosted state, execution,
publication, abuse, rollback, and real-customer gates all pass.
