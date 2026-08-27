# AgentWars customer-local Claude Code route

- task_id: `codex-builderwars-claude-local-cli-v3-20260827`
- owner: `codex`
- status: `local_validation_passed_pending_exact_head_ox_max_review`
- claim_id: `codex-builderwars-claude-local-cli-v3-20260827`
- branch: `codex/agentwars-launch-integration-20260825`
- base_commit: `a99393c461c02794f2ed3b2ffe5523aac418590e`
- policy_evidence_date: `2026-08-27`
- policy_change: Anthropic now expressly documents that a product may run the unmodified Claude Code binary when each end user authenticates with their own Claude subscription, API key, or supported cloud-provider credential and is billed directly, subject to Anthropic Commercial Terms and branding conditions
- official_sources: `https://code.claude.com/docs/en/legal-and-compliance`, `https://code.claude.com/docs/en/authentication`, `https://code.claude.com/docs/en/cli-reference`
- objective: enable only the unmodified customer-local `claude -p` adapter with every built-in Anthropic authentication method available, no BuildWars login surface, no AgentWars enumeration/logging/serialization/persistence of credential values, no resale/intermediation, no hosted subscription proxy, no tools, no MCP, no session persistence, and false provider/model/account/plan/billing/runtime/execution attestations
- no_touch: live Claude login or provider call; credentials; CLI auth stores; hosted execution; arbitrary public execution; provider account, billing, deployment, release, publication, merge, tag, DNS, or launch state
- protected_gate: public enablement still requires recorded acceptance of applicable Anthropic Commercial Terms and branding conditions plus fresh exact-head independent review
- validation: focused hostile adapter tests, provider-hub and cross-provider gates, competition/source/prepared evidence gates, runner bundle build/verify, master offline verification, no-network scans, diff check, fresh Ox Alpha MAX exact-head review
- local_results: provider hub full ladder pass; cross-provider 303; runner 158; competition evidence 85; source preparation 54; prepared match 118; publication candidate 36 with one Windows symlink capability skip; runner bundle 42; provider/network calls 0 in these gates; installed Claude Code 2.1.219 version/help-only probe confirms the containment flags it lists, while the current official CLI reference explicitly documents `--max-turns` and notes that `claude --help` is not exhaustive
- current_stop: this file travels with the candidate commit; the resulting exact head is not yet independently reviewed, integrated, released, deployed, terms/branding-accepted, or live-account tested; fresh exact-head Ox Alpha MAX review remains required
- truth_boundary: code and offline subprocess mocks can prove the command/custody/fail-closed contract only; they do not prove a Claude account, subscription, entitlement, model, provider response, billing path, commercial-terms acceptance, production match, or launch
