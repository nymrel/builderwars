# BuilderWars.com domain cutover contract

Status: **HELD — operator-attested registration, no public cutover authorized**
Prepared: 2026-08-27
Candidate canonical origin: `https://builderwars.com`
Accountable company: **Nymrel**
Naming sources: GitHub issues `nymrel/builderwars#10` and `#11`

## Decision

`BuilderWars.com` is the preferred eventual public product origin because the
operator has confirmed that the domain was purchased in Cloudflare. This
reopens the earlier path decision that selected `nymrel.com/builderwars` only
while buying a dedicated domain was out of scope.

This document is a cutover contract, not a launch claim. Until every gate below
passes:

- `nymrel.com/builderwars` remains the preview or legacy surface;
- `builderwars.com` must not be described as live, configured, or customer-ready;
- no DNS, Cloudflare, identity-provider, storage, deployment, billing, or public
  account mutation is authorized by this document.

## Product and naming boundary

- **BuilderWars** is the public umbrella, canonical origin, arena, and community
  product name.
- **AgentWars** is the flagship agent-sports and evaluation competition system
  inside BuilderWars. It may remain a user-facing competition or league-family
  label, but it does not receive a separate account, canonical origin, identity
  system, or infrastructure stack.
- **BuildWars** is the builder-versus-builder, builder-versus-agent, and
  build-off competition format inside BuilderWars, not a second platform.
- **AgentBattles**, **AgentGames**, and similar variants remain historical,
  compatibility, or campaign terminology unless a later reviewed naming
  decision promotes one. They must not silently create separate public brands,
  accounts, canonical routes, or infrastructure stacks.
- Existing digest-bound AgentWars names, schema namespaces, receipt bytes,
  verifier snapshots, manifest identifiers, and historical routes remain intact
  where renaming would break provenance or compatibility.
- **Nymrel** remains visibly accountable as owner and operator in the footer,
  legal surfaces, trust documentation, support, and incident response.
- Existing `BuildWars` code identifiers may remain for compatibility. Renaming
  internal identifiers is a separate migration and must not block the domain
  cutover or imply a second platform.

## Current evidence snapshot

At the time this contract was prepared:

- domain purchase is operator-attested, not independently verified through the
  protected Cloudflare account;
- public DNS delegates the zone to `cosmin.ns.cloudflare.com` and
  `nova.ns.cloudflare.com`;
- the apex returned no A or AAAA address, `www.builderwars.com` returned
  NXDOMAIN, and bounded HTTPS probes could not resolve either hostname;
- a fresh 2026-08-27 19:36 PT DNS recheck observed the same delegation and
  unresolved apex/`www` state; this confirms only public DNS, not protected
  Cloudflare-account custody or billing;
- the proposed defensive domain `builderswars.com` was not verified as owned,
  delegated, configured, or available and is not part of the cutover unless a
  separate protected ownership check passes;
- no live BuilderWars.com route, response headers, source binding, account
  journey, traffic, customer, or revenue was proven.

DNS observations are point-in-time evidence, not proof of provider-account
custody, billing status, or future availability.

## Canonical route contract

The intended post-launch route policy is:

| Request | Required result after cutover |
| --- | --- |
| `http://builderwars.com/*` | permanent HTTPS redirect preserving path and query |
| `https://www.builderwars.com/*` | permanent redirect to `https://builderwars.com/*` |
| `https://builderwars.com/*` | canonical product origin |
| `https://builderwars.com/builderwars/*` | permanent redirect with the redundant prefix removed; never an indexable duplicate tree |
| `https://builderswars.com/*` and `https://www.builderswars.com/*` | only after separate ownership proof: permanent redirect to the equivalent canonical path and query; otherwise no claim or dependency |
| public `GET` or `HEAD` under `https://nymrel.com/builderwars/*` | permanent redirect preserving the equivalent public path and query only after the dedicated origin is fully proven |
| signed, private, account, pairing, submission, review, deletion, or support requests under the old Nymrel origin | no redirect; fail closed with a no-store terminal response after the dedicated write origin is enabled |
| pre-cutover Nymrel preview | remains available until rollback proof passes |

Use one canonical origin in HTML metadata, Open Graph data, share cards,
sitemaps, robots directives, replay links, runback links, invitation links, and
signed release descriptors. Do not serve indexable duplicate product pages on
both domains.

The dedicated host must expose only the BuilderWars product tree. Its `/`,
`/arena`, `/m/*`, `/clips/*`, `/leagues/*`, `/rivalries/*`, `/rules/*`, and
protected review/control-room paths map to the current Nymrel `/builderwars`
implementation without retaining that prefix in the public URL. Signed APIs
keep their exact `/api/builderwars/*` paths. Unrelated Nymrel company, commerce,
lead, account, scan, dispatch, and tool routes must not become reachable merely
because the same source repository or deployment substrate is reused. Host-aware
metadata, authorization, CSRF/origin checks, error handling, and tests must prove
that separation before cutover.

## Protected configuration gates

The cutover owner must record approval and source-bound evidence for each gate.

1. **Cloudflare and DNS**
   - verify the exact zone and operator account without disclosing credentials;
   - treat `builderwars.com` and any defensive domain as separate ownership and
     configuration proofs; never infer custody of one from the other;
   - export the existing DNS, redirect, SSL/TLS, WAF, bot, and cache settings;
   - define apex and `www` records, certificate mode, redirect rules, and a
     reversible rollback target;
   - keep private control-room and runner-pairing responses out of shared caches.

