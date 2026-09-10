"""An *agent* is any callable ``(BughouseBoard) -> chess.Move``. This module
holds the trivial uniform-random one."""

import random
import chess

from engine.board import BughouseBoard


def pick_move(board: BughouseBoard) -> chess.Move:
    """Uniform-random legal move, drawn from the global ``random`` state."""
    return random.choice(list(board.legal_moves))


def make_random_agent(seed: int | None = None):
    """Return a ``(board) -> Move`` agent with its own RNG, so games are
    reproducible and independent of the global ``random`` state."""
    rng = random.Random(seed)

    def agent(board: BughouseBoard) -> chess.Move:
        return rng.choice(list(board.legal_moves))

    return agent
