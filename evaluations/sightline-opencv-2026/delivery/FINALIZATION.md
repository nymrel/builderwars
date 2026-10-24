# Sightline finalization record - October 24, 2026

Status: prepared local candidate; final competition requirements remain incomplete. This continues the merged BuilderWars Sightline implementation. No new application or Devpost project was created.

## Remaining release gates

| Gate | Observed status | Exact completion evidence |
| --- | --- | --- |
| AWS runtime | Not verified; no AWS CLI, profile or credentials in this execution runtime; AWS console browser returned Site Unavailable | Authorized account/role and cost envelope, observed AWS-hosted session or invocation, real OpenCV outputs and failure controls, exact source/input/dependency hashes |
| Judge application access | No working Sightline endpoint or arranged screen share established | Functional endpoint checks or organizer-confirmed live demonstration arrangement |
| Video | 167.72-second local recording prepared; no public/unlisted URL established | Judge-accessible video, under five minutes, including team, architecture, principal results and real AWS evidence |
| Devpost account | whoami returned UNAUTHORIZED / reconnect required | Reauthenticated account, existing Sightline project ID and hackathon submitted_at read live |
| Form | Authenticated custom questions unavailable | Fetch live submission requirements and answer exact required fields; never invent IDs or attestations |
| Legal/IP | Published rules reviewed; final authenticated click-through unseen | Review exact final materials, verified rights and eligibility; operator acceptance of material terms if required |
| Final submission | Unknown authenticated status; no submission performed by this work | Successful submit response plus a fresh Devpost read of submitted_at/public project URL and preserved confirmation |

## Legal and intellectual-property review

Published source: https://opencv26.devpost.com/rules (reviewed October 24, 2026).

Participants retain underlying IP ownership. Submitted proposals, reports, presentations and videos grant OpenCV and AWS independent, perpetual, irrevocable, worldwide, royalty-free, transferable and sublicensable rights. The permitted uses include modifications, derivative works, publication and commercial or noncommercial use without further attribution or compensation. Linked private assets are excluded unless themselves included in the submission with sufficient rights. Do not accept or broaden that license by treating this preparation as consent.

The same rules require necessary rights, prohibit misleading capability/results/human-review claims, exclude competition administrators/judges and their immediate households, require a designated team representative and responsibility for prize/tax documents, and limit organizer liability (including a stated aggregate USD 100 cap, subject to applicable law). Published age/platform wording is not perfectly aligned; use actual participant-facing eligibility and the live form. No unchecked eligibility or household/employment fact is certified here.

No AWS account, payment method, promotional credit, Marketplace purchase, IAM policy or billing setting was changed. CloudShell is a candidate existing-account path, not a verified deployment. AWS documents no additional CloudShell charge but standard transfer charges and charges for other resources; verify the permitted account cost envelope before use. Do not create a new account or accept AWS/credit terms to bypass missing access.

## Exact proposed material scope and rights

| Material | Basis | Exclusions / required notice |
| --- | --- | --- |
| Sightline source and BuilderWars mobile-arena source | Tracked Nymrel work under repository MIT license | Preserve MIT copyright/license; submit only the scoped source archive |
| Screenshots and walkthrough | Real loopback rendering of tracked Nymrel interface; known injected fault; original captions and annotations | No private/customer/account screens, stock media, third-party portraits, audio/music or synthesized voice |
| Report, diagram and Devpost prose | New project-specific explanatory material | No proprietary customer material, credentials or private operational records |
| OpenCV 5.0.0 / opencv-python-headless 5.0.0.93 | Dependency, not relicensed Nymrel code | Official package wheel + license notices retained; pinned hash. No dependency binary included in source archive |
| NumPy 2.3.5 | Dependency | BSD license and bundled-library notices retained from installed wheel; pinned hash |
| Playwright 1.58.0 / managed Firefox 146.0.1 | Recording and evaluation tools | Apache-2.0 / browser distribution terms; installed from official package distribution, not included in source archive |

The scoped package manifest freezes each included file by SHA-256. Changes to footage, report, source, images or cloud evidence invalidate that freeze and require a new manifest/review. This is a rights inventory, not acceptance of the competition license or an organizer determination.

## Source and evidence lineage

- Stage 1 merge: c41a83d5761dd98edf1d776686555e21ba4803b9 (PR 69).
- Main checked through GitHub: 1745c0a0cc8aaa31aaf8f67edc7765f32de6b547.
- Existing local recording revision: e46cc424229beb2d4b138772b6d56f374582be85; this local revision is retained in the source bundle/patch, not assumed to be a public commit.
- Merged hosted result: 35 tests; historical Chromium and Firefox 24 case executions across six workflow types and two viewports.
- Reproduced local extension: 39 tests, 3 generated task cases, 2 fail-closed controls; one controlled end-to-end journey.
- Current-main Firefox receipt: 12/12 cases, 10 TP, 2 TN, 0 FP, 0 FN. Historical Chromium is not called a fresh rerun.
- Walkthrough: 54 components, 62,432 changed pixels, approval requested; denied attempt does not change screenshot; scripted one-use demo approval restores a temporary DOM property; fresh verification returns zero findings and baseline-identical bytes.

No production accuracy, baseline superiority, root-cause inference, real human approval, general autonomous remediation, user time saving, cloud cost/latency, AWS execution or Devpost submission is claimed.
