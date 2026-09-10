"""1-ply greedy agent: play the move that maximises evaluate() of the
resulting position, from our own perspective.

evaluate(board) is scored from the side-to-move's perspective. After we push
our move it's the opponent to move, so evaluate(child) is from THEIR
perspective -- negate it to get ours. Terminal children are handled directly
(evaluate() is only valid on non-terminal positions): a move that delivers
mate wins outright; a move that forces stalemate/repetition is a draw.

Deterministic (no RNG): ties broken by move.uci(). Useful as a cheap
benchmark opponent in the arena and as a regression canary for eval changes.
"""

import chess

from engine.board import BughouseBoard
from engine.eval import evaluate


def pick_move(board: BughouseBoard) -> chess.Move:
    best_move = None
    best_score = None
    for move in board.legal_moves:
        child = board.copy()
        child.push(move)
        over, res = child.is_over_board()
        if over:
            score = float("inf") if res in (0, 1) else 0.0  # (0,1) = checkmate we just delivered
        else:
            score = -evaluate(child)
        if (best_score is None
                or score > best_score
                or (score == best_score and move.uci() < best_move.uci())):
            best_move, best_score = move, score
    return best_move


def make_greedy_agent():
    """Return a ``(board) -> Move`` 1-ply argmax-of-evaluate agent."""
    return pick_move
