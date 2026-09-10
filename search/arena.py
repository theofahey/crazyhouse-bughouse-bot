"""A-vs-B match harness: play N seeded self-play games between two agent
configs and report W/D/L plus a rough Elo delta.

An agent is any callable ``(BughouseBoard) -> chess.Move``. Configs are given
as spec strings so a fresh agent can be built per game:

    random        uniform-random, seeded per game
    random:7      uniform-random, fixed seed 7
    greedy        1-ply argmax of evaluate()
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
from search.greedy_agent import make_greedy_agent
from search.mcts import DEFAULT_ITERATIONS, make_mcts_agent
from search.random_agent import make_random_agent

OPENING_PLIES = 4    # seeded-random plies before the configured agents take over
MAX_PLIES = 400      # abandon (score as draw) a game that runs this long


def build_agent(spec: str, *, fallback_seed: int | None = None):
    """Turn a spec string into a ``(board) -> Move`` agent."""
    name, _, arg = spec.partition(":")
    if name == "random":
        return make_random_agent(seed=int(arg) if arg else fallback_seed)
    if name == "greedy":
        return make_greedy_agent()
    if name == "mcts":
        return make_mcts_agent(iterations=int(arg) if arg else DEFAULT_ITERATIONS)
    raise ValueError(f"unknown agent spec: {spec!r}")


def _team_a_to_move(ply: int, board) -> bool:
    # run_self_play_game plays board A on even plies, board B on odd.
    # TEAM A = White-on-A + Black-on-B.
    return (ply % 2 == 0) == (board.turn == chess.WHITE)


def two_agent_dispatch(agent_x, agent_y, *, x_is_team_a: bool, opening_seed: int,
                       opening_plies: int = OPENING_PLIES):
    """Build the per-ply move picker for a two-agent game: `opening_plies`
    seeded-random moves, then `agent_x` on X's team and `agent_y` on the
    other. Returns ``(dispatch, movers)`` where `dispatch(board) -> Move` is
    passed to `run_self_play_game` and `movers` is a list that grows one
    entry per ply, each ``"open"`` / ``"x"`` / ``"y"`` naming who moved."""
    opening = make_random_agent(seed=opening_seed)
    team_a_agent = agent_x if x_is_team_a else agent_y
    team_b_agent = agent_y if x_is_team_a else agent_x
    movers: list[str] = []

    def dispatch(board):
        ply = len(movers)
        if ply < opening_plies:
            movers.append("open")
            return opening(board)
        team_a = _team_a_to_move(ply, board)
        movers.append("x" if team_a == x_is_team_a else "y")
        return (team_a_agent if team_a else team_b_agent)(board)

    return dispatch, movers


def play_game(agent_x, agent_y, *, x_is_team_a: bool, opening_seed: int,
              opening_plies: int = OPENING_PLIES, max_plies: int = MAX_PLIES,
              on_move=None) -> str:
    """Play one game; return 'x', 'y', or 'draw'. `on_move(ply, board, move)`
    is forwarded to `run_self_play_game` for logging/inspection."""
    game = BughouseGame()
    game.assign_roles()
    dispatch, _ = two_agent_dispatch(agent_x, agent_y, x_is_team_a=x_is_team_a,
                                     opening_seed=opening_seed, opening_plies=opening_plies)
    game.run_self_play_game(dispatch, max_moves=max_plies, on_move=on_move)

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


def _bt_ratings(specs, total_wins, games_matrix, *, prior_games=2.0,
                iters=1000, tol=1e-10) -> dict:
    """Bradley-Terry strengths from a round-robin, solved by MM iteration,
    converted to Elo (mean 0). `total_wins[i]` counts draws as half. A light
    `prior_games` (a virtual 50%% opponent at strength 1) keeps an unbeaten
    or winless agent's rating finite."""
    n = len(specs)
    w = [total_wins[i] + prior_games / 2.0 for i in range(n)]
    p = [1.0] * n
    for _ in range(iters):
        nxt = []
        for i in range(n):
            denom = prior_games / (p[i] + 1.0)
            for j in range(n):
                if j != i and games_matrix[i][j]:
                    denom += games_matrix[i][j] / (p[i] + p[j])
            nxt.append(w[i] / denom)
        gm = math.exp(sum(math.log(x) for x in nxt) / n)
        nxt = [x / gm for x in nxt]
        if max(abs(a - b) for a, b in zip(nxt, p)) < tol:
            p = nxt
            break
        p = nxt
    return {s: round(400.0 * math.log10(p[i]), 1) for i, s in enumerate(specs)}


@dataclass
class TournamentResult:
    specs: list
    records: dict          # (spec_i, spec_j) with i<j in `specs` order -> MatchRecord
    ratings: dict          # spec -> Elo (mean 0)
    totals: dict           # spec -> (wins, draws, losses) aggregated over all its games

    def __str__(self) -> str:
        order = sorted(self.specs, key=lambda s: self.ratings[s], reverse=True)
        width = max(len(s) for s in self.specs)
        lines = [f"{'agent':<{width}}    Elo   score   W-D-L (all games)"]
        for s in order:
            wi, di, li = self.totals[s]
            g = wi + di + li
            pct = (wi + 0.5 * di) / g if g else 0.0
            lines.append(f"{s:<{width}}  {self.ratings[s]:+6.0f}  {pct:5.1%}   "
                         f"{wi}-{di}-{li}")
        return "\n".join(lines)


def run_round_robin(specs, *, games_per_pair: int = 8, seed: int = 0,
                    opening_plies: int = OPENING_PLIES, max_plies: int = MAX_PLIES,
                    on_match=None) -> TournamentResult:
    """Every unordered pair of `specs` plays `games_per_pair` games (sides
    swapped each game, deterministic per `seed`). Returns pairwise
    `MatchRecord`s, per-agent W/D/L totals, and Bradley-Terry Elo ratings.
    `on_match(spec_i, spec_j, record)` fires after each pair."""
    specs = list(specs)
    n = len(specs)
    records: dict = {}
    totals = {s: [0, 0, 0] for s in specs}
    games_matrix = [[0] * n for _ in range(n)]
    wins_vec = [0.0] * n

    for a in range(n):
        for b in range(a + 1, n):
            si, sj = specs[a], specs[b]
            # unique per-pair seed so pairs don't share the same games
            rec = play_match(si, sj, games=games_per_pair, seed=seed + 1000 * (a * n + b),
                             opening_plies=opening_plies, max_plies=max_plies)
            records[(si, sj)] = rec
            totals[si][0] += rec.wins;   totals[si][1] += rec.draws; totals[si][2] += rec.losses
            totals[sj][0] += rec.losses; totals[sj][1] += rec.draws; totals[sj][2] += rec.wins
            games_matrix[a][b] = games_matrix[b][a] = rec.games
            wins_vec[a] += rec.wins + 0.5 * rec.draws
            wins_vec[b] += rec.losses + 0.5 * rec.draws
            if on_match is not None:
                on_match(si, sj, rec)

    ratings = _bt_ratings(specs, wins_vec, games_matrix)
    return TournamentResult(specs, records, ratings,
                            {s: tuple(totals[s]) for s in specs})
