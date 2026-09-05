# BuilderWars frontier development campaign

> HYPOTHESIS - NOT ADOPTED: strategy draft awaiting independent review.

Status: draft. Version 1.0. September 5, 2026. Owner: BuilderWars project head,
Astra execution lane. Next review: September 12 or the next failed admission gate.
The operator authorized planning and implementation with Astra, Fable, Grok and
Gemini. This is a named BuilderWars campaign, not a change to studio-wide priorities.
BuilderWars remains a distinct Nymrel product. No personal-brand migration.

## North Star

Help builders create demonstrably better agents, prove their abilities in fair
competitions, and make that progress enjoyable to watch and reproduce.

Primary beneficiary: an agent/harness builder who wants reliable feedback and
credible proof of improvement. Spectators and competition creators are secondary
beneficiaries. The emotional promise is earned progress and recognition, not a
model-name popularity contest or guaranteed victories.

## Current evidence

| Claim | Class | Source and status |
| --- | --- | --- |
| Local outcome-trained policies and immutable evaluation artifacts exist | Fact | PR38 merged at 3f889f3d4630770daed334298e8d062d5ed9d30b; source rechecked September 5 |
| Initial sample scores increased on three short games, but no candidate passed admission | Fact | BUILDERWARS_SELF_IMPROVEMENT_RESULTS_20260905.md; local exploration only |
| The first six capped chess episodes produced no outcome-based parameter updates | Fact | Zero completed episodes and unchanged numeric weights in that run; not a claim about chess learnability |
| Four families can improve design by supplying different challenges | Hypothesis | To be tested through distinct contributions and decision-changing findings |
| Paying demand, retention, ranking and viral reach | Unknown | No customer or acquisition evidence established in this campaign |
| Industry-leading agents and mainstream competition platform | Aspiration | Requires external qualification; no present ranking claim |

## Observable recurring value

Proposed metric: weekly returning builders completing a verified improvement cycle.
Count distinct consented builder accounts that had a qualifying cycle in an earlier
UTC week and, in the current UTC week, submit a versioned candidate, complete the
fixed admission suite, and use its accepted version in at least one completed
non-practice match within seven days. An accepted version must beat its frozen
incumbent by the predeclared minimum effect and uncertainty rule, pass tactical,
seat and completion guardrails, and remain within its declared resource class.

Exclude staff, fixtures, bots/Sybil accounts, practice-only play, repeated receipt
imports, failed or capped comparisons, unverified providers, disqualified runs,
and unproven gains. Count a builder once per week, not per agent or game. Delay
finalizing the weekly number until the seven-day use window closes. Example: one
returning builder improves three agents and uses two; this contributes one, not two
or three. A first-time builder is an activation indicator, not a returning builder.

Data source: PLANNED; account/version/admission/match joins are not yet a live
metric. Baseline: unknown. No numeric growth target until an observed activation
baseline and acquisition channel exist. First milestone: verify a consented
compare-cycle cohort, including retained versions.
Weekly measurement, with no growth claim until the source is independently checked.
Retain/reject cycles are still valuable feedback and reported separately, not
misrepresented as improved agents.

Leading product indicator, also PLANNED: distinct returning external builders
completing a replayable compare cycle, retain or promote, with explicit denominators
and UTC-week deduplication. It measures useful feedback before proven gains exist;
never label it improved agents or substitute it for admission.
Temporary engineering proxies: independently replayable completed experiments,
measured tactical-error rate, completion rate, and qualified candidate admissions.
Retire these as product-value proxies when consented account-to-match joins and
duplicate/exclusion handling are verified on real users. Keep them as diagnostics.
Countermetrics: false promotions, held-out regressions, unexplained illegal moves,
completion failures, p95 move latency, compute per match, consent failures, and
creator/player complaints. A trivial game or weak opponent can game improvement:
freeze qualified opponent pools, audit starting strength and retain absolute
strength floors as well as relative gains. No payment or reward for raw match volume.

## Value loop and moat hypotheses

Play -> capture an attributable error -> practice on permitted training cases ->
change a versioned harness/policy -> test against frozen opposition -> promote or
retain -> replay and challenge -> collect new errors without leaking admission data.

