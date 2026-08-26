# AgentWars customer-local source-match lane

Status: locally complete and committed; external acceptance and production
lanes remain open. No provider, model, hosted service, production account,
deployment, publication, ranking, billing, or customer state changed.

## Ownership

- Claim: `codex-builderwars-agentwars-source-match-v1-20260826`
- Branch: `codex/agentwars-launch-integration-20260825`
- Base commit: `b4c5f9ec3ab1a42ef14c6d7acbb06ccb3cb69bb7`
- Feature commit: `b5fb8739ecfc71d59ddb1338604c8671f98e3f38`
- Immutable Ox review range:
  `b4c5f9ec3ab1a42ef14c6d7acbb06ccb3cb69bb7..b5fb8739ecfc71d59ddb1338604c8671f98e3f38`
- Hosted contract pair: Nymrel
  `1d9e6003590447380219470356f87aa2cf528426`.
- Ox Alpha Max: required for immutable-delta acceptance. The provider contract
  preflight remains externally drifted, so no model verdict is claimed.

## Exact scope

- Validate one signed, non-leasing private job preparation response.
- Recheck the paired fixed fantasy harness before provider spend.
- Reverify two assigned signed Agent Passports and their exact job bindings.
- Reserve three new, distinct, non-nested local output paths.
- Write one digest-bound plan for the fixed local cross-provider runner.
- Keep fresh execution consent outside the generated plan.
- Do not launch a provider, model, subprocess, arbitrary harness, publication,
  ranking, or evidence upload from preparation.

## Local receipts so far

- `python bin/check_competition_source_match.py`: 52/52 passing.
- `python bin/check_competition_evidence_job.py`: 82/82 passing.
- `python bin/check_cross_provider_match.py`: 302/302 passing.
- `python bin/check_agentwars_runner.py`: 154/154 passing.
- `python bin/check_provider_hub.py`: all sections passing.
- Ruff lint and formatting: passing for the exact Python delta.
- Independent Ox Alpha Max review remains open. The provider preflight last
  failed closed before seat acquisition on documentation, endpoint,
  training-policy, retention-policy, and temporary-offer contract drift, so no
  model verdict is represented.
