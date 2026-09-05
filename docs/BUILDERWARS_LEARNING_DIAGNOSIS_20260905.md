# Why repeated games do not currently guarantee improvement

Source inspected: deployed application tree `d0873da18dfeeda1062cdce5e503c82aa804d904`;
pending documentation/test head `640d955e21df6da9969ebd42622a46b952ac4193` has no
application changes. September 5, 2026. No claim of a reproduced customer session.

## Confirmed implementation limits

- `src/learning.ts` records only replay-verified, rule-complete practice games.
  Failed, stopped and unfinished games do not train. It detects missed immediate
  wins and avoidable one-move losses, not general strategic mistakes or forks.
- Eligible games are Connect Four, tic-tac-toe and custom connect boards of at
  most42cells. Chess, checkers and built-in opponents do not adapt.
- Connected OpenRouter/harness contenders receive at most four recent tactical
  examples in subsequent request context. This does not modify model weights,
  the harness implementation or the provider's subscription model.
- Memory is local to this device/browser. It is keyed by name, connection kind,
  model, effort, strategy, harness endpoint and exact rule configuration. Changing
  those profile fields can select a different memory history. This isolation is
  deliberate, but an unchanged display name is not sufficient to identify a
  continuing learner. There is no account-wide learning synchronization.
- Evaluation memory defaults off. The optional memory-enabled evaluation freezes
  a snapshot; outcomes never update it. This prevents learning from the test set.
- A request receipt proves context was attached, not that the model obeyed it.
  A customer-local harness receives `practiceMemory` and must actually consume it.
  No before/after real-model uplift has been established by existing persistence,
  referee, mock-response or browser tests.

This makes the user's observation consistent with the current implementation.
Playing more games alone cannot turn the current chess contender into a stronger
chess engine, and repeatedly running baseline Evals does not teach the model.

## Exact checks for a reported repeat mistake

1. Identify the game, contender kind and unchanged profile configuration.
2. Confirm the prior practice game reached a rules-defined finish and contains
   one of the supported tactical mistakes; inspect its replay, not its caption.
3. Confirm a retained episode and a subsequent request's context digest/source
   receipt. A device-save failure or another browser is a separate storage issue.
4. For an external harness, inspect whether it uses the supplied `practiceMemory`.
5. Classify the subsequent decision: format failure, illegal move, tactical
   mistake, or a longer-horizon strategic weakness. Do not combine these rates.

## Next bounded improvement experiment

Use one supported game and one connected contender first. Record a baseline on
a fixed held-out position set. Collect lessons from a separate practice set,
freeze the resulting memory, then rerun the same held-out set with identical
model, effort, legal-move contract and capped resources. Keep evaluation outcomes
out of practice memory. Counterbalance condition order and include uncertainty;
one successful rematch is not a reliable improvement estimate.

Use the production decision parser for gameplay acceptance. Independently count
strict-format compliance, illegal/failed calls, missed wins, avoidable immediate
losses, completion, input/output usage and latency. Track rejected attempts too.
Compare no-memory versus frozen-memory contexts; a hand-coded tactical helper is
a separate harness-assistance experiment, not learned behavior. Retain original
failures and version every candidate. Promote no candidate unless held-out results
improve without unacceptable reliability or resource regressions.

The local showcase in `BUILDERWARS_LOCAL_SHOWCASE.md` includes an actual two-response
strict-format experiment with no accepted moves, followed by a separately
predeclared two-game legal-constrained harness-assistance experiment. That pair
split1–1, with the first seat winning both games. Neither experiment tested
practice memory or satisfies the improvement milestone. No performance,
world-level chess, universal learning or public leaderboard claim is justified.
