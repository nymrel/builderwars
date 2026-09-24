# Sightline Limitations and Claim Boundary — Draft, Not Submitted

## Supported Claims

- OpenCV 5.0.0 is exercised in the hosted integration workflow.
- Generated missing-region, unexpected-region, and layout-shift fixtures produce the expected bounded outcomes.
- Material findings require human approval.
- The source artifact is deterministic for identical inputs.
- The AWS planning boundary is credential-free and non-executable.

## Unsupported Claims

- Production accuracy, precision, recall, or generalization.
- Representative browser, device, accessibility, or user coverage.
- Production safety or availability.
- AWS deployment, scalability, latency, or cost.
- Competition qualification, ranking, or prize eligibility.
- Automated remediation or deployment.

## Known Technical Limits

- Pixel-difference methods remain sensitive to animation, antialiasing, font rendering, and responsive-layout variation.
- Current findings cover a small set of visual-regression classes.
- Inputs must be equally sized PNG images and are limited to 1 MiB each at the handler boundary.
- The current artifact is a source package, not a deployed dependency layer or container image.
- No authenticated storage, queue, database, telemetry, or external tool is used.

## Human Control

The agent cannot apply a change. Medium- and high-risk findings return `request_human_approval`. Deployment, billing, credentials, registration, legal acceptance, and submission remain outside the current system.

## Data and Rights

Only generated fixtures and materials with documented Nymrel ownership or public-license provenance may enter the judge-facing packet. Customer data, private source, credentials, operational records, and third-party material without documented permission are excluded.
