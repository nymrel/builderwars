# Sightline Technical Report — Draft, Not Submitted

## Problem

Visual regressions can leave an application functional at the protocol level while making important controls, content, or layouts unusable. Sightline turns bounded visual evidence into an auditable diagnostic decision without granting the agent authority to modify or deploy an application.

## Approach

Sightline compares a baseline PNG with a candidate PNG using OpenCV 5. It computes an absolute-difference mask, extracts bounded connected components, classifies missing, unexpected, and shifted regions, and normalizes those findings into a deterministic SHA-256 trace.

A policy layer maps the findings to one of three outcomes:

- accept no material change;
- request human approval;
- reject unbounded input.

Medium- and high-risk findings stop at human approval. The current system exposes no repository-write, configuration-change, or deployment tool.

## OpenCV 5 Role

OpenCV 5.0.0 performs image decoding, absolute difference, grayscale conversion, thresholding, connected-component extraction, and PNG fixture encoding. The hosted environment pins the official Python wheel and NumPy by exact version and SHA-256.

## Agentic Loop

1. Perception: OpenCV 5 produces typed visual findings.
2. Decision: deterministic policy selects the next bounded outcome.
3. Control: material changes require human approval.
4. Evidence: the trace records the normalized findings digest and false execution authority.

## Evaluation

The generated offline baseline covers missing-region, unexpected-region, and layout-shift cases. All three expected task outcomes pass. Two fail-closed controls cover unreadable images and dimension mismatch. The full hosted unit suite contains 26 tests.

A separate browser workflow serves tracked Nymrel-owned BuilderWars Mobile Arena source on loopback and captures controlled no-change, missing-region, unexpected-region, and layout-shift screenshots in Chromium. All 4/4 browser cases pass against OpenCV 5.0.0. Material browser cases require human approval; the receipt records zero cross-origin requests, zero console warnings/errors, no persisted PNGs, false AWS invocation, and false execution authority.

These results establish deterministic behavior for generated and controlled browser-rendered fixtures only. They do not establish public-site capture, user-traffic representativeness, production accuracy, precision, recall, or generalization.

## AWS-Compatible Boundary

The Lambda-compatible handler accepts two bounded base64 PNG inputs and returns findings plus the decision trace. It performs no network, storage-service, repository, mutation, or deployment action.

A deterministic source builder emits an allowlisted ZIP and passes its metadata through an inert AWS boundary. The boundary rejects credential-bearing environments and requires credential, deployment, and spend authority to remain false. No AWS endpoint has been contacted.

## Reproducibility

The repository documents the hash-locked CPython 3.12 environment, test command, evaluator, artifact builder, and hosted exact-head evidence. The generated artifact uses fixed timestamps, permissions, ordering, and content.

## Responsible Operation

Inputs are size-bounded and must be PNG. Invalid base64, unreadable images, dimension mismatch, excessive findings, unsafe artifact metadata, credentials, and deployment authority fail closed. Secret values are never emitted by the AWS-boundary checks.

## Current Limitations

The corpus combines generated arrays with controlled loopback browser rendering; it is not representative browser traffic. The classifier is intentionally narrow. No AWS deployment, production endpoint, user study, or competition submission has occurred. See `LIMITATIONS.md` for the complete claim boundary.
