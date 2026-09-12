"""Ten Fronts must finish under its hard move bound.

One Ten Fronts round costs FOUR engine turns, not two: signal seat 0, signal
seat 1, commit seat 0, commit seat 1. The runner (arena/match.py) increments
``turn`` once per ``apply`` and aborts with ``move_bound_exceeded`` when
``turn >= move_bound(setup_state)``. A bound derived from "two moves per round"
therefore exhausts mid-match and no Ten Fronts match can ever end on score.
These tests pin the true per-round cost and prove a full match completes both
at the game-module level (random legal agents) and through the real runner.
"""

from __future__ import annotations

import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arena.games import ten_fronts as tf  # noqa: E402
from arena.match import run_reference_match  # noqa: E402
from arena.replay import verify  # noqa: E402
from arena.transcript import load  # noqa: E402
from entrants.backends import execution_claim_for_backend  # noqa: E402

TURNS_PER_ROUND = 4  # signal x2 seats, then commit x2 seats
SAFE_SIGNALS = ("holding the line", "all in on the centre", "expect a feint", "")


def random_legal_move(state, rng):
    """A trivial agent: random legal signal or random legal allocation."""
    if state["phase"] == tf.PHASE_SIGNAL:
        return {"signal": rng.choice(SAFE_SIGNALS)}
    cuts = sorted(rng.randint(0, tf.TROOPS) for _ in range(tf.FRONTS - 1))
    edges = [0, *cuts, tf.TROOPS]
    allocation = [edges[i + 1] - edges[i] for i in range(tf.FRONTS)]
    return {"allocation": allocation}


def stub_manifest(name, strategy):
    return {
        "name": name,
        "cmd": [
            sys.executable,
            str(ROOT / "entrants" / "ten_fronts_model_harness.py"),
            "--name", name, "--strategy", strategy, "--backend", "stub:v1",
        ],
        "env": [],
        "claimed_model": "stub:v1",
        "execution_claim": execution_claim_for_backend("stub:v1"),
    }


class TenFrontsMoveBoundTests(unittest.TestCase):
    def test_one_round_costs_four_engine_turns(self):
        state = tf.setup(random.Random(1))
        rng = random.Random(2)
        for turn in range(TURNS_PER_ROUND):
            self.assertEqual(state["round"], 0, f"round advanced early at turn {turn}")
            state = tf.apply(state, random_legal_move(state, rng))
        self.assertEqual(state["round"], 1)
        self.assertEqual(state["turn"], TURNS_PER_ROUND)
        self.assertEqual(state["phase"], tf.PHASE_SIGNAL)

    def test_bound_is_exactly_the_full_match_turn_count(self):
        state = tf.setup(random.Random(1))
        self.assertEqual(tf.move_bound(state), tf.ROUNDS * TURNS_PER_ROUND)

    def test_random_agents_finish_under_the_bound_for_many_seeds(self):
        for seed in range(25):
            state = tf.setup(random.Random(seed))
            bound = tf.move_bound(state)
            rng = random.Random(seed * 7919)
            turn = 0
            # Mirror the runner's loop order exactly: terminal first, then bound.
            while tf.terminal(state) is None:
                self.assertLess(
                    turn, bound,
                    f"seed {seed}: bound {bound} exhausted at round {state['round']} "
                    f"phase {state['phase']} — match can never finish",
                )
                move = random_legal_move(state, rng)
                ok, why = tf.legal(state, move)
                self.assertTrue(ok, why)
                state = tf.apply(state, move)
                turn += 1
            end = tf.terminal(state)
            self.assertEqual(state["round"], tf.ROUNDS)
            self.assertEqual(turn, tf.ROUNDS * TURNS_PER_ROUND)
            self.assertLessEqual(turn, bound)
            self.assertTrue(end["reason"].startswith("ten_fronts_score"), end)

    def test_runner_plays_a_full_match_to_a_scored_result(self):
        with tempfile.TemporaryDirectory(prefix="ten-fronts-bound-") as out:
            result = run_reference_match(
                game_name="ten_fronts",
                seed=7001,
                entrants=[
                    stub_manifest("bound-alpha", "value-blitz"),
                    stub_manifest("bound-omega", "even-pressure"),
                ],
                out_dir=out,
            )
            self.assertNotEqual(result["reason"], "move_bound_exceeded")
            self.assertTrue(result["reason"].startswith("ten_fronts_score"), result["reason"])
            states = [r for r in load(result["transcript"]) if r.get("kind") == "state"]
            last = states[-1]["body"]
            self.assertEqual(last["turn"], tf.ROUNDS * TURNS_PER_ROUND)
            self.assertEqual(last["state"]["round"], tf.ROUNDS)
            self.assertNotIn("abort", {r.get("kind") for r in load(result["transcript"])})
            self.assertEqual(verify(result["transcript"])["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
