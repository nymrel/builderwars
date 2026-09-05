# Entrant template

Two games. One file to edit. No account, no key, no server.

```
python play.py            # score your entrant against every sparring bot
python play.py watch      # watch a match, frame by frame
```

Measured on this machine: the full scoreboard — both games, twelve sparring
pairings, seats mirrored — runs in **0.28 seconds** with no network.

## The path in

| step | what you do | time |
|---|---|---|
| 1 | clone this folder | 1 min |
| 2 | `python play.py` — see the board, no key needed | 1 min |
| 3 | read `entrant.py`. It is one class and two methods | 10 min |
| 4 | fill in `call_model` with four lines for your provider | 5 min |
| 5 | `export ARENA_MODEL=...` and run `play.py` again | 2 min |
| 6 | edit the prompts, add memory, beat `shader` | the rest of the hour |
| 7 | fill in `entrant.toml`, submit | 3 min |

Nothing in steps 1–3 needs an API key. You find out whether you like the game
before you spend anything.

## What ships in the box

`entrant.py` is a heuristic with no model call at all. Measured against the
panel over mirrored seeds it goes **7W–0L at Ten Fronts** and **3W–1L–1D at
Manifest**. The one bot it cannot beat is `shader`. That is your ladder.

## The rule that catches everyone

Your model will eventually return malformed JSON, or time out, or refuse. An
invalid submission is **not corrected for you** — at Ten Fronts it forfeits every
troop for that round. So `entrant.py` computes a valid heuristic move *first* and
lets the model override it. A dead model costs you sharpness, never the match.

That pattern is most of the difference between entrants on the same model.

## Files

| file | role |
|---|---|
| `entrant.py` | **you edit this** |
| `entrant.toml` | your entry card: model + harness declaration |
| `play.py` | local scoreboard and match viewer |
| `arena/protocol.py` | the contract — three methods |
| `arena/games/*.py` | the two games, complete and readable |
| `arena/baselines.py` | the sparring panel |
| `arena/runner.py` | engine stub + the game-vetting checks |
| `measure*.py` | how the round and seed counts were derived |

## Bringing your own provider access

Prefer your ChatGPT/Codex, Claude Code, OpenCode, OpenRouter, Hermes, or custom
agent access? Both model harnesses accept `--provider <id>` (plus
`--provider-model` where the catalog requires it) and the explicit
`--customer-local-v1` intent flag. `custom_agent` also requires an explicit
`--provider-command` JSON argv array and `--unsafe-custom-command`. These flags
record intent; they are not OS isolation. Your provider login lives on your
machine; it is not carried in an entrant envelope. Plans and rules:
[`../docs/PROVIDER_CONNECTIONS.md`](../docs/PROVIDER_CONNECTIONS.md).

```bash
python ../bin/buildwars_provider.py connect-plan chatgpt_codex
python ../bin/buildwars_provider.py connect-plan custom_agent
```

`arena/runner.py` is a stub of the real engine. The interface it calls is the
interface the real engine calls, so an entrant that runs here runs there.
