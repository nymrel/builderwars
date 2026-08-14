"""The entrant contract. This is the whole interface you have to satisfy.

An entrant is an object with three methods. The engine owns the loop; you never
call the engine, the judge, or the opponent. You receive an Observation that has
already been filtered to what your seat is allowed to see, and you return an
Action. Everything else you do -- model calls, memory, search, retries -- happens
inside act() and is entirely up to you. That is the harness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Rules:
    """Handed to the entrant once, at match start. Everything public about the game."""

    game: str
    seat: str  # "A" or "B"
    opponent_label: str  # display name only; never a handle you can call
    config: dict[str, Any] = field(default_factory=dict)
    turn_deadline_s: float = 30.0


class Entrant(Protocol):
    """Implement this. See entrant.py for a working example."""

    def on_match_start(self, rules: Rules) -> None:
        """Called once. Set up memory, warm a cache, pick an opening strategy."""

    def act(self, obs: dict[str, Any], deadline_s: float) -> dict[str, Any]:
        """Called every time it is your turn. Must return within deadline_s.

        obs is JSON-safe and contains ONLY information your seat may see.
        Return a JSON-safe action dict. An invalid or late action is not
        corrected for you -- see each game's forfeit rule.
        """

    def on_match_end(self, result: dict[str, Any]) -> None:
        """Called once. Full reveal (including the opponent's private state) lands
        here, so you may learn across matches within a tournament."""


class Game(Protocol):
    """Implement this to contribute a GAME rather than a player."""

    name: str
    seats: tuple[str, str]

    def setup(self, seed: int, config: dict[str, Any]) -> Any: ...
    def observation(self, state: Any, seat: str) -> dict[str, Any]: ...
    def to_act(self, state: Any) -> list[str]:
        """Seats that must submit an action now. Two seats = simultaneous."""

    def apply(self, state: Any, actions: dict[str, dict[str, Any]]) -> Any: ...
    def is_over(self, state: Any) -> bool: ...
    def scores(self, state: Any) -> dict[str, float]: ...
    def render(self, state: Any) -> str:
        """One spectator frame. Must be legible without reading the rulebook."""

    def reveal(self, state: Any) -> dict[str, Any]:
        """Full post-match truth, including both sides' private state."""
