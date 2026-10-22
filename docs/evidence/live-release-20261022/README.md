# BuilderWars live release verification — 2026-10-22

Both retained receipts passed against actual HTTPS responses and Chromium journeys. The application source is merged commit `1745c0a0cc8aaa31aaf8f67edc7765f32de6b547`, tree `ed6656541535881578bb51164d44a475197eb5cd`. The verifier checks out that exact application independently of this isolated verification branch. These evidence files do not change the deployed application or main branch.

Each receipt covers all 202 built files and 14 core routes, security headers, Markdown MIME, canonical links, and 390 px / 1280 px Watch replay/export/provenance, free-play, public replay, and actual Lab worker completion/cancellation/restoration. All files and routes had raw byte parity. Both browser runs recorded zero blocked requests, page errors, and provider calls. Canonical additionally passed three existing 308 redirect aliases and the direct `builderwars.vercel.app` alias. The index HTML is 4,452 UTF-8 bytes.

| Evidence | Preview | Canonical |
| --- | --- | --- |
| Origin | `https://builderwars-632bfkr0w-jalens-projects-0ade4450.vercel.app` | `https://builderwars.com` |
| Provider deployment ID | `dpl_7j7mkZdW8fQEZfTRqhqhwXRmBA3s` | `dpl_7JYf9isc1yU2x4ssfNZqCNnstdEk` |
| Verification run | [39712981458](https://github.com/nymrel/builderwars/actions/runs/39712981458) | [39713991377](https://github.com/nymrel/builderwars/actions/runs/39713991377) |
| Verifier commit | `e1484194ea934b66aae058d7eb9b11a38a705ed3` | `3e6f2b4114a29320b81018c805b0f0b9f66db5a7` |
| Artifact ID | `12398200518` | `12398111732` |
| Artifact ZIP SHA-256 | `b49810e0a076eed473506f16c26e152829780d37111275f2efd146b181cc39de` | `4beac8ea683e16fa075c82a3c6345edeb6cbdc41f94a2e900fdb736b154343d4` |
| Receipt SHA-256 | `71fe1ca1d8d8345661cf754326b1d473336f6cf6ec20b7206df8890c54a8c486` | `10866c0a7b3b1c493e757cdb7e81a213e9b1831e63e5f01e4d016a3e6e830650` |

Each directory retains the unmodified machine-readable receipt, eight screenshots, and two exported public sample replays. The CI artifacts expire after seven days; this Git evidence remains available. The verifier source SHA-256 is `45b7bb58a1e8ce510a8ccdca6504bfb8fa8c332f8673ef3a711142b7eda90821`; both independent application builds produced inventory SHA-256 `40d53272f042c9706c13e85346f45a3ede134f58107520d0de3fd03433896527`.

The release coordinator confirmed the production deployment READY, source commit 1745 above, and `builderwars.com` bound to that deployment in the existing project `prj_c2HDxCRh3sEFEZkOxemiwoUmp1Gp`. Production was a new build of the verified source, not promotion of the preview artifact. Its per-deployment install command was `npm ci --ignore-scripts --no-audit --no-fund`; no project or domain settings were changed. The canonical receipt independently establishes exact output parity. Previous production `dpl_21snU8G8aJp1gKnbmFtrBJQNTjBf` remains the rollback candidate; its source SHA is not provider-attested here.

Attempt history: initial verification run [39712355751](https://github.com/nymrel/builderwars/actions/runs/39712355751) was canceled during preparation before live checks and produced no live receipt. Direct preview promotion returned 422 without a detailed cause and did not change production. Production attempt `dpl_PtxnJC3ui5UFmpivMa2gmVa5FfMt` was canceled while building, before canonical traffic assignment; it remains unverified. The successful production retry changed only the ancillary npm audit/funding flags, without changing dependencies or enabling install scripts. These canceled attempts are not passes.

Scope: this proves source/output parity and the recorded browser journeys at the recorded times. It does not attest provider identity, model execution, physical mobile devices, or simultaneous multiplayer gameplay. Preview-only handling for an exact known Vercel toolbar suffix exists in the verifier but was unused in the recorded preview run; canonical always requires raw byte parity.
