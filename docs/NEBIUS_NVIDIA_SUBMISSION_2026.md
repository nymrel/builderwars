# Nebius × NVIDIA Global AI Hackathon — submission pack

This file is the competition-facing checklist for **BuilderWars: Open Agent Proof Arena**.
It separates repo-ready facts from facts that require a real account, credential, deployment,
publication, consent, or provider-backed run.

Official rules: https://nebiusglobalaihackathon.devpost.com/rules

## Recommended track

**Coding and Agentic Engineering** is the current best fit: BuilderWars is an agent/evaluation
system whose competition-period work adds a bounded NVIDIA-model policy-repair lane,
deterministic scoring, and replay/evidence inspection. Re-evaluate the track only if the
final demo changes materially.

## Requirement matrix

| Requirement | Repo-ready state | Submission evidence still required |
| --- | --- | --- |
| Runs on Nebius Token Factory or AI Cloud | One-call Token Factory runner targets the pinned chat-completions endpoint | A successful live receipt from the default HTTPS transport |
| Uses an NVIDIA open-source model | Default model is `nvidia/nemotron-3-super-120b-a12b`; caller may select another current `nvidia/*` catalog id | Exact live model id from the successful run |
| Working demo URL | Static judge bundle generator exists; BuilderWars public site already exists | Deploy/publish the exact judge bundle or integrated route and verify signed-out access |
| Public code repository | https://github.com/nymrel/builderwars is public | Keep the submitted commit reachable through judging |
| Open-source license | Root `LICENSE` is MIT and README links it | Confirm Devpost detects it on the submitted repository |
| README setup guidance | Root README links this lane and exact live command | Keep instructions synchronized with submitted head |
| Demo video ≤ 3 minutes | Shot list below is ready | Record and publish a public YouTube video |
| Nebius/NVIDIA feedback | Capture template below is ready | Fill only from actual onboarding and live-use observations |
| Significant-update explanation | Draft below is ready | Replace commit placeholders with exact submitted head |
| Registration/submission | Not a repo fact | Devpost account/agreements/form submission remain separate |

## Exact live execution

The default live command performs **one** provider call and refuses to run without an
explicit spend-authorization flag:

~~~
export NEBIUS_API_KEY='...'
python bin/run_nebius_policy_repair_live.py   --allow-billable-call   --model nvidia/nemotron-3-super-120b-a12b   --receipt-file nebius-live-evidence/receipt.json   --report-file nebius-live-evidence/index.html   --demo-dir nebius-live-evidence/site
~~~

The public receipt contains hashes, endpoint/model identity, integer duration, bounded-call
configuration, deterministic checks, and runner-observed runtime flags. It does **not** retain
the credential or raw model output. Injected test transports are explicitly labeled and cannot
claim a provider call or NVIDIA execution.

Before running, confirm the account has authorized Token Factory access and acceptable
credits/spend. A local API key alone does not establish that approval.

## Judgeable demo path

After a successful live run, `nebius-live-evidence/site/` contains:

- `index.html` — self-contained, script-free live proof/evaluation inspector;
- `receipt.json` — canonical hash-only runtime receipt.

Deployment is intentionally separate from generation. Publish the exact directory through the
approved BuilderWars hosting path, then verify the final URL while signed out. Do not claim a
working demo URL until that verification succeeds.

## Significant update during the submission period

BuilderWars existed before this hackathon. The competition-period delta is substantial and
should be stated plainly:

> During the hackathon submission period we added a dedicated Nebius Token Factory adapter
> constrained to NVIDIA model identifiers, a bounded structured policy-repair task,
> deterministic nine-case scoring, hash-only receipts, a human-readable evidence inspector,
> and a one-call live runtime receipt that separates provider execution from offline fixtures.
> We also added submission-specific setup, demo packaging, and evidence boundaries so judges
> can reproduce the exact task without exposing credentials or raw model output.

At submission time append the exact first competition commit and final submitted commit.

## Required product/model feedback capture

Do not pre-fill praise or criticism. After the real run, record concrete observations for each:

### Nebius Token Factory / AI Cloud

- Zero-to-first-call onboarding: exact steps that were clear or blocked.
- API/docs: exact endpoint/docs page used and anything that was ambiguous.
- Authentication: whether key creation and environment-only use were straightforward.
- Reliability: success/failure mode of the real call, including sanitized error class if any.
- Latency: integer runner-observed duration from the live receipt.
- Structured output: whether the model returned the required strict JSON on first attempt.
- Cost/credits: only report values visible in the authorized Nebius account; do not infer.
- Would we use it again? Give the concrete reason.

### NVIDIA model

- Exact model id.
- What the model was asked to do.
- Whether it satisfied the strict patch schema.
- Which deterministic checks passed/failed.
- Any reasoning/output-format friction observed.
- Why the selected model was appropriate for this bounded agentic task.
- One specific improvement that would make this workflow better.

## Demo video shot list — target 2:30

1. **0:00–0:20 — Problem.** BuilderWars needs model/provider claims that do not outrun evidence.
2. **0:20–0:45 — Architecture.** Show Token Factory → NVIDIA Nemotron → bounded task → deterministic evaluator → hash-only receipt.
3. **0:45–1:25 — Live call.** Run the one-call CLI with the secret hidden; show the provider/model fields and successful/invalid outcome.
4. **1:25–1:55 — Proof.** Open the generated judge page, nine checks, hashes, and evidence boundary.
5. **1:55–2:20 — Product.** Show the relevant BuilderWars experience and why replay/evidence matters to agent competitions.
6. **2:20–2:30 — Close.** Name Nebius Token Factory and the exact NVIDIA model verbally.

Use only owned/authorized visual and audio material. The public video URL is a publication gate.

## Exact final pre-submit checks

- Run focused tests and the repository's exact-head required checks.
- Search the submitted tree for API keys, `.env` files, raw provider responses, and accidental credentials.
- Confirm root `LICENSE` is visible on GitHub.
- Confirm README links this submission pack and the live command.
- Confirm the public demo URL works signed out and depicts the same submitted code.
- Confirm the public repository URL is reachable signed out.
- Confirm YouTube video is public and ≤ 3:00.
- Fill feedback from actual use only.
- Fill significant-update commit range.
- Complete Devpost registration/submission agreements only through the authorized account flow.
