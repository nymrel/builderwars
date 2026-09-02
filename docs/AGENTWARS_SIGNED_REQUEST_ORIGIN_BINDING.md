# AgentWars signed-request origin binding

Status: reviewed local protocol candidate. No production route, custom host,
DNS record, account setting, provider subscription, deployment, or publication
was changed by this work.

## Security objective

An Ed25519 runner request that is valid for one endpoint origin must not be
valid at another origin, even when both hosts expose the same path and receive
the same method, body, timestamp, nonce, runner id, and public key. This closes
the host-confusion gap recorded as `signed-request-origin-binding` in the frozen
BuilderWars foundation acceptance snapshot.

## Versioned contract

`agentwars.runner_request.v2` replaces the unreleased v1 request-signing
candidate. The exact UTF-8 canonical string is:

```text
agentwars.runner_request.v2
origin:<exact canonical endpoint origin>
method:<exact uppercase method>
path:<exact absolute path without query or fragment>
body-sha256:<lowercase SHA-256 of the exact body bytes>
timestamp:<canonical UTC instant with exactly milliseconds>
nonce:<16 random bytes as unpadded base64url>
runner-id:<exact awr1 id>

```

The final empty line above represents exactly one trailing LF. The signature is
Ed25519 over those exact bytes and is encoded as unpadded base64url.

## Trust boundaries

- The customer client signs the origin already validated and stored in the
  local runner profile.
- `send_signed_request` validates the requested transport origin and refuses a
  mismatch with the signed origin before calling any opener or network client.
- The hosted control plane is constructed with one validated `allowed_origin`.
  Its verifier reconstructs the canonical message with that server-side value.
- No request header or body field can select the verification origin.
- Production origin policy remains exact `https://nymrel.com`. Tests may use
  exact literal loopback origins under the existing local-test policy.
- Redirects, proxies, alternate casing, default-port aliases, userinfo, paths,
  queries, fragments, `localhost`, and IP shorthand remain refused.

The origin is public context, not a secret and not an identity attestation.
Origin binding does not prove provider account ownership, subscription, model,
runtime, harness execution, match execution, operator identity, deployment, or
publication.

## Host-confusion acceptance

The deterministic local runner suite proves that a request signed for
`https://nymrel.com` cannot be sent through a loopback transport and that the
refusal occurs before the injected opener is called. The hosted suite proves
that a same-key, same-path, same-body request signed for a different allowed
loopback origin fails as `invalid_signature`. It also proves that this failed
presentation does not consume the nonce: a correctly origin-bound request using
the same nonce is then accepted exactly once.

Run the focused evidence:

```bash
python -B bin/check_agentwars_runner.py
python -m unittest provider_hub_hosted.tests.test_control_plane
```

The runner suite also pins a deterministic v2 canonical string and Ed25519
signature vector, so an accidental downgrade, reordered field, missing origin,
or byte-level drift fails closed.

## Release and migration rule

There is no v1/v2 negotiation and no compatibility fallback. A v1 request is
rejected by the exact protocol header check. Before any protected domain cutover
or tester distribution, the reviewed source commit must be used to regenerate
the deterministic runner candidate and its manifests, ZIP digest, dependency
lock references, and verifier receipt. Publication remains a separate protected
decision with its own target, source, environment, rollback, and consent proof.
