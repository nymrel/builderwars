# Ox Alpha MAX review record: hosted P2 closure

Status: **APPROVED** for the bounded local hosted-control-plane slice.

This record does not authorize a merge, tag, release, provider run, account
mutation, Redis provisioning, deployment, Cloudflare/DNS change, signup, billing,
invitation, or public launch.

## Reviewed identity

- immutable base: `6330c5b673589eac69ffcb3fb00c16c6973baa61`
- task-packet SHA-256: `7c9b585119f168c49e83aca3299d3622ecbdf3da57ea621ee95f0517687a3197`
- exact reviewed `store.py` SHA-256: `a08cd077035dd098e49b874f9a5e204109627d71c1742a683ee813513102f31f`
- exact reviewed `handlers.py` SHA-256: `63b698af1e045bfd07a0ebf5d3b46401799d0952f575299140d7336ad0424df1`
- exact reviewed `verify.py` SHA-256: `73c12ee810d7af9dd05353a815dc8cbc6407d442e0d27e4977a90607ea1079ce`
- exact reviewed `tests/test_control_plane.py` SHA-256: `4814e9116275caec55ba513ff814c456fdd61f24acafbd1605f2da40892d1ddc`

The reviewed task packet contained the exact `git diff --unified=8` for those
four files against the immutable base. The contained reviewer had no filesystem,
shell, edit, task, skill, or network tools.

## Accepted Max receipt

- run id: `51119615-11ef-4962-b223-c368e1884485`
- route: `opencode-go`
- runtime identity: `glm-5.3-flash`, variant `max`
- authority/input: read-only, private
- fallback: disabled
- assistant-output SHA-256: `ac587924a22c1193d976a6086595d028995bdd0f6b3eace0536ade061d8c98d0`
- receipt SHA-256: `891107e08a1dfc300a6b4460fc8bba88b4f080e9318b3dfafba3afd17bbbe491`
- receipt: `C:\Users\johns\AppData\Local\JalenBuilds\receipts\ox-alpha-agent-runs\51119615-11ef-4962-b223-c368e1884485.json`
- verdict: `VERDICT: APPROVE`
- severity counts: P0 `0`, P1 `0`, P2 `0`, P3 `5`

Max found all five accepted P2 items closed: uniform malformed-runner taxonomy,
wrong-owner pairing non-mutation, renewal/refusal fidelity, strict JSON/body/time
boundaries before nonce consumption, and stable signed-envelope error handling.
It assessed the five added tests as non-vacuous and coherent with the 20-to-25
test-count increase.

## Non-blocking P3 observations and disposition

1. Pre-auth callers can distinguish coarse `invalid_json` and `invalid_schema`
   codes. Retained intentionally so invalid schema is rejected before a valid
   nonce is consumed; no state or secret is disclosed.
2. `_decode_exact_object` relies on the unchanged `validate_json_body` contract
   returning `bytes`. Retained; the local validator guarantees that exact type
   and strict envelope gates reject non-`bytes` bodies.
3. Max noted removal of `expired = False` in `revoke_runner`. Integrator review
   confirmed the assignment was unused; Ruff identified it as `F841` and the
   function has no later read of that local.
4. Handler and verifier envelope gates duplicate a small type check. Retained as
   defense in depth so handlers do not parse or compare malformed envelopes
   before the verifier boundary.
5. Handler responses collapse store `invalid_epoch` and `invalid_digest` into the
   coarser `invalid_schema`. Retained and pinned by tests; the store keeps its
   more specific internal taxonomy.

## Review trace

- `550ec4f1-d4f0-4c70-99d4-704856ea13ca`: preflight blocked before provider
  invocation because `release-candidate` was incompatible with read authority.
- `fccd24e4-c8a0-42a2-8136-63c7ded150ef`: preflight blocked before review because
  immutable explorer snapshotting rejects linked worktree Git custody.
- `a8311e19-43e4-4ec0-a4e8-b35c8cb8aa1f`: contained Max completed but returned
  commands instead of a verdict; result rejected. Receipt SHA-256:
  `5babd8b0cbc1453eb2b8973631038a12ff1a57c75412e03fb6df342fd8073979`.
- `51119615-11ef-4962-b223-c368e1884485`: corrected tool-disabled output contract;
  completed with the accepted zero-P0/P1/P2 verdict above.

## Local evidence supplied to Max

- hosted control-plane tests: `25/25` passing
- Ruff: passing
- `py_compile`: passing
- `git diff --check`: passing before the temporary embedded-diff packet was
  replaced by this durable record

The exact reviewed implementation bytes must be re-hashed immediately before
commit. Any source change invalidates this acceptance and requires a fresh Max
review.