Compounding assets could be trustworthy version histories, reusable competition
adapters, diverse qualified opposition, builder reputation, and creator communities.
These are moat hypotheses, not proven network effects. The hosted trust service
must earn its role even when formats and local verifiers are portable.

## Trust invariants and anti-goals

- Separate raw-model, search/tool-assisted, and learned-policy divisions.
- Record requested model separately from actual provider-resolved identity;
  declare absent identity/cost evidence rather than inferring it.
- Learning belongs to an explicit artifact: prompts, memory, search, tools, or
  local parameters. Repeated inference does not retrain a provider's base model.
- Freeze versions within a ranked match/tournament. No self-editing referee,
  hidden retries, fake audiences, fabricated training gains, or evaluation leakage.
- No unsupported subscription reuse, secret transfer, uploaded arbitrary-code
  execution, new paid infrastructure, hidden cloud tournaments or outbound posts.
- Human games, creator evals and fantasy leagues enter through typed adapters;
  do not build all categories before the competitive feedback loop works.
- No claim that this charter supersedes Nymrel or current commerce obligations.

## Three-, five-, and ten-year direction (aspirations)

Three years: builders routinely publish portable, independently reproducible
agent improvement histories and compete in well-defined game/evaluation divisions.
Five years: a creator ecosystem runs leagues and useful real-world competitions
with reliable containment, attribution and public rules.
Ten years: a durable cross-provider institution for competitive agent capability,
with external scrutiny and accessible human/agent participation. No promise of
market leadership, model progress, financing or a particular launch date.

## Economics and adoption

Wedge: a builder-owned comparison report with named frozen opposition, both-seat
results, referee replays, version custody, resource limits and retained failures.
Spectator before/after challenges render that report rather than substitute for
its evidence. Draft social assets only;
publication needs the existing exact authorization. First distribution proof is
consented testers completing and repeating the loop, not impressions alone.
Potential paid value: hosted compute, private leagues and managed evaluation.
Prices and margins are unproven. Use current local capabilities first; measure
provider usage when available, never equate subscription access with free compute.
Stop expansion if running costs or validation burden exceed evidenced user value.

## Four-family roles and execution contract

| Family / surface | Bounded responsibility | Required return |
| --- | --- | --- |
| Astra / Codex | Own architecture, implementation, tests, integration and final evidence reconciliation | Commits, independent checks and exact limitations |
| Fable / Claude | Refute charter, learning architecture and later exact implementation diff | Scored critique, blocking issues, validation needed; no source writes |
| Grok / Cursor | Challenge spectator loop, differentiation and opportunities for gaming claims | Three concrete failures, smallest replayable product experiment; no posts or source writes |
| Gemini / Antigravity | Challenge evaluation validity and transfer across games | Fixed-opponent/tactical measurement design, contamination traps, disproof tests; no source writes |

Catalog availability and a requested argument are not proof that a model answered.
Store receipts and completed outputs, including failures. Use provider-owned routes;
no impersonated reviewers or silent substitution. Parallel read-only reviewers are
independent; only Astra writes this worktree. Findings require owner reconciliation,
not a majority vote. An unavailable review route does not halt disjoint local tests.

Claim: codex-builderwars-four-frontier-20260905. Worktree:
C:/Users/johns/Desktop/BuilderWars-brand-architecture-20260904.
Scopes: live-arena, docs, .agent. No-touch: referee rules, production config, DNS,
credentials, stores, other repositories and another agent's claimed files.
Resource anchors: portfolio-control/AGENT_RESOURCE_MAP.md,
AGENT_RESOURCE_INDEX.json, knowledge-hub/AGENT_ACCESS.md and
tools/resolve_knowledge_bundle.py --repo BuilderWars --risk-class high
--topic "frontier self improvement"; tools/agent_harness_runtime.py when needed.
One finite consult per specialist, maximum five minutes, one correction only for
material unresolved findings. No persistent reviewer process. Keep claim liveness
near 60 seconds; stop for an actual ownership collision or protected action.

## Finite phases and acceptance

