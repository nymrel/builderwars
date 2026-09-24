# Sightline Terms and Registration Matrix

**Draft, Not Submitted**

Source snapshot: 2026-09-24 UTC. This is a factual preflight, not legal advice, acceptance, registration, publication, or submission authority.

Official sources:

- Rules: https://opencv26.devpost.com/rules
- Overview: https://opencv26.devpost.com/

| Area | Current official text / conflict | Operational consequence | Status |
|---|---|---|---|
| Governing terms | The rules page says final participant-facing governing-law, venue, eligibility, platform, and privacy terms will appear in the Devpost Official Rules before registration opens, and will control over conflicting overview text. | Do not register or accept terms until that final version is posted, captured, and reviewed. | **Hard gate: final controlling terms not yet available.** |
| Submission deadline | The page header and rules show **October 26, 2026 at 11:45 p.m. PDT**; overview prose says 11:59 p.m. | Use 11:45 p.m. PDT as the fail-closed external cutoff and an earlier internal cutoff. | Conflict recorded; no reliance on 11:59 p.m. |
| Reward display | Rules state up to **$12,000 cash**: $5,000, $3,000, $2,000, and two $1,000 category prizes. The overview header displays **$20,250** and 55 × $150 grants as cash, while overview prose describes 50 teams receiving a $150 cloud-compute grant. | Treat the cash pool and grant count/type as unresolved until the organizer reconciles the official pages. | Material reward inconsistency; do not represent a higher amount as verified cash. |
| Entry ownership | Participants retain rights in their entry and intellectual property. | Preserve source provenance and do not imply organizer ownership of private source merely referenced by submitted materials. | Compatible with continued private preparation. |
| Submitted Materials license | Rules describe a perpetual, irrevocable, worldwide, royalty-free, fully paid-up, non-exclusive, transferable, sublicensable license to OpenCV and AWS for submitted proposals, reports, presentations, and videos, including modification, publication, and commercial or noncommercial use without further notice, approval, attribution, or compensation. The rules distinguish those submitted materials from private source, weights, datasets, credentials, and confidential assets merely referenced unless included. | Freeze the exact submission corpus before acceptance; exclude secrets, private assets, unnecessary source, model weights, datasets, and credentials. Acceptance is a material legal/IP decision. | **Hard gate: exact license acceptance is not authorized.** |
| AWS credits and platform terms | The overview makes credits subject to AWS Free Tier terms and AWS Promotional Credit Terms. | Do not enroll, activate credits, add billing, or accept AWS terms. Continue credential-free local packaging and design-time validation only. | **Hard gate if credits/account terms are required.** |
| Eligibility and team authority | Rules require each team member to be eligible and the team representative to be authorized to submit, receive notices, and receive prizes. Age, administrator/judge conflicts, and household restrictions apply. | Verify existing account facts only; do not invent eligibility, team authority, age, employment, or household attestations. | Exact factual attestation required at registration. |
| Agent use | Fraud, manipulation, bot abuse, and hacking are prohibited; disclosed agents integral to the project are permitted. | Disclose material agent use in the final packet and preserve human approval controls and deterministic receipts. | Preparation can continue. |
| Responsible AI / safety | Organizers may reject entries lacking rights or consent, or presenting privacy, security, discrimination, surveillance, safety, harmful-content, misrepresentation, or other rule risks. | Keep provenance, consent, privacy, failure, observability, and human-control evidence in the submission packet. | Preparation can continue. |
| Winner documents | Potential winners must complete eligibility, release, and tax documentation; taxes are the winner's responsibility. | Prepare no signatures or attestations now. Escalate only if selected. | Future non-delegable gate, not a current build blocker. |
| Organizer changes | Organizers may modify, suspend, or cancel the competition and communicate changes. | Re-check final rules immediately before any registration or submission. | Monitoring required. |
| Liability | Rules include liability exclusions and an aggregate organizer-liability cap of $100. | Treat acceptance as material legal terms, not routine click-through. | Covered by the final-terms hard gate. |

## Autonomous work that remains authorized

The studio may continue source analysis, implementation, tests, offline evaluation, documentation, demo scripting, architecture work, provenance review, and preparation of a bounded submission corpus. It may also re-check official pages and prepare registration fields from verified facts.

The studio must not accept platform or competition terms, activate AWS credits, add billing, publish, register, deploy, or submit on the basis of this draft. The verifier must continue to report:

- `status=draft_not_submitted`
- `publication_authorized=false`
- `submission_authorized=false`
