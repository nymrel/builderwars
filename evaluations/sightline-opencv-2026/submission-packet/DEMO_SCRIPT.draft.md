# Sightline Demo Script — Draft, Not Submitted

Target duration: approximately three minutes, below the five-minute competition maximum. The current cut is a silent, English-captioned recording of the functioning local walkthrough. It is a **local evidence cut**, pending independently verified AWS runtime evidence and final submission review.

## Opening — Start with the user's broken journey

Show two actual screenshots of the tracked BuilderWars Arena: the expected featured receipt and the same view after a controlled missing-receipt fault. The page still responds. Its proof is missing.

Say or caption: “The page still loads, but the featured receipt has disappeared. This controlled fault uses the real tracked BuilderWars interface.”

## Detect and decide — Show the OpenCV evidence

Click **Inspect with OpenCV 5**. Run the existing real OpenCV 5.0.0 adapter, not a test double. Show the measured connected components, changed-pixel count, findings digest, and `request_human_approval` decision.

Explain that absolute differences, thresholding, and connected components are deterministic computer vision, not model inference. The known injected fault supplies the cause; pixel evidence alone does not prove the root cause of an unknown defect.

## Enforce approval — Show the failed attempt first

Click **Try restore without approval**. Require rejection. Show identical before/after screenshot hashes. The page does not change.

Then check the explicitly labeled demo-operator approval box. The receipt must identify `actor=automated_demo_operator`, `human_approval_observed=false`, and `production_authority=false`.

Say or caption: “This recorded event is scripted for the demonstration. It grants one restore of the injected DOM property in this temporary browser. It is not a human approval or a production authorization.”

## Perform the bounded demo action — Keep the claim narrow

Click **Apply approved local fixture restore**. The separate demo controller consumes the one-use candidate-bound event and restores only the injected visibility property. `SightlineAgent` retains `execution_authorized=false` and has no write operation.

Show the restored screenshot with status **restore applied, not verified**. Do not label the outcome successful yet.

## Verify — Measure the outcome

Click **Verify the fresh outcome**. Capture a new screenshot and compare it against the original baseline with the same OpenCV thresholds and policy.

Require zero retained findings, `accept_no_material_change`, and a screenshot hash identical to the baseline. State that this proves this exact controlled fixture at this viewport, not production accuracy or general autonomous remediation.

## Retain failures and measurement limits

Show three actual handler rejections: malformed PNG, dimension mismatch, and compressed expansion with oversized IHDR dimensions. Each is a `ValueError`; do not describe it as an HTTP response or AWS error.

Keep the prior fragmented-materiality false negative, mobile below-fold framing mistake, reversed synthetic polarity, and compressed-PNG expansion defect in the record. Explain their fixes without dropping failed attempts from the narrative.

Keep measured scopes separate:

- Merged Stage 1 hosted evidence: 35 tests, 3 generated cases, 2 failure controls, and 24 browser executions across Chromium and Firefox.
- Current-main local Firefox rerun: 12 cases across six workflow types and two fixed viewports, 10 true positives, 2 true negatives, 0 false positives, and 0 false negatives.
- This new walkthrough: one injected fault, one temporary DOM restore, one fixed viewport, and a scripted demo-operator event.

These results do not establish representative user traffic, device coverage, semantic correctness, unknown root-cause diagnosis, or production reliability.

## AWS — Use actual execution evidence or state the gap

The current local cut explicitly says **AWS execution remains unverified**. Source packaging and Lambda compatibility do not satisfy the organizer's meaningful-AWS-component requirement.

An AWS segment may be added only after an authorized run is verified. Show a sanitized runtime receipt with exact source and dependency hashes, input hashes, actual returned findings, AWS runtime identity, and retained invocation evidence. Never manufacture those fields or reinterpret local execution as cloud execution.

## Close

“See the defect. Bound the decision. Verify the outcome.”

The source and recorded artifacts remain associated with the existing Sightline entry. This recording does not itself establish a public video URL, legal acceptance, competition qualification, or Devpost submission.

## Recording and rights controls

- Use only tracked Nymrel source, original generated fixtures, and documented dependencies; retain the MIT license and third-party notices with the source package.
- Display no customer records, private source, credentials, account identifiers, private local paths, or billing screens.
- Record real browser activity and actual measurements; label the scripted operator event.
- Preserve the defective inputs and unsuccessful attempts with the fresh verified outcome.
- Freeze and review the exact submitted-materials corpus before accepting material legal/IP commitments.