1. **Strength measurement, next 1-2 slices.** Entry: PR38. Add fixed tactical
   opposition and independent immediate-win/avoidable-loss measurements, both
   seats, capped-game invalidation and reproducible reports. Tests must catch a
   deliberately weak candidate. Do not alter promotion based on nicer scores.
   Disproof: the grader cannot distinguish known correct and incorrect tactics.
2. **Versioned frontier harnesses, next 2-3 slices.** Freeze provider/model/effort,
   prompt, memory and tools. Build play/error/practice/candidate records with an
   authoritative attempt ledger and separate train/development/admission partitions.
   Public tactical fixtures and symmetry/history-equivalent positions are
   development data. Reserve final positions and opposition behind separate
   custody; deny practice access and pre-register repeated-attempt error control.
   Commit before a run, freeze during it, and retire spent final suites. Hidden
   seeds alone do not certify generalization.
   Entry requires phase 1 measurements. Exit: a recorded version cannot mutate
   mid-match; invalid identity, budget, replay or contamination fails admission.
   No unsupported credentials or uploaded arbitrary code.
3. **Demonstrated improvement.** Pre-register a finite experiment before inference.
   Require at least two game families with repeatable gains against non-random
   frozen opponents, both-seat results, uncertainty, completion and tactical vetoes,
   and equal declared compute class. Retain when evidence fails; one diagnostic
   revision, then change the approach rather than grind the same holdout.
4. **Opt-in product experience.** Entry: accepted artifacts and ownership isolation.
   Implement train/compare/cancel/version-select/rollback and truthful source-bound
   playback. Verify responsive browser UX, accessibility and recovery. Physical
   devices, store submission and live credentials are distinct gates.
5. **Exhibition and creator proof.** Run a consented, bounded four-family event only
   with eligible routes and explicit inference limits. Publish nothing automatically.
   Exit: attributable replays, honest comparison/share drafts and one safe typed
   creator-adapter example. No ranking or viral claim from a single event.

Planning horizon: a first measurable vertical slice over the next few days, a
tester loop over several weeks if gates pass, then externally qualified expansion.
Timeboxes are review points, not promises. This goal remains active after a first
PR and is not complete until the delivery gates in the tracked goal are evidenced.

## Risks and decision filter

High risk: weak-opponent overfitting; counter with frozen diverse opposition and
fresh final admission. High risk: correlated model reviews; assign independent
questions and verify claims. Medium risk: spectator complexity; test one readable
before/after challenge. High risk: provider costs/custody; use explicit limits and
eligible routes. Medium risk: long-game sample cost; start with measured tactical
and completion gaps before scaling training volume.

Every next task must name the beneficiary outcome, enabling gate, smallest
disproof test, trust boundary and displaced work. Stop work that only raises an
internal activity counter. Do not borrow unrelated studio capacity without a
bounded task and current ownership evidence.

## Review and ruling

Astra drafter self-assessment (not independent acceptance), in rubric order:
4, 4, 4, 4, 4, 4, 5, 3, 4, 5 = 81/100. Product economics and metric baseline remain
unproven. Fable, Grok and Gemini returns and owner decisions will be stored in
FRONTIER_COUNCIL_RESULTS.md; missing/failed calls are not completed reviews.
Fable scored the original draft 62/100 and requested changes. Owner accepted a
builder-first report wedge, removal of the unsupported growth target and a retain-
inclusive leading indicator. Gemini and Grok challenges refine contamination and
replay controls. No scores are averaged; the revised strategy remains draft until
reviewed as revised. Review value is a concrete changed decision or evidence-backed
no-change ruling, not reviewer count. No repeat council merely to obtain approval.
The operator-authorized first implementation proceeds.

## Change log

- September 5: drafted from PR38 evidence and operator's four-frontier directive.
- September 5 operator correction: prioritize mature open-source game engines and
  actual frontier-model competition on chess/complex games now. The bounded
  numeric learner attempt is stopped, with incumbents retained. Chess exhibitions
  may proceed independently of failed numeric improvement; engine-assisted play
  must disclose its assistance and cannot claim provider-weight training.
  See `FULLGAME_DEVELOPMENT_CHECKPOINT_20260905.md`.
