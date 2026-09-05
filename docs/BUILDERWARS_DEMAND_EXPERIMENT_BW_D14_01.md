# BW-D14-01 — qualified BuilderWars demand experiment

Status: **PREPARED_NOT_OPEN**. Bound to source
`e004aaea86c097dc8427499d0c35413fc1e704a1`. No roster, identity, contact
destination, outreach, response, session, demand, virality, conversion,
retention, revenue, or launch evidence exists under this packet.

## Decision question

After the pure seat-swap proof and bounded certification correction pass, can
a manually reviewed set of qualified external builders produce enough
voluntary, truth-informed commitments to justify a separate operator decision
about opening the six-builder product cohort?

This is a zero-spend recruitment falsification test, not a growth campaign.
It must not advertise a public product, fair benchmark, provider comparison,
model ranking, prize, live audience, marketplace, or earned virality.

## Activation boundary

The zero-row baseline decision is `HOLD_NOT_AUTHORIZED`. Before any person or
destination is researched or recorded, the operator must separately authorize:

1. opening Gate 3 `BW-D14-01` for exactly fourteen calendar days from the first
   approved outreach attempt;
2. creating a private contact map for exactly 50 frozen candidates;
3. the exact one-message and one-follow-up copy;
4. the three channel allocations and named sender;
5. the private support/incident, privacy, and deletion owners; and
6. the local storage location and deletion dates.

The authorization to author this packet is not outreach authorization. No
agent may infer approval from the project goal, an existing provider session,
a prior contact, or an internal test.

## Frozen audience

After authorization, freeze exactly 50 qualified candidates before sending:

- 36 independent agent builders who shipped or demonstrated a recent local
  agent workflow;
- 8 technical commissioners who run communities, leagues, competitions, or
  structured evaluations; and
- 6 evaluation-team leads who evaluate or purchase agent tooling.

Suggested delivery allocation is 25 individually researched emails, 15
permissioned direct messages, and 10 warm introductions. Each candidate gets
an independently generated random contact key; the key is not derived from or
hashed from identity. Qualification source and reason are stored in the
private contact map; neither identity nor destination appears in the event
ledger.
Duplicates, employees, prior contributors, unverified scraped lists, purchased
lists, minors, and candidates whose route requires accepting terms on their
behalf are excluded before the roster freezes.

## Honest offer and message requirements

Every approved message must say:

- this is a supervised, private, local, unranked fantasy-redraft alpha;
- it uses the participant's own already-configured provider route and may
  consume their quota or incur their provider-side cost;
- BuilderWars operators, services, and the observer do not receive credentials;
  an OpenRouter customer-local process may transiently read
  `OPENROUTER_API_KEY` and pass it only to its local adapter/child, but the
  value is never printed, persisted, uploaded, included in evidence, or
  disclosed to staff; other routes use customer-controlled configured CLI
  sessions;
- BuilderWars does not upload evidence, publish results, or attest
  provider/model identity or competitive parity;
- participation is optional, unpaid, carries no prize or public attribution,
  and may stop at any time;
- the live session is capped at 75 minutes; and
- there is one action: review the identity-free consent packet and volunteer
  for a session.

The first approved outreach attempt creates the Gate 3 OPEN timestamp and fixes
the experiment timezone. Day 1 is the calendar date containing that timestamp;
the experiment closes at the end of day 14 in the same timezone. Attempt every
initial invitation by the end of day 3. One follow-up may be attempted for a
non-responder no earlier than day 5 and no later than day 7. Replies are
accepted through the day-14 close. The market decision is evaluated only at
that close; only a universal safety KILL may stop the experiment earlier.

No automation, blast, enrichment upload, tracking pixel, link fingerprint,
urgency trick, or additional follow-up is allowed. The experiment spend cap is
`$0` and its staff-time cap is 16 execution hours plus four analysis/repair
hours.

## Separated data custody

Two artifacts live outside tracked source and never join:

### `contacts.private`

The separately access-controlled contact map may contain contact key,
identity, destination, qualification source, qualification reason, channel,
consent-to-contact basis, send state, and deletion due date. It contains no
provider credential, provider account detail, prompt, model output, receipt,
passport, game artifact, or session result.

### `demand-events.jsonl`

The pseudonymous ledger may contain experiment id, source SHA, contact key,
channel class, event name, timestamp rounded to the day, message version,
qualification segment, response class, commitment state, session state, and
withdrawal/deletion state. It contains no name, email, handle, phone number,
IP address, user agent, URL parameter, free text, provider, model, harness,
account, prompt, output, or credential.

The allowlisted event names are exactly `qualified_contact_locked`,
`outreach_attempted`, `delivery_recorded`, `reply_classified`,
`eligible_commitment_recorded`, `withdrawal_recorded`,
`staff_minutes_recorded`, and `scope_violation_recorded`. Existing product
measurement remains uninstrumented and non-live under
[`AGENTWARS_MEASUREMENT_CONTRACT.md`](AGENTWARS_MEASUREMENT_CONTRACT.md); this
manual ledger cannot be presented as product analytics.

## Retention and withdrawal: 7 / 30 / 90 days

- **7 days:** acknowledge a withdrawal/deletion request and delete the
  candidate's row from `contacts.private`, controlled delivery correspondence,
  every pseudonymous event/session row for that candidate, and any unneeded
  raw local session artifact within seven calendar days. Only a non-linkable
  aggregate decrement and a deletion receipt digest with no contact key or
  identity link may remain. Provider-side or participant-controlled artifacts
  are not claimed deleted.
