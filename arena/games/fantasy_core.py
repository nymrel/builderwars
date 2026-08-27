"""Shared deterministic draft board for the AgentWars fantasy circuits.

The game is intentionally fictional. Real player data changes, carries source
rights, and would make an old replay depend on a network snapshot. These player
archetypes make every board self-contained while preserving the decisions a
fantasy harness has to solve: positional scarcity, roster construction, a
redraft window, and a dynasty window.
"""

ROSTER_LIMITS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1}
ROSTER_SIZE = sum(ROSTER_LIMITS.values())
TOTAL_PICKS = ROSTER_SIZE * 2
FORMATS = ("redraft", "dynasty", "qb_surge")

_BLUEPRINTS = (
    (1, "Pocket Ace", "QB", 322, 820, 25),
    (2, "Cannon North", "QB", 310, 900, 22),
    (3, "Sunday Driver", "QB", 336, 650, 33),
    (4, "Dual Current", "QB", 300, 870, 24),
    (10, "Workhorse", "RB", 286, 620, 24),
    (11, "Breakaway", "RB", 274, 710, 22),
    (12, "Goal Line", "RB", 260, 510, 27),
    (13, "Rookie Burst", "RB", 238, 720, 21),
    (14, "Checkdown", "RB", 248, 590, 25),
    (15, "Iron Runner", "RB", 270, 470, 28),
    (20, "Route Surgeon", "WR", 298, 780, 25),
    (21, "Deep Signal", "WR", 288, 700, 24),
    (22, "First Read", "WR", 280, 820, 22),
    (23, "Veteran Hands", "WR", 304, 560, 30),
    (24, "Slot Current", "WR", 268, 650, 25),
    (25, "Rookie Orbit", "WR", 246, 800, 21),
    (30, "Mismatch", "TE", 235, 650, 24),
    (31, "Red Zone", "TE", 250, 480, 29),
    (32, "Rookie Tower", "TE", 205, 680, 22),
    (33, "Chain Mover", "TE", 225, 540, 26),
)


def rules_text(format_name):
    if format_name == "redraft":
        score = "one-season points"
    elif format_name == "dynasty":
        score = "three-year dynasty value"
    elif format_name == "qb_surge":
        score = "one-season points with the roster's quarterback counted twice"
    else:
        raise ValueError("unknown fantasy format")
    return (
        "Two general-manager harnesses run a six-round snake draft. Each roster "
        "must finish with 1 QB, 2 RB, 2 WR, and 1 TE. Choose one available player "
        f"per turn. The higher total {score} wins. A move is "
        '{"player_id": <integer>}. Illegal, unavailable, or position-overflow '
        "picks forfeit the match. Every player and score is fictional and fixed "
        "inside this replayable game."
    )


def setup(rng, format_name):
    if format_name not in FORMATS:
        raise ValueError("unknown fantasy format")
    players = []
    for player_id, name, position, redraft, dynasty, age in _BLUEPRINTS:
        players.append(
            {
                "id": player_id,
                "name": name,
                "position": position,
                "redraft_points": redraft + rng.randint(-18, 18),
                "dynasty_points": dynasty + rng.randint(-45, 45),
                "age": age,
            }
        )
    return {
        "format": format_name,
        "players": players,
        "available": [p[0] for p in _BLUEPRINTS],
        "rosters": [[], []],
        "to_move": 0,
        "turn": 0,
        "last_mover": None,
    }


def _player(state, player_id):
    return next((p for p in state["players"] if p["id"] == player_id), None)


def _position_counts(state, seat):
    counts = {position: 0 for position in ROSTER_LIMITS}
    for player_id in state["rosters"][seat]:
        player = _player(state, player_id)
        if player is not None and player["position"] in counts:
            counts[player["position"]] += 1
    return counts


def _needs(state, seat):
    counts = _position_counts(state, seat)
    return {position: limit - counts[position] for position, limit in ROSTER_LIMITS.items()}


def observation(state, player):
    available = set(state["available"])
    return {
        "game": f"fantasy_{state['format']}",
        "format": state["format"],
        "rules": rules_text(state["format"]),
        "you_are": player,
        "to_move": state["to_move"],
        "turn": state["turn"],
        "round": state["turn"] // 2 + 1,
        "needs": _needs(state, player),
        "your_roster": list(state["rosters"][player]),
        "opponent_roster": list(state["rosters"][1 - player]),
        "available_players": [dict(p) for p in state["players"] if p["id"] in available],
    }


def legal(state, move):
    if not isinstance(move, dict):
        return False, "move must be an object"
    unexpected = set(move) - {"player_id"}
    if unexpected:
        return False, f"unexpected keys in move: {sorted(unexpected)}"
    if "player_id" not in move:
        return False, 'move requires "player_id"'
    player_id = move["player_id"]
    if not isinstance(player_id, int) or isinstance(player_id, bool):
        return False, "player_id must be an integer"
    if state.get("to_move") not in (0, 1):
        return False, "state has no legal seat to move"
    if player_id not in state.get("available", []):
        return False, "player is not available"
    player = _player(state, player_id)
    if player is None:
        return False, "player is not on this draft board"
    needs = _needs(state, state["to_move"])
    if needs.get(player["position"], 0) <= 0:
        return False, f"roster has no open {player['position']} slot"
    return True, "legal"


def _seat_for_turn(turn):
    # Six-round two-seat snake: 0,1,1,0,0,1,1,0,0,1,1,0.
    round_index, pick_in_round = divmod(turn, 2)
    if round_index % 2 == 0:
        return pick_in_round
    return 1 - pick_in_round


def apply(state, move):
    seat = state["to_move"]
    player_id = move["player_id"]
    rosters = [list(state["rosters"][0]), list(state["rosters"][1])]
    rosters[seat].append(player_id)
    turn = state["turn"] + 1
    return {
        "format": state["format"],
        "players": [dict(p) for p in state["players"]],
        "available": [pid for pid in state["available"] if pid != player_id],
        "rosters": rosters,
        "to_move": _seat_for_turn(turn) if turn < TOTAL_PICKS else 0,
        "turn": turn,
        "last_mover": seat,
    }


def roster_score(state, seat):
    format_name = state["format"]
    key = "dynasty_points" if format_name == "dynasty" else "redraft_points"
    total = sum(_player(state, player_id)[key] for player_id in state["rosters"][seat])
    if format_name == "qb_surge":
        total += sum(
            _player(state, player_id)["redraft_points"]
            for player_id in state["rosters"][seat]
            if _player(state, player_id)["position"] == "QB"
        )
    return total


def terminal(state):
    if state.get("turn") != TOTAL_PICKS:
        return None
    if any(_needs(state, seat)[position] for seat in (0, 1) for position in ROSTER_LIMITS):
        return None
    score0, score1 = roster_score(state, 0), roster_score(state, 1)
    if score0 == score1:
        return {"winner": None, "reason": f"{state['format']}_roster_score_tie:{score0}"}
    winner = 0 if score0 > score1 else 1
    return {"winner": winner, "reason": f"{state['format']}_roster_score:{score0}-{score1}"}


def move_bound(state):
    return TOTAL_PICKS
