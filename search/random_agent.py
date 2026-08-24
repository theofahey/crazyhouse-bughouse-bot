import random
import chess

from engine.board import BughouseBoard


def pick_move(board: BughouseBoard) -> chess.Move:
    return random.choice(list(board.legal_moves))
