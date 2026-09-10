import chess
import pytest

from engine.board import BughouseGame
from search.greedy_agent import pick_move


def _board(fen: str):
    game = BughouseGame()
    game.assign_roles()
    game.board_a.set_fen(fen)
    return game.board_a


def test_takes_a_free_queen():
    # White pawn e4 can grab the undefended black queen on d5.
    board = _board("4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1")
    assert pick_move(board).uci() == "e4d5"


def test_plays_mate_in_one():
    # Ra1-a8 is back-rank mate; the pawns wall the black king in.
    board = _board("7k/5ppp/8/8/8/8/5PPP/R6K w - - 0 1")
    assert pick_move(board).uci() == "a1a8"


def test_is_deterministic():
    fen = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1"
    board = _board(fen)
    assert pick_move(board) == pick_move(_board(fen))


@pytest.mark.slow
def test_greedy_outscores_random():
    from search.arena import play_match

    rec = play_match("greedy", "random", games=6, seed=0)
    assert rec.wins > rec.losses
