"""A-vs-B match harness: play N seeded self-play games between two agent
configs and report W/D/L plus a rough Elo delta.

An agent is any callable ``(BughouseBoard) -> chess.Move``. Configs are given
as spec strings so a fresh agent can be built per game:

    random        uniform-random, seeded per game
    random:7      uniform-random, fixed seed 7
    mcts          MCTS at DEFAULT_ITERATIONS
    mcts:800      MCTS at 800 iterations/move

Every game opens with `opening_plies` seeded-random moves (an identical
opening regardless of which agent is X) so a match of otherwise
deterministic agents still produces distinct games. The two configs also
swap sides each game. A fixed `seed` makes the whole match reproducible.
"""

import math
from dataclasses import dataclass

import chess

from engine.board import BughouseGame
from search.mcts import DEFAULT_ITERATIONS, make_mcts_agent
from search.random_agent import make_random_agent

OPENING_PLIES = 4    # seeded-random plies before the configured agents take over
MAX_PLIES = 400      # abandon (score as draw) a game that runs this long


def build_agent(spec: str, *, fallback_seed: int | None = None):
    """Turn a spec string into a ``(board) -> Move`` agent."""
    name, _, arg = spec.partition(":")
    if name == "random":
        return make_random_agent(seed=int(arg) if arg else fallback_seed)
    if name == "mcts":
        return make_mcts_agent(iterations=int(arg) if arg else DEFAULT_ITERATIONS)
    raise ValueError(f"unknown agent spec: {spec!r}")


def _team_a_to_move(ply: int, board) -> bool:
    # run_self_play_game plays board A on even plies, board B on odd.
    # TEAM A = White-on-A + Black-on-B.
    return (ply % 2 == 0) == (board.turn == chess.WHITE)


def play_game(agent_x, agent_y, *, x_is_team_a: bool, opening_seed: int,
              opening_plies: int = OPENING_PLIES, max_plies: int = MAX_PLIES) -> str:
    """Play one game; return 'x', 'y', or 'draw'."""
    game = BughouseGame()
    game.assign_roles()
    opening = make_random_agent(seed=opening_seed)
    team_a_agent = agent_x if x_is_team_a else agent_y
    team_b_agent = agent_y if x_is_team_a else agent_x
    state = {"ply": 0}

    def dispatch(board):
        ply = state["ply"]
        if ply < opening_plies:
            move = opening(board)
        else:
            picker = team_a_agent if _team_a_to_move(ply, board) else team_b_agent
            move = picker(board)
        state["ply"] = ply + 1
        return move

    game.run_self_play_game(dispatch, max_moves=max_plies)

    outcome = game.result()  # 'A' | 'B' | 'draw' | None
    if outcome in (None, "draw"):
        return "draw"
    x_won = (outcome == "A") == x_is_team_a
    return "x" if x_won else "y"


def elo_delta(wins: int, draws: int, losses: int) -> tuple[float, float, float]:
    """Rough Elo difference (X minus Y) from a W/D/L record, with a ~95%
    interval from the score's standard error. Draws count half. Saturates at
    +/-800 when the score hits 0 or 1 (too few games to say more)."""
    n = wins + draws + losses
    if n == 0:
        return (0.0, 0.0, 0.0)
    s = (wins + 0.5 * draws) / n

    def to_elo(p: float) -> float:
        if p <= 0.0:
            return -800.0
        if p >= 1.0:
            return 800.0
        return -400.0 * math.log10(1.0 / p - 1.0)

    se = math.sqrt(s * (1.0 - s) / n) if 0.0 < s < 1.0 else 1.0 / (2.0 * n)
    return (to_elo(s), to_elo(s - 1.96 * se), to_elo(s + 1.96 * se))


@dataclass
class MatchRecord:
    spec_x: str
    spec_y: str
    games: int
    wins: int      # X wins
    draws: int
    losses: int    # X losses (== Y wins)
    elo: float
    elo_lo: float
    elo_hi: float

    @property
    def score(self) -> float:
        return (self.wins + 0.5 * self.draws) / self.games if self.games else 0.0

    def __str__(self) -> str:
        return (f"{self.spec_x}  vs  {self.spec_y}\n"
                f"  {self.games} games: +{self.wins} ={self.draws} -{self.losses} "
                f"(X score {self.score:.1%})\n"
                f"  Elo(X-Y) {self.elo:+.0f}  [{self.elo_lo:+.0f}, {self.elo_hi:+.0f}] ~95%")


def play_match(spec_x: str, spec_y: str, *, games: int = 20, seed: int = 0,
               opening_plies: int = OPENING_PLIES, max_plies: int = MAX_PLIES,
               on_game=None) -> MatchRecord:
    """Play `games` games between the two specs, swapping sides each game.
    `on_game(i, result, wins, draws, losses)` fires after each game."""
    wins = draws = losses = 0
    for i in range(games):
        agent_x = build_agent(spec_x, fallback_seed=seed + i)
        agent_y = build_agent(spec_y, fallback_seed=seed + 10_000 + i)
        r = play_game(agent_x, agent_y, x_is_team_a=(i % 2 == 0),
                      opening_seed=seed + i, opening_plies=opening_plies,
                      max_plies=max_plies)
        if r == "x":
            wins += 1
        elif r == "y":
            losses += 1
        else:
            draws += 1
        if on_game is not None:
            on_game(i, r, wins, draws, losses)

    elo, lo, hi = elo_delta(wins, draws, losses)
    return MatchRecord(spec_x, spec_y, games, wins, draws, losses, elo, lo, hi)