- **30 days:** delete all remaining identities, destinations, contact notes,
  scheduling correspondence, and `contacts.private` no later than 30 calendar
  days after experiment close. The random contact keys and mapping are deleted
  with the map, making the remaining ledger non-linkable by the team.
- **90 days:** delete `demand-events.jsonl`, session-level pseudonymous
  worksheets, and receipt manifests no later than 90 calendar days after the
  final experiment decision. A source-bound aggregate decision may remain only
  if it contains no row-level data, free text, contact keys, or identity link.

An incident hold cannot silently extend these periods. Any extension requires
separate operator and privacy approval, a reason, a new deletion date, and a
bounded affected-artifact list. These private-alpha day counts do not alter or
claim production retention policy under
[`AGENTWARS_RETENTION_DELETION_ROLLBACK_RECOVERY.md`](AGENTWARS_RETENTION_DELETION_ROLLBACK_RECOVERY.md).

## Counting rules

- `frozen`: a unique, qualified candidate in the approved 50-row private map.
- `delivered`: a message accepted by the chosen channel, excluding bounces and
  blocked destinations.
- `substantive reply`: a human response that addresses the private alpha rather
  than an automated acknowledgement.
- `qualified commitment`: a qualified candidate voluntarily chooses a session
  window after receiving the disclosures. Interest, likes, link clicks, or a
  staff promise do not count.
- `valid session`: the definition in
  [`AGENTWARS_PRIVATE_ALPHA_PROTOCOL.md`](AGENTWARS_PRIVATE_ALPHA_PROTOCOL.md).

The GO threshold is eight active qualified commitments; six is the minimum
viable cohort-recruitment signal but is not GO. Denominators never exclude
negative replies, withdrawals, bounces after delivery, or stopped sessions
unless the frozen candidate was a documented pre-send duplicate or ineligible
person.

## Deterministic decision

Evaluate the market result exactly at the end of day 14. Never decide early
from a favorable count or extend the window to improve the result. A universal
safety KILL may stop collection before close. If fewer than 40 deliveries are
recorded at close, the result is `HOLD_INCOMPLETE`, never a demand KILL; do not
infer market demand from the incomplete denominator.

### `GO_DEMAND_GATE`

All must be true: exactly 50 candidates were frozen after authorization; at
least 40 invitations were delivered; at least eight active qualified
commitments were recorded; no identity crossed into the pseudonymous ledger; no
credential, provider-policy, consent, deletion, harassment, or material truth
incident occurred; spend was `$0`; and total staff time was no more than 20
hours. This GO permits only a separate operator decision about authorizing the
cohort; it does not authorize contact, scheduling, provider execution, or a
cohort OPEN timestamp.

### `HOLD_MINIMUM_MET`

Use when 50 are frozen, at least 40 are delivered, and six or seven active
qualified commitments remain at the day-14 close. The minimum signal is
recorded, but the demand gate does not pass and the cohort is not authorized.

### `HOLD_BELOW_MINIMUM`

Use when 50 are frozen, at least 40 are delivered, and four or five active
qualified commitments remain at close. One revision may change message clarity
or channel mix within the frozen 50; it may not widen the audience, change the
offer, reduce disclosure, increase spend/time, add follow-ups, reset the
evidence, or extend the fixed window.

### `HOLD_INCOMPLETE`

Use when fewer than 50 qualified candidates were frozen, fewer than 40
invitations were delivered, or the fixed timing/recording contract was not
completed at the day-14 close without a universal KILL. This is an execution
failure, not evidence of insufficient demand.

### `KILL_CURRENT_RECRUITMENT_WEDGE`

At the day-14 close, with 50 frozen and at least 40 delivered, kill when zero
through three active qualified commitments remain. Also apply a closeout-only
low-trust KILL when at least half of substantive replies rate receipt/truth
trust at 1 or 2 on the five-point allowlist, but only when every non-withdrawn
substantive reply received through the day-14 close has complete
`reply_classified` evidence. The low-trust rule is not an early-stop rule. If
fewer than 40 invitations were delivered, `HOLD_INCOMPLETE` controls and the
low-trust condition cannot produce KILL.

Before close, stop early only for a universal safety, privacy, or material
truth KILL: unauthorized contact; identity/ledger crossing; secret or
credential exposure or request; deceptive ranking, parity, provider, or model
claim; terms ambiguity; unhandled withdrawal/deletion; harassment; or a
material privacy or participant-safety incident. Reaching the staff-time or
spend cap stops further activity, but its deterministic experiment outcome is
recorded at the day-14 close rather than treated as a low-trust or market
early-stop result.

Before activation, missing authorization or an empty ledger is always
`HOLD_NOT_AUTHORIZED`, never a market KILL and never evidence of zero demand.

## Evidence and closeout

The closeout manifest records source and packet digests, authorization receipt,
the frozen-roster count (not its content), message digests, channel counts,
allowlisted event counts, spend/time receipts, deletion due dates, incident
codes, and the deterministic decision. It carries explicit false values for
public launch, virality, revenue, ranking, provider/model attestation,
competitive parity, production telemetry, and permission to contact anyone
outside the frozen roster.
