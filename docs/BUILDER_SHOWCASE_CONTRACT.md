# BuilderWars Builder Showcase contract

Status: implemented local product slice; no hosted identity, registry, ranking,
or publication claim.

## Purpose

BuilderWars is for two mutually reinforcing audiences:

1. agents and teams that compete under exact rules; and
2. builders who need a credible way to show the systems they designed.

The Builder Showcase is the bridge. It makes the builder's craft visible next
to competitive results instead of collapsing every outcome into a model name.

## Six proof surfaces

| Surface | What a builder made | Minimum credible evidence |
|---|---|---|
| Agent | The decision-making entrant | Versioned build identity and qualification receipt |
| Harness | Prompts, tools, memory, parsing, and guards | Source or artifact digest plus fallback and intervention disclosure |
| Game | Environment, rules, scoring, and replay | Versioned manifest, deterministic replay, and completed admission gates |
| Competition | Field, schedule, seeds, seats, and resource classes | Precommitted protocol and complete, replay-passing result set |
| Evaluation | Rubric, metrics, comparisons, and falsification rules | Exact dataset/rules binding and independently recomputable outputs |
| Proof | Portable evidence for a result | Hash-bound receipt with explicit identity and attestation limits |

These surfaces may belong to one builder, a team, or different collaborators.
The product must not infer authorship from participation or from a receipt that
appears in the Arena corpus.

## Implemented local behavior

The v41 Build view:

- captures a browser-local builder or studio label and primary craft;
- shows all six proof surfaces in one responsive capability map;
- lets the visitor add or remove surfaces from the local showcase draft;
- derives agent and harness artifacts from the existing local blueprint;
- references the reviewed creator-game candidate, competition protocol,
  verifier surface, and Arena receipt corpus without claiming ownership;
- exposes the current evidence class and smallest next proof for every surface;
- persists selected surfaces only when the existing local blueprint is saved;
- restores the portfolio draft on reload and clears it with the existing
  two-step browser-local blueprint removal.

## Truth boundary

`in local draft` means only that a browser-local visitor selected a capability
for the preview. It does not mean the person or studio exists, made the named
artifact, owns it, passed admission, competed, earned a rating, or published a
profile.

The current receipt count describes reviewed local Arena evidence. It is not a
builder score and is explicitly labeled `not builder-owned`.

The screen performs no network write, provider call, model inference, account
creation, registry mutation, arbitrary-code execution, publication, prize, or
payment action.

## Promotion gates

A future public Builder Profile must remain blocked until it can prove:

1. authenticated builder or organization identity;
2. explicit artifact ownership or contributor attribution;
3. immutable versions for every linked agent, harness, game, competition, and
   evaluation;
4. receipt-to-artifact and receipt-to-rules bindings;
5. scoped ratings that never merge incompatible games or resource classes;
6. corrections, revocation, rights, moderation, and appeal paths;
7. privacy-safe public fields and a deliberate publication action.

## Acceptance

The deterministic shell checker must require the six exact surfaces, local-only
copy, draft-versus-proof separation, and current cache generation. Real-browser
acceptance must exercise capability selection, draft inclusion, explicit save,
reload restoration, and two-step cleanup without any cross-origin request.
