# Human and agent connection review

September 5, 2026. Implementer: Astra / Codex; scope: the existing browser
connection dialog, public setup guide, and its regression tests. No provider
account, authentication backend, referee, or eligibility policy was changed.

## Observed friction and implementation

1. Entry: the existing Connect models action opened a technical form with name,
   strategy, connection details and export controls competing for attention.
   The new form starts with a plain route choice and puts optional strategy and
   attribution behind a disclosure. Built-in play needs no account setup.
2. Direct API: the old catalog implicitly selected its first model. New API
   drafts require an explicit model choice and show the catalog price before
   saving. Saved OpenRouter choices are isolated by seat; a local model label
   cannot become an automatic API choice. Reasoning options remain available.
3. Local agent: the old endpoint field gave no practical human-to-agent handoff.
   The new help provides a client-specific, previewable copy brief and links to
   `/agent-setup.md`. Its five allowed client choices are guidance, not newly
   enabled integrations. A fixed local-address button clears the old token.
4. Finish: imports remain disconnected drafts. Credentials are entered separately,
   checks never invoke models, and Use contender does not start a match. Profile
   export still warns that names and strategies are public data, not secret stores.

Initial canonical screenshots and local comparisons are retained outside Git in
`live-arena/output/playwright/connect-ux-20260905/`: `01-entry.png`,
`02-current-form.png`, `03-current-local.png`, `04-current-api.png`,
`05-guided-basic.png`, and `06-guided-local.png`. Initial and revised basic forms
were inspected together at the same 1265-by-713 viewport. The revised basic form
shows its primary save action in the initial view; the previous form did not.
These captures are design evidence, not production-adoption proof.

## Independent review and disposition

The native Claude review route requested `claude-fable-5-1`, high, plan/read-only
mode. Receipt `builderwars-connect-ux-20260905-20260905-151033-0700` completed in
213.93 seconds with `changes_requested`. Requested routing is recorded; the text
receipt does not independently attest a provider-resolved model identifier.

The reviewer found the closed-enum clipboard brief, unchanged strict profile
parser, secret clearing, subscription boundaries and non-inference checks sound.
All five findings received concrete disposition:

- Updated the two remaining legacy browser journeys to select their fixture model
  explicitly and reveal effort options. No test assertion or network guard was
  removed to accommodate the placeholder.
- Reworded the brief to verify the actual browser origin, using the canonical
  origin only as its known example. No arbitrary URL or form input is copied.
- Kept the setup live region rendered while empty, and removed the empty-region
  hiding rule rather than relying on a newly inserted status announcement.
- Restored the built-in default name from the selected opponent, including
  Wildcard, instead of always writing Tactician.
- Excluded the help-only client selector's input and change events from clearing
  the connection check. A browser regression caught the input-event half and
  now verifies that changing guidance preserves the credential and status.

## Validation scope

The Node suite initially passed 195 tests plus 10 Python native-frontier tests.
New unit checks validate both route/client enums, reject prototype/private text,
and parse every generated profile with the existing strict parser.
The new guarded browser journey exercises explicit paid-model selection,
secret-free clipboard content and fallback, keyboard navigation, narrow-screen
overflow, cancellation, address reset and separate saved seat models. It is
included in the normal browser CI gate. Provider responses in these tests are
synthetic, and unexpected external network access is blocked.

Release acceptance additionally requires the full exact-candidate CI, the
canonical static guide and changed UI, and the existing source-to-deployment
and asset comparisons. Local/native/browser tests do not prove every customer
subscription, real model inference, physical devices, or app-store publication.

The bounded frontend work does not complete the broader frontier-training goal
or turn the preceding capped chess exhibition into a four-family result.
