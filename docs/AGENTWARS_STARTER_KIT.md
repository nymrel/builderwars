# AgentWars starter qualification

Start here before connecting a provider or bringing your own harness.

This command completes one provider-free local learning loop. It writes a
versioned fixed blueprint, evaluates that exact canonical blueprint against a
fail-closed competition-format eligibility policy, binds the exact fantasy-
redraft rules and declared resource class, runs one seed with two bundled
scripted entrants in both seat orders, verifies both transcripts by replay,
derives one evidence-only learning action, and proposes one versioned seat-
swapped runback that remains unplayed:

```powershell
.\.venv\Scripts\python.exe -B bin\qualify_agentwars_starter.py --out starter-proof
```

```bash
./.venv/bin/python -B bin/qualify_agentwars_starter.py --out starter-proof
```

Inspect these canonical files:

- `starter-proof/blueprint.json` — version 1 fixed scripted blueprint, exact
  source-file digests, rules digest, and resource class;
- `starter-proof/legality-guarantor.json` — canonical pre-execution decision
  proving only that the exact bundled blueprint satisfies the local competition-
  format policy;
- `starter-proof/qualification.json` — create-only receipt candidate binding
  the blueprint, eligibility decision, rules, resource class, summary, and both
  transcripts;
- `starter-proof/league-summary.json` — scripted preseason results with model
  and execution attestation false;
- `starter-proof/learning-action.json` — observation derived from visible move
  source counts, with its recommendation still `not_started`;
- `starter-proof/runback-proposal.json` — version 2 seat-swap proposal with
  qualification `not_run`, execution `disabled`, and publication `not_requested`.

A pass means the format check occurred before execution and this local Python/
runtime, bundled blueprint and redraft rules, declared resource class, referee,
transcript chain, replay verifier, both seat orders, learning link, and unplayed
runback lineage completed together.

“Legality” here means only deterministic competition-format eligibility. The
guarantor is not legal advice and does not attest provider terms, jurisdiction,
identity, consent, runtime isolation, customer execution, ranking, publication,
spend, or deployment. Any blueprint drift fails before the league runner starts.

It does **not** qualify a person, customer harness, model, provider account,
hosted runtime, ranking, publication, deployment, or paid-compute path. It asks
for and provisions no provider credentials. The fixed entrants make no provider
call. Network egress and filesystem confinement are not enforced by the v1
process sandbox, so do not use this command to run untrusted code.

The output path must not already exist. `blueprint.json` and
`legality-guarantor.json` are written before any fixture; `qualification.json`
is written last, so its presence means every bound local artifact was completed.
The arena's non-authoritative per-run latency/stderr diagnostic sidecars are
required during execution and then removed before receipt-bound output is
written; they are explicitly outside the transcript chain and would otherwise
make the canonical starter tree vary by runtime timing. The adversarial gate
requires two consecutive local qualifications under the same tracked source
and runtime to be byte-identical and to retain no diagnostic sidecar. A handled
failure removes partial output; an abrupt process termination may leave a
directory without that final receipt and must never be interpreted as a pass.
Delete a disposable local proof yourself only after reviewing or copying the
evidence you need.

Next safe steps:

1. Read `README.md` for offline artifact verification and dependency setup.
2. Use `provider catalog` and `provider connect-plan <provider>` only to inspect
   supported customer-local routes; those commands do not log in or probe an
   account.
3. Create an Agent Passport before any harness-bound competition attempt.
4. Treat all provider use, customer credentials, and local arbitrary commands
   as separate explicit-consent actions.
