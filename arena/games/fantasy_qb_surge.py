"""AgentWars New Rules Week: quarterback points count twice."""

from . import fantasy_core as core

NAME = "fantasy_qb_surge"
VERSION = "1"
RULESET_ID = "fantasy_qb_surge_v1"
SUMMARY = "Draft a one-season roster with quarterback points counted twice."
PLAYERS = 2
RULES = core.rules_text("qb_surge")


def setup(rng):
    return core.setup(rng, "qb_surge")


observation = core.observation
legal = core.legal
apply = core.apply
roster_score = core.roster_score
terminal = core.terminal
move_bound = core.move_bound
