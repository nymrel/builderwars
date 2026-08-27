# Security policy

BuilderWars executes entrant programs as local subprocesses. The v1 engine enforces process separation, scratch working directories, an environment allowlist, no inherited handles, timeouts, and output caps. It does **not** block network access, confine filesystem access, or enforce CPU/memory quotas.

## Supported versions

The current `main` branch is supported while the project remains experimental. Published transcripts remain independently replay-verifiable under the engine digest recorded in each header.

## Report privately

Send security reports to **contact@nymrel.com**. Do not place credentials, private entrant source, provider keys, customer data, or live exploit details in a public issue.

Useful reports include:

- a forged or altered transcript that verifies as valid;
- a scorer path influenced by entrant-authored self-report data;
- engine/verifier disagreement;
- protocol output that escapes its configured cap;
- inherited handles, unexpected environment variables, or leaked transcript paths;
- a timeout or engine error that awards points rather than voiding the match;
- a path-classification bypass in the shipped entrant-admission guard;
- a result or policy statement that materially overstates isolation or model identity.

Include the affected commit, operating system and Python version, the smallest synthetic reproducer, expected and observed behavior, and whether the issue can modify scoring, expose data, or execute outside the stated boundary.

## Untrusted entrants

The shipped `run_match.py` and `run_series.py` commands refuse entrant files outside the repository's own `entrants/` directory unless the operator explicitly supplies `--allow-unconfined-entrants`. Classification uses resolved filesystem paths so string-prefix lookalikes and symlinks resolving outside the bundled tree remain external.

This is an accidental-use guard, **not** a sandbox. The override does not add network, filesystem, CPU, or memory isolation. Direct callers of `arena.match.run_match` do not pass through the CLI guard. Never run an entrant you do not trust until an OS-level enforcement adapter exists.

## Out of scope

Reports requesting hidden model attribution, consumer-subscription credential routing, covert network access, or weaker replay verification are not features the project will implement.
