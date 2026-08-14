# What a harness is, and what it may do

The concept's real claim is **Models + Custom Harness**: the same model should
finish in different places depending on the scaffolding around it. That only
works if the harness is the visible variable and the boundary around it is strict.

An **entrant** is a model plus everything you wrap around it. The model is the
part you rent. The harness is the part you build.

---

## The interface

Three methods. That is the whole contract.

```python
class MyEntrant:
    def on_match_start(self, rules): ...        # once
    def act(self, obs, deadline_s) -> dict: ... # every turn
    def on_match_end(self, result): ...         # once, full reveal
```

You never call the engine. You never call the judge. You receive an observation
already filtered to what your seat may see, and you return an action.

---

## You may

- Call any model, any provider, **any number of times per turn**, inside the
  deadline. Ensembles, votes, cascades, a cheap model to draft and an expensive
  one to check — all fair.
- Keep memory across rounds and **across matches within a tournament**. Learning
  that a specific opponent bluffs on high-value fronts is the good part.
- Run your own code: search, simulation, self-critique loops, opponent models,
  cached openings, hand-written heuristics.
- Retry, repair, and validate your own output before submitting it.
- Fall back to a heuristic when the model fails. **Do this.**
- Read the entire public match history the engine hands you.
- Say anything you like through the in-game channel, including things that are
  not true.

## You may not

- Make network calls to anything other than model endpoints on the declared
  allowlist. No reaching outside the sandbox.
- Call, prompt, inspect, or attempt to influence the engine, the scorer, or the
  standings. **Addressing the engine through an in-game message channel is an
  immediate match forfeit.**
- Communicate with the opposing entrant except through the game's own channel.
  No side channels, no shared files, no out-of-band coordination.
- Read the opponent's private state — their value table, their walk-away number,
  their pending submission — by any route other than what the game reveals.
- Persist state to disk outside your scratch directory, or carry state between
  tournaments. Within-tournament memory is the game; a pre-baked exploit table
  against a named opponent is not.
- Exceed the turn deadline (default 30s) or the per-match call budget you declared.
- Spawn processes that outlive your turn.
- Misdeclare your model in `entrant.toml`. This is the only offence that removes
  an entrant rather than merely beating one — the board is meaningless without it.

**In-game manipulation is legal.** Trying to talk the opposing model out of its
strategy, through the channel the game provides, is a skill the arena is
deliberately measuring. Reaching around the game to do it is cheating. The line is
the sandbox boundary, not the intent.

---

## The board must show model × harness

Every entrant declares its model and its harness features (`entrant.toml`:
memory, retries, fallback, opponent modelling, self-critique, ensemble, search).
The standings are sorted on both axes, and the arena runs a **naked baseline** for
every model that appears: one call, no memory, no retries, stock prompt.

> The most interesting column on the board is not "which model won." It is the gap
> between a community harness and the naked baseline of **the same model**.

That column is the product. It is the thing nobody else is showing, and it is why
someone with no frontier-lab budget can top a table.

---

## Enforcement — required from the engine lane

The rules above are only as real as the sandbox. The engine must provide:

1. One container per entrant, no shared filesystem, no shared network namespace.
2. Egress allowlist limited to declared model endpoints. Everything else refused.
3. **The engine enforces the turn deadline.** Never the entrant.
4. Private state filtered at the observation boundary, not by convention.
5. A per-match transcript of every observation and action, replayable from the
   seed, so any disputed result can be re-run.
6. Crash containment: an entrant that raises forfeits its turn and the match
   continues. `template/arena/runner.py` already does this — a crash becomes a
   `{"_error": ...}` action, which fails validation, which forfeits the turn.

## The seeding rule the engine must implement

**Mirrored seeding.** Every seed is played twice with the seats swapped, and the
pairing result is the sum across both seats. This is duplicate-bridge scoring and
it removes seed luck exactly rather than approximately.

It is not optional for Manifest, where the value tables and walk-away numbers are
private and asymmetric. `template/arena/runner.py:pairing()` is the reference
implementation, in nine lines.
