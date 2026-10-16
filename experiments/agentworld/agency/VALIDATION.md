# Candidate validation — October 15, 2026

This additive candidate is based on draft #82 at
`65bdfedc9e1ba22c42f87b70f593fae20cd9b81c`. All added source is under
`experiments/agentworld/agency/`. The parent experiment, its engine, its existing
evidence and the production app remain unchanged.

## Automated checks run

- Node **24.19.0**, Python **3.12.14**, Chromium **151.0.7922.173**.
- **54/54 Node tests passed**: 14 new agency tests plus the 40 existing engine,
  Hive ledger, consumer-quest and portable-evidence tests. See the retained
  [actual test output](evidence/node-tests.txt).
- **51/51 browser checks passed**: 25 each for the source page and bundled HTML on
  an authorized loopback origin, plus the no-JavaScript recovery check. The
  [browser receipt](evidence/browser-results.json) binds all six runtime/harness
  source files by SHA-256.
- Desktop and 390px mobile screenshots were visually inspected. Layout checks
  passed at 320, 390, 768 and 1280 CSS pixels. The primary choice is reachable in
  the initial 390 × 844 viewport. This is browser emulation, not phone acceptance.
- `git diff --check` passed for the final candidate.

Commands:

```sh
node --test experiments/agentworld/agency/policy.test.mjs experiments/agentworld/test.mjs experiments/agentworld/consumer-quests.test.mjs experiments/agentworld/world-evidence.test.mjs
python experiments/agentworld/agency/browser_test.py --out /tmp/builderwars-agency-evidence
```

The Node checks cover legal and deterministic actions, resource conservation,
suggestion refusal and persistence, energy recovery, delivery commitments, exact
visited-cell memory, aliasing, strict input/tamper rejection, checkpoint
continuation and the 240-action cap. An ordinary Relay replay built from the
policy's recorded actions independently reproduces the same world.

Browser checks exercise actual controls, downloads and imports, canceled
replacement, tampering/duplicate-key refusal, preservation of newer world state,
latest-file ownership under deferred reads, Stop timing and focus, explicit
incomplete caps, responsive layout and absence of external requests or script
errors. Visibility handling is tested with a synthetic event, not an actual
mobile background/resume journey.

## Concrete behavior observed

For seed 1, with no suggestion, Mara's first action is help → move east, using
one energy. Asking her to rest instead is accepted and produces a wait in place.
Asking Mara to explore is declined; the same exploration request to Kite on the
next turn is accepted. These are authored policy choices with observable effects.

The unsuggested seed-5 visit reaches the 240-turn cap with 10 of 16 supplies
delivered. It is displayed as incomplete. This is a development example, not an
evaluation of general performance or an improvement claim.

## Review and repairs

A separate agent in this session reviewed the candidate and reported no remaining
confirmed material issue after rechecking the fixes. Its independent bounded
checks covered 1,920 transitions across eight seeds, 40 replay round trips and
26 tampering refusals. It also used real loopback Chromium to verify old-first /
newer-second successful file reads, continuation labels, Stop focus/timing and a
downloaded checkpoint.

Review corrected a preview script-tag mismatch, an older-file race, and a journal
label that called continued acceptance of a prior suggestion an “own choice”.
The final browser harness covers newer-file success followed by an obsolete
failure; the separate review checked older success arriving before newer success.
Source review also corrected capped-completion wording and removed a map line
that could imply an untraversed route.

This is independent assistance within the same session. It does not fulfill
cross-team release review, the parent's outstanding review, consumer acceptance
or any model-family-specific gate.

## Limits and retained failures

The initial browser harness exposed a test-only Playwright function-return
invocation error when restoring `File.prototype.text`; it was corrected without
changing application behavior. Direct `file://` preview navigation then returned
`ERR_BLOCKED_BY_ADMINISTRATOR`. No browser policy was changed. Both the source
page and exact generated bundle subsequently passed over loopback; direct-file
execution remains unverified on this host.

No connected model, real provider call, persistent shared room, cross-visit
learning, physical phone, screen reader, cross-browser or actual-zoom acceptance
is claimed. Recorded content can be reconstructed but is not authenticated.
No merge, deployment or production journey is included. Parent #82 and this
candidate retain separate review and integration decisions.
