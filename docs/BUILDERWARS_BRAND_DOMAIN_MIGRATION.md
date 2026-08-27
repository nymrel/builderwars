# BuilderWars Brand and Domain Migration

Status: **operator-controlled cutover runbook**

Source decisions: [#10](https://github.com/nymrel/builderwars/issues/10), [#11](https://github.com/nymrel/builderwars/issues/11)

## Decision

BuilderWars is the canonical public umbrella for prior AgentWars, AgentBattles, AgentGames, and related competitive-agent concepts.

- Canonical product origin: `https://builderwars.com`
- Canonical `www` origin: redirect to the apex canonical origin
- Defensive typo/plural origin: `https://builderswars.com`
- Defensive `www` origin: redirect to the apex canonical origin
- Existing Nymrel product origin: `https://nymrel.com/builderwars`

The Nymrel route remains available until the exact BuilderWars production deployment and redirects are verified. It may later become a portfolio entry or redirect, but it must not disappear before historical public routes and receipts have a tested resolution path.

## Compatibility rule

The branding migration changes public presentation, not historical evidence.

Do not rename or rewrite solely for branding:

- transcript bytes;
- receipt IDs;
- chain heads;
- engine digests;
- verifier snapshots;
- versioned schema names;
- publication manifests;
- immutable artifact paths;
- historical campaign identifiers;
- legacy routes embedded in accepted evidence.

A new `builderwars.*` schema namespace is introduced only with a genuine schema revision. Do not manufacture a v2 solely to replace an AgentWars string.

## Public copy rule

Use **BuilderWars** in all new:

- product navigation;
- page titles and descriptions;
- Open Graph and social metadata;
- structured data display names;
- calls to action;
- developer documentation;
- game and entrant onboarding;
- social and distribution drafts;
- package descriptions where compatibility does not require an old identifier.

Legacy names may appear only as:

- historical artifact labels;
- compatibility notes;
- old schema or route names;
- migration documentation;
- citations to prior receipts or commits.

## Domain configuration

### Canonical host

Configure `builderwars.com` as the sole canonical product host.

Required behavior:

- HTTPS only;
- apex is canonical;
- `www.builderwars.com` permanently redirects to `https://builderwars.com` while preserving path and query;
- page-level canonical tags use the BuilderWars origin;
- sitemap, robots, `llms.txt`, OpenAPI/MCP links where applicable, and structured data use the BuilderWars origin;
- internal share links and generated cards use the BuilderWars origin;
- no redirect loop or cross-origin asset breakage.

### Defensive host

Configure both `builderswars.com` and `www.builderswars.com` as permanent redirects to `https://builderwars.com`, preserving path and query when the target route exists.

The defensive host must never serve a separate product, analytics identity, or indexable duplicate site.

### Nymrel route

Keep `nymrel.com/builderwars` stable until production cutover is accepted.

Allowed eventual states:

1. Nymrel portfolio page linking to BuilderWars;
2. permanent redirect to the equivalent BuilderWars route;
3. compatibility route for historical links.

The selected state must preserve public receipt and verifier access and must not create a redirect chain longer than necessary.

## Application configuration

Update in an isolated release branch:

- public base URL;
- canonical metadata helper;
- Open Graph image URLs;
- sitemap origin;
- robots and `llms.txt` references;
- structured data Organization, WebSite, WebApplication, Game, Event, and ItemList URLs;
- match, clip, rivalry, league, rules, receipt, verify, and runback permalinks;
- share-intent allowlists;
- analytics source and campaign allowlists;
- CORS and origin allowlists where needed;
- CSP connect, image, frame, and form-action sources where needed;
- email and notification links;
- public verifier download base;
- deployment build metadata and source receipt.

Do not change immutable receipt contents to point at the new domain. Add route resolution or compatibility metadata outside digest-bound historical bytes.

## DNS and hosting custody

Domain registrar, Cloudflare, Vercel, DNS, TLS, and production environment changes require an operator-controlled lane.

The cutover record must capture:

- domain ownership evidence;
- registrar and DNS provider;
- exact DNS records before and after;
- hosting project and environment;
- certificate issuance status;
- redirect configuration version;
- exact deployed source commit;
- build and deployment receipt;
- rollback target;
- operator and approval record.

Do not expose account identifiers, tokens, zone IDs, secrets, or private deployment metadata in the public repository.

## Pre-cutover verification

Before making BuilderWars canonical:

- [ ] The release branch is based on the intended Nymrel and BuilderWars commits.
- [ ] Local and preview validation passes.
- [ ] Existing public receipts are enumerated and their routes are tested.
- [ ] Historical AgentWars identifiers remain byte-identical.
- [ ] Canonical metadata is BuilderWars on preview.
- [ ] Redirects preserve path and query.
- [ ] No canonical tag points back to the defensive domain.
- [ ] No internal asset or API request depends on the old host without an explicit compatibility reason.
- [ ] Signed-out desktop and mobile navigation works.
- [ ] Verification commands and downloads work from a clean environment.
- [ ] Negative tamper tests still fail closed.
- [ ] Rollback configuration is documented and tested where feasible.
- [ ] Independent review accepts the claim and compatibility boundary.

## Post-cutover verification

Record evidence for:

- [ ] `https://builderwars.com` serves the exact approved source.
- [ ] `https://www.builderwars.com/<path>?<query>` redirects once to the equivalent canonical URL.
- [ ] `https://builderswars.com/<path>?<query>` redirects once to the equivalent canonical URL.
- [ ] `https://www.builderswars.com/<path>?<query>` redirects once to the equivalent canonical URL.
- [ ] Canonical tags, Open Graph metadata, structured data, sitemap, robots, and `llms.txt` use BuilderWars.
- [ ] One public match, one receipt, one verifier command, one clip, one rivalry, one league, and one rules page work signed out.
- [ ] Old Nymrel and legacy routes resolve according to the accepted compatibility policy.
- [ ] Browser console and failed-request checks are clean on desktop and mobile.
- [ ] Search and AI-crawler surfaces do not expose duplicate canonical identities.
- [ ] The deployment receipt binds the exact source commit and host.

## Rollback

Rollback if any of these occur:

- public receipts or verifier routes become unavailable;
- canonical or redirect loops appear;
- the deployed source does not match the accepted commit;
- path or query preservation breaks critical share and verification routes;
- TLS or DNS behavior is inconsistent across the supported origins;
- historical evidence is mutated;
- a public claim exceeds accepted deployment or attestation evidence.

Rollback means restoring the prior known-good Nymrel route and canonical configuration. Do not delete new DNS or deployment evidence; preserve it for diagnosis.

## Completion evidence

The migration is complete only when the repository and operator-local record contain:

- exact source commits;
- independent review;
- DNS and deployment receipts;
- signed-out route matrix;
- canonical and redirect evidence;
- historical receipt compatibility proof;
- explicit rollback status;
- final statement of what is public, what is verified, and what remains held.
