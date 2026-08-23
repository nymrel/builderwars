"""AgentWars fantasy football: one-season redraft circuit."""

from . import fantasy_core as core

NAME = "fantasy_redraft"
VERSION = "1"
SUMMARY = "Draft a complete fantasy roster for the strongest one-season score."
PLAYERS = 2
RULES = core.rules_text("redraft")


def setup(rng):
    return core.setup(rng, "redraft")


observation = core.observation
legal = core.legal
apply = core.apply
terminal = core.terminal
move_bound = core.move_bound
