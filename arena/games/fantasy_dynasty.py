"""AgentWars fantasy football: three-year dynasty circuit."""

from . import fantasy_core as core

NAME = "fantasy_dynasty"
VERSION = "1"
SUMMARY = "Draft a complete fantasy roster for the strongest three-year dynasty value."
PLAYERS = 2
RULES = core.rules_text("dynasty")


def setup(rng):
    return core.setup(rng, "dynasty")


observation = core.observation
legal = core.legal
apply = core.apply
terminal = core.terminal
move_bound = core.move_bound