2. **Deployment binding**
   - deploy only an independently reviewed commit through the recorded release
     path;
   - bind deployment ID, source commit, build digest, runner assets, and public
     release descriptor;
   - prove that the bytes served at the canonical origin match the reviewed
     release rather than merely showing a READY provider state.

3. **Identity and account lifecycle**
   - add the exact production origin and redirect URIs to Clerk;
   - keep BuilderWars account authentication separate from provider
     authorization: never accept a provider password, cookie, refresh token, or
     API key into BuilderWars, and never imply that a consumer subscription can
     be federated unless that provider documents and sanctions the exact flow;
   - verify sign-up, sign-in, sign-out, session rotation, cookie scope,
     cross-site request protections, and denied-origin behavior;
   - verify the `user.deleted` webhook, account deletion, and tenant cleanup;
   - prohibit wildcard redirect URIs or cookies scoped broadly to `.nymrel.com`
     or `.builderwars.com` without a documented need.

4. **Runner pairing and recovery**
   - keep supported provider sessions on the customer's machine through the
     reviewed local client or documented browser flow, with provider-specific
     plan, workload, quota, terms, and billing limits left explicit;
   - keep exactly one signed-write origin active during cutover. The current
     request signature does not include the origin, so two independently
     stateful origins must not accept the same protocol unless a reviewed
     protocol version commits the origin or both share one atomic nonce-replay
     domain;
   - bind pairing codes, QR/deep links, signatures, callbacks, and recovery to
     the canonical origin and exact protocol version;
   - reject Nymrel-preview, localhost, encoded-path, case-variant, and alternate
     host confusion after the production origin is enabled;
   - prove revocation and recovery without retaining provider credentials in
     BuilderWars.

5. **Hosted state and abuse controls**
   - pass the isolated production-compatible Redis conformance suite for
     atomicity, expiry, poisoning, idempotency, revocation, cleanup, and account
     deletion;
   - bind environment names, peppers, reviewer keys, rate limits, and feature
     flags without emitting secret values;
   - keep arbitrary third-party code execution disabled. Entrant submissions
     stay declarative or use a separately approved hardened sandbox.
   - keep spectator predictions, votes, titles, and rivalry points zero-stakes,
     non-purchasable, non-transferable, and without monetary value. No entry
     fee, wager, betting odds, cash or crypto prize, purchasable competitive
     advantage, sweepstakes, or licensed-live-sports-data claim enters the beta
     without a separate legal, provider, and operator gate.

6. **Security and privacy headers**
   - enforce HTTPS, HSTS after rollback is proven, CSP, frame restrictions,
     MIME protections, referrer policy, and explicit permissions policy;
   - send `Cache-Control: no-store` on account, pairing, passport-private,
     submission, review, deletion, and support routes;
   - prove CORS and API-origin allowlists deny every unapproved origin.

7. **Discoverability and sharing**
   - identify BuilderWars as the umbrella in the public shell, navigation,
     metadata, social cards, and structured data; present AgentWars and
     BuildWars only as contained competition systems or formats;
   - emit one canonical URL per public page;
   - verify title, description, Open Graph and social-image bytes, sitemap,
     robots policy, structured data, and 404/410 behavior;
   - bind replay, clip, upset, rivalry, league, and runback shares to a verified
     public projection that cannot expose owner, runner, provider-account,
     pairing, nonce, signature, credentials, unrevealed private inputs, or any
     seed outside the approved public replay or teaser contract.

8. **Operations and rollback**
   - define health, error, abuse, queue, latency, publication, and deletion
     monitors before traffic is invited;
   - prove feature-flag disablement, deployment rollback, redirect rollback,
     identity-origin rollback, runner revocation, and state cleanup;
   - retain one source-bound last-known-good release and an operator-readable
     incident path.

## Required live acceptance journey

A fresh, consented customer—not an internal fixture—must complete all of the
following against the exact deployed release:

1. visit BuilderWars.com on mobile and desktop;
2. sign up, sign out, and sign back in;
3. pair a customer-owned local runner and recover it after a deliberate
   disconnect;
4. create two distinct encrypted agent and harness passports with truthful
   model/provider declarations;
5. complete one genuine model-and-harness versus model-and-harness match;
6. submit privately, replay deterministically, receive independent review, and
   publish only the bounded public projection;
7. view and share the match as a spectator, then launch an exact runback;
8. revoke the runner, remove local/provider artifacts, delete the account, and
   prove hosted cleanup;
9. execute and verify rollback without losing the signed evidence trail.

The journey must record failures as failures. A fixture, mocked provider,
self-declared model label, internal operator account, deployment dashboard, or
synthetic analytics event cannot substitute for customer proof.

## Source-bound release evidence

The final cutover pack must bind at least:

- reviewed source commit and true-merge ancestry;
- immutable runner and verifier digests;
- Cloudflare zone and DNS observation digests with secret-free configuration
  evidence;
- deployment ID, build digest, served-byte hashes, route map, redirects, and
  response headers;
- Clerk configuration checks and deletion-webhook receipt;
- Redis conformance and exact cleanup receipt;
- mobile, accessibility, performance, offline/error-state, and browser results;
- consented customer-journey receipts and redacted support/abuse checks;
- detached Ed25519 reviewer signature and rollback proof.

## Launch authority

The default state is closed or preview-only. Public cutover requires a recorded
operator authorization after every protected gate passes against the same
release. A DNS record, valid certificate, provider deployment marked READY, or
successful fixture match is not launch authorization.
