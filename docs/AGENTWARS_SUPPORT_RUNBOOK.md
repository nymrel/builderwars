# AgentWars support runbook

Status: **local schema and drill only; no support channel, inbox, owner, on-call
rotation, response window, alert delivery, status page, or production action is
configured**.

This runbook connects the finite-league support severities to the existing
observability incident contract without creating a fake customer-support
operation. It accepts only one allowlisted issue class, an exact source commit,
a UTC timestamp, and up to eight opaque resource references. It accepts no free
text, attachment, identity, account, contact detail, prompt, raw model output,
provider token, credential, secret, or URL.

## Inspect and validate

```powershell
python -B bin/agentwars_support.py
python -B bin/check_agentwars_support.py
```

The checker builds deterministic case candidates, verifies canonical digests,
and attacks severity downgrades, submission and review claims, response-time
promises, free-text fields, incident emission, staffing, moderation authority,
malformed references, duplicates, and oversized reference lists.

## Case intake

A local case candidate contains only:

- `caseId`: opaque `awsupp_...` identifier;
- `openedAt`: UTC whole-second timestamp;
- `sourceCommit`: exact 40-character source commit;
- `issueClass`: one allowlisted league-support class; and
- `resourceRefs`: zero to eight unique opaque `awref_...` identifiers.

Severity, release posture, evidence requirements, and the lack of a response
promise are derived from reviewed source. The caller cannot choose a lower
severity or insert unstructured customer content. The result always stays
`local_unsubmitted_candidate`, with submission transport unconfigured, human
review not performed, actions not executed, and every authority flag false.

## Deterministic routing

- `sev1` holds release and new admissions for receipt integrity, secret
  exposure, provider boundary, or deletion/cleanup concerns.
- `sev2` holds the affected flow for rules/seed drift, accessibility blockers,
  fixture availability, or correction disputes.
- `sev3` continues local validation only for orientation, receipt explanation,
  or runback explanation.

The contract binds the exact finite-league support-policy digest and the exact
observability-contract digest. A future `sev1` bridge names the reviewed
`support_case_opened` event and `SUPPORT_SEV1` incident code, but the bridge is
schema-only: it emits no event and creates no incident.

## Incident procedure after protected activation

When real support exists, the staffed owner must independently:

1. acknowledge through the approved private channel;
2. preserve the exact source, opaque resource references, and redacted case
   class without copying secrets or raw customer/model content;
3. apply the derived release hold before investigating a `sev1` or `sev2`;
4. collect only the allowlisted evidence named by the route;
5. escalate privacy, security, provider-boundary, moderation, or legal decisions
   to the separately authorized owner;
6. record any correction as a new append-only candidate; never rewrite a
   receipt or standings silently; and
7. close only with a redacted resolution and cleanup receipt.

This text is a future operating sequence, not proof that a person, inbox, SLA,
incident, or escalation path exists today.

## Operator blockers

Before tester support can be claimed, all of these need separate evidence:

- approved public support channel and terms;
- staffed case owner plus on-call escalation;
- privacy, legal, moderation, and data-handling review;
- production ticket-store access controls, tenant isolation, and retention;
- tested alert delivery, status page, and incident communications; and
- measured and approved response windows.

A green local checker proves only that reviewed source can express and validate
redacted, fail-closed support candidates. It proves no customer, contact,
response, staffing, resolution, production incident, public communication, or
launch readiness.
