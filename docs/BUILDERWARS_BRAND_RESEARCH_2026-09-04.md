# BuilderWars Brand and Category Research

Status: **current research snapshot — 2026-09-04**

This note records the evidence behind the adopted public category architecture. It is not legal clearance, a launch claim, or proof of demand.

## What adjacent platforms prove

| Reference | Durable lesson for BuilderWars |
| --- | --- |
| [Kaggle competition setup](https://www.kaggle.com/docs/competitions-setup) | A credible competition product separates public feedback from private final scoring, supports both objective prediction contests and judged creative challenges, and gives hosts explicit access and visibility controls. |
| [OpenAI Evals](https://github.com/openai/evals) | An open framework, registry, custom eval path, and private-data option can coexist. The unit of trust is a named, versioned eval with reproducible inputs and metrics. |
| [Hugging Face leaderboards](https://huggingface.co/docs/leaderboards/index) | Model-centric results, community-managed leaderboards, official benchmark results, and programmatic access are distinct layers. BuilderWars Passport should link a person or artifact to scoped results rather than flatten them into one rating. |
| [SWE-bench Docker evaluation guide](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/docker_setup.md) | Reproducible execution environments are a prerequisite for comparable agent claims. A visually exciting arena cannot compensate for an unpinned environment. |
| [FastChat / Chatbot Arena](https://github.com/lm-sys/fastchat) | Side-by-side battles and human preference can generate participation and understandable rankings, but model serving, evaluation, and UI remain separate capabilities. |
| [Microsoft Agents League](https://github.com/microsoft/agentsleague) | Live battles, asynchronous challenges, starter kits, submissions, community participation, recognition, and multiple tracks can form one event loop. BuilderWars should make that loop persistent rather than event-only. |

## Naming collision findings

- [AgentWars.eu](https://agentwars.eu/en/) currently markets an AI-agent tournament and identifies AgentWars as an OAKZONE trade name. That makes AgentWars a poor public umbrella or sub-brand for this product.
- [Build Wars on Steam](https://store.steampowered.com/app/816240/Build_Wars/) is a released multiplayer building-contest game.
- [MultiversX Build Wars](https://bon.multiversx.com/builders-track) is a builder-focused hackathon track.

These findings support retiring AgentWars and BuildWars from new public product naming. They do **not** establish that BuilderWars is legally clear. Professional trademark and marketplace clearance remains required before material brand spend, paid promotion, merchandise, or a broad public launch.

## Why the nine-category architecture holds together

- **Arena** owns competition execution.
- **Forge** owns agent and harness iteration.
- **Games** owns playable and creator-authored formats.
- **Evals** owns scoped, reproducible measurement.
- **Leagues** owns persistent competitive structure.
- **Studio** owns creation workflows across agents, harnesses, games, and competitions.
- **Watch** owns spectator discovery and replay.
- **Academy** owns learning and progression.
- **Passport** owns portable proof and attribution.

The names describe user jobs without forcing separate brands. Their shared moat is the competition graph connecting builder, agent, harness, model claim, provider claim, resource class, game, rules, fixture, transcript, verifier, receipt, correction, and runback.

## Open-core implication

The strongest boundary remains:

- open: deterministic engine and verifier, receipt and protocol formats, local runner, SDK, starter games, and portable passport export;
- operated: official matchmaking, hosted isolation, official rankings and certification, private fixtures, abuse detection, moderation, disputes, billing, sponsorships, and enterprise leagues.

That boundary lets creators build around BuilderWars while preserving a meaningful operated network.

## Current domain evidence

Cloudflare account visibility on 2026-09-04 showed both `builderwars.com` and `builderswars.com` as active full zones. Both contained zero DNS records. Public DNS returned no A, AAAA, or CNAME records for either apex or `www`, and HTTPS probes failed at resolution. The current token could not inspect Rulesets or Worker routes.

[Cloudflare documents](https://developers.cloudflare.com/rules/url-forwarding/) that Single and Bulk Redirects require proxied DNS, and its [Single Redirect API guide](https://developers.cloudflare.com/rules/url-forwarding/single-redirects/create-api/) requires Rulesets write authority. The adopted plural redirect must therefore remain inactive until the singular origin is healthy and the required provider scope is available.

## Decision

Proceed with BuilderWars as the sole public brand and the nine adopted categories. Preserve legacy strings only for compatibility. Do not spend materially on the brand until professional clearance is complete. Do not activate the plural redirect before the canonical-host blocking check passes.
