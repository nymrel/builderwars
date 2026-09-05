# AgentWars measurement contract v1

Status: executable schema contract. Not instrumented. No live source, durable
counter, identity, audience, performance, retention, conversion, revenue, or
launch claim.

## Purpose

AgentWars already emits a schema-only measurement declaration with each
verified-moment share bundle. This contract moves that declaration into one
shared validator so generated artifacts, future ingestion, and launch evidence
cannot drift into different field sets or privacy rules.

The module is deliberately pure and in-memory. It imports no network, database,
filesystem, process, account, identity, provider, cookie, or analytics SDK.
Nothing in v1 sends or persists an event.

## Exact event envelope

Every candidate event has exactly five top-level fields:

```json
{
  "schemaVersion": "agentwars.measurement-event/1",
  "eventId": "awmevt_<32 lowercase hex>",
  "eventName": "<allowlisted event>",
  "occurredAt": "YYYY-MM-DDTHH:MM:SSZ",
  "properties": {}
}
```

Unknown, missing, wrongly typed, non-UTC, malformed, duplicated, or
future-relative-to-observation records fail closed.

## Six allowlisted events

| Event | Required properties | Optional properties |
| --- | --- | --- |
| `share_intent_recorded` | `match_id`, `clip_id`, `share_method` | `surface`, `campaign_id`, `creative_id` |
| `share_landing_viewed` | `match_id`, `clip_id`, `source_label`, `campaign_id`, `creative_id` | `surface` |
| `replay_started` | `match_id`, `clip_id` | `surface` |
| `replay_verified` | `match_id`, `clip_id`, `verdict` | `surface` |
| `spectator_vote_cast` | `match_id`, `clip_id`, `vote` | `surface` |
| `league_join_clicked` | `match_id`, `clip_id` | `surface` |

Enums are closed:

- `share_method`: `native`, `copy`, or `download`;
- `surface`: `receipt_card`, `share_landing`, or `match_page`;
- `verdict`: `PASS` or `FAIL`; and
- `vote`: `seat0`, `seat1`, or `runback`.

Identifiers are bounded opaque tokens. `clip_id` and `creative_id` retain their
deterministic digest-derived formats. Values containing schemes, paths, query
strings, whitespace, free-form prose, or delimiters are refused.

## Privacy boundary

The exact property sets admit no raw URL, href, query string, user id, name,
email, phone, IP address, user agent, cookie, prompt, model output, environment
value, credential, secret, token, or API key. New fields require a reviewed
schema version; ingestion must never treat unknown fields as harmless metadata.

Match, clip, campaign, creative, and source labels bind a candidate event to a
public derivative. They do not identify a person, authenticate an entrant,
prove a share, or prove that a referred visitor exists.

## Zero-baseline receipt

`build_zero_baseline(observed_at)` deterministically names all six events with a
count of zero and binds the exact contract digest. It also records:

- `sourceStatus: no_source_configured`;
- `instrumentationStatus: schema_only_not_instrumented`;
- `productionDataRead: false`;
- `durableCounterProven: false`;
- `audienceMeasured: false`;
- `performanceMeasured: false`;
- `builderIdentityAvailable: false`;
- `retentionMeasured: false`; and
- `launchable: false`.

This proves the code can express an honest zero. It is not a production baseline
probe. A live baseline later requires an authorized destination, source-bound
deployment, zero-before-traffic read, redacted synthetic write/read/delete
receipt, privacy review, and external verification.

`aggregate_in_memory` exists only to prove validation, uniqueness, observation
cutoff, and deterministic counting. Its output remains
`in_memory_validation_only` and keeps every authority flag false.

## Activation and retention boundary

The North Star definitions for WVRB, WVBC, first verified builders, time to first
verified match, runback acceptance, and four-week retention remain planned and
uninstrumented. This v1 schema intentionally carries no builder identity and
cannot calculate them. Durable identity eligibility, receipt-registry queries,
QA/demo exclusions, duplicate and pair-concentration controls, correction
handling, deletion, and cohort validation must pass before those metrics become
live.

Tagged URL retention proves transport only. A locally validated event proves
schema conformance only. Neither proves persistence, audience, sharing, replay
completion, conversion, virality, retention, or revenue.

## Validation

```powershell
python bin\check_agentwars_measurement.py
python bin\check_share_bundle.py
python bin\check_provider_hub.py
python bin\check_agentwars_local_launch_evidence.py
```

The adversarial gate covers every event, exact schemas, enum drift, missing and
extra fields, URL/person-field injection, malformed identifiers and timestamps,
duplicate ids, future events, deterministic digests, zero counts, false
authority flags, and the module's no-network/no-storage import boundary.
