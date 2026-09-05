# AgentWars observability and incident contract v1

Status: executable local schema and drill contract. Not instrumented. No live
telemetry, durable sink, alert delivery, status page, on-call coverage, support
queue, production thresholds, protected-flag mutation, rollback execution, or
launch authority.

## Purpose

The BuilderWars cutover contract requires health, error, abuse, queue, latency,
publication, and deletion monitors plus an operator-readable incident path
before traffic is invited. This contract makes those categories and decisions
testable without pretending a production operations system exists.

The module is pure and in-memory. It imports no network, browser, filesystem,
database, process, provider, analytics, pager, or feature-flag client. Future
runtime instrumentation must emit this exact version or a separately reviewed
successor; unknown fields and free-form log material fail closed.

## Exact operational event envelope

Every candidate event has exactly five fields:

```json
{
  "schemaVersion": "agentwars.operational-event/1",
  "eventId": "awops_<32 lowercase hex>",
  "eventName": "<allowlisted event>",
  "occurredAt": "YYYY-MM-DDTHH:MM:SSZ",
  "properties": {}
}
```

Event ids must be unique within a window. Timestamps are valid UTC whole
seconds and cannot occur after the observation cutoff.

## Ten allowlisted events

| Event | Purpose | Exact classified properties |
| --- | --- | --- |
| `health_probe_failed` | A named system class failed a health check | `component`, `failure_class` |
| `request_failed` | A route class returned a bounded failure/latency class | `route_class`, `status_class`, `latency_bucket`, `failure_class` |
| `abuse_refused` | A security or abuse control refused a request | `control`, `reason` |
| `queue_saturation_observed` | A job-class saturation bucket was observed | `queue`, `saturation_bucket` |
| `publication_refused` | A bounded public projection was refused | `reason` |
| `deletion_failed` | A classified deletion resource did not clean up | `resource`, `failure_class` |
| `integrity_check_failed` | A digest-bound artifact failed verification | `artifact_class` |
| `secret_exposure_suspected` | Secret-equivalent material may have entered a surface | `surface` |
| `rollback_requested` | A classified trigger requested rollback review | `trigger` |
| `support_case_opened` | A redacted issue class entered support triage | `issue_class`, `severity` |

Every property value comes from a closed enum. The schema admits no URL, query,
IP, user, owner, account, runner, session, email, phone, name, cookie, token,
credential, secret, signature, prompt, output, exception text, stack trace, or
free-form support content.

## Zero baseline and in-memory window

`build_zero_baseline` names every event with count zero and records:

- `sourceStatus: no_source_configured`;
- `instrumentationStatus: contract_only_not_instrumented`; and
- every production authority flag false.

`aggregate_in_memory` validates exact schemas, uniqueness, cutoff, counts, and
derived server-failure, queue-pressure, severity-one support, and abuse-refusal
totals. Its window digest covers every input field. Modified fields, totals,
derived counts, authority flags, or digests are rejected before an incident
decision can be made.

Neither artifact is a production baseline. A zero from no configured source is
not evidence of healthy traffic.

## Deterministic incident and support drills

The local decision table covers ten outcomes:

| Outcome | Release decision | Primary response |
| --- | --- | --- |
| `NO_INCIDENT` | Continue local validation only | Retain the drill receipt |
| `SECRET_EXPOSURE_SUSPECTED` | Hold release | Disable protected flows; open security incident; assess rollback |
| `INTEGRITY_FAILURE` | Hold release | Disable protected flows; compare last-known-good evidence; assess rollback |
| `DELETION_FAILURE` | Hold release | Disable private writes; open privacy incident; prove cleanup |
| `ROLLBACK_REQUESTED` | Hold release | Disable protected flows; assemble and verify rollback evidence |
| `SUPPORT_SEV1` | Hold release | Acknowledge, reproduce, scope impact, and resolve |
| `HEALTH_FAILURE` | Hold release | Disable the affected flow and investigate dependencies |
| `ERROR_BUDGET_BREACH` | Hold release | Freeze the affected flow and capture the redacted error window |
| `QUEUE_PRESSURE` | Hold new admissions | Close new job admission and prove drain/capacity recovery |
| `ABUSE_SURGE` | Hold new admissions | Tighten or close the affected flow and route trust/safety review |

The thresholds are synthetic drill values, not production SLOs: five classified
5xx failures, one full queue or three high-saturation observations, and 25 abuse
refusals. They exist to prove exact branching and must be replaced or confirmed
from an authorized production baseline before traffic.

Every decision names severity, support routing, communication class, evidence
required, operator review, flag recommendation, and rollback recommendation.
`actionsExecuted` stays false. The module cannot mutate flags, page a person,
post a status, roll back a deployment, or contact a customer.

## Validation

```powershell
python bin\check_agentwars_observability.py
python bin\check_provider_hub.py
python bin\check_agentwars_local_launch_evidence.py
```

The adversarial gate covers all events, exact schemas and enums, malformed and
future timestamps, duplicate ids, person/URL injection, zero baseline, window
tampering, inconsistent derived counts, false authority flags, priority order,
threshold edges, ten drills, required evidence, and no-integration imports.

## Production activation boundary

Production observability remains held until an authorized source-bound release
proves all of the following without exposing secret or personal material:

1. exact deployment, environment, route, and source binding;
2. approved structured event emitters and privacy review;
3. durable sink retention, access, deletion, and tenant controls;
4. source-bound health/error/abuse/queue/latency/publication/deletion dashboards;
5. tested alert delivery, staffed ownership, escalation windows, and status path;
6. baseline-derived thresholds, false-positive review, and support coverage;
7. synthetic fault injection with alert, flag, rollback, recovery, and cleanup
   receipts; and
8. an externally verified last-known-good release and rollback target.

Until those receipts exist, “no incident,” “healthy,” “monitored,” “on call,”
and “rollback ready” are not production claims.
