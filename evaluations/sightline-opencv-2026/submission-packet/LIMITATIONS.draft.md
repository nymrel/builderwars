# Sightline Limitations and Claim Boundary — Draft, Not Submitted

## Supported Claims

- OpenCV 5.0.0 is exercised in the hosted integration workflow.
- Generated missing-region, unexpected-region, and layout-shift fixtures produce the expected bounded outcomes.
- A loopback-only Chromium corpus renders tracked Nymrel-owned BuilderWars source; four labeled user-flow cases produce the expected safe outcomes without cross-origin requests or persisted PNGs.
- On that four-case set only, the material-change confusion matrix is 3 true positives, 1 true negative, zero false positives, and zero false negatives.
- Material findings require human approval.
- The source artifact is deterministic for identical inputs.
- The AWS planning boundary is credential-free and non-executable.

## Unsupported Claims

- Production accuracy or generalization; the reported precision and recall apply only to four labeled loopback cases.
- Representative user-traffic, device, accessibility, or public-site coverage.
- Production safety or availability.
- AWS deployment, scalability, latency, or cost.
- Competition qualification, ranking, or prize eligibility.
- Automated remediation or deployment.

## Known Technical Limits

- Pixel-difference methods remain sensitive to animation, antialiasing, font rendering, and responsive-layout variation.
- Current findings cover a small set of visual-regression classes.
- Browser evidence uses controlled state changes on a tracked interface. Its four cases are insufficient to represent naturally occurring regressions, devices, viewport classes, or production traffic.
- Fragmented materiality uses a conservative eight-component stop threshold; broader corpus work is required to characterize nuisance-alert risk.
- Inputs must be equally sized PNG images and are limited to 1 MiB each at the handler boundary.
- The current artifact is a source package, not a deployed dependency layer or container image.
- No authenticated storage, queue, database, telemetry, or external tool is used.

## Human Control

The agent cannot apply a change. Medium- and high-risk findings return `request_human_approval`. Deployment, billing, credentials, registration, legal acceptance, and submission remain outside the current system.

## Data and Rights

Only generated fixtures and materials with documented Nymrel ownership or public-license provenance may enter the judge-facing packet. Customer data, private source, credentials, operational records, and third-party material without documented permission are excluded.
