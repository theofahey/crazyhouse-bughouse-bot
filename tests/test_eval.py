import chess
from engine.board import BughouseGame
from engine import eval

#Tests that evaluate functions as expected

def test_score_pieces():
    #Tests that the eval sums all the points on the board correctly. 
    game = BughouseGame()
    board_a = game.board_a
    board_b = game.board_b
    assert eval.score_pieces(board_a) == 0.0
    assert eval.score_pieces(board_b) == 0.0

    board_a.push_san("e4")
    board_a.push_san("e5")
    board_b.push_san("e4")
    board_b.push_san("d5")
    board_b.push_san("exd5")

    assert eval.score_pieces(board_a) == 1.0 #Currently white's turn, and white has an extra pawn in its pocket.
    assert eval.score_pieces(board_b) == -1.0 #Black's turn, and white took one of his pawns. 

    board_a.push_san("Nf3")
    board_a.push_san("Nc6")
    board_a.push_san("Nxe5")
    board_a.push_san("Nxe5")

    assert eval.score_pieces(board_a) == -1.5 # White's turn, has one pawn in pocket and has captured a pawn but is missing a knight
    assert eval.score_pieces(board_b) == 1.5 #Black's turn, is down a pawn but has a knight in pocket

    board_a.push_san("h3")

    assert eval.score_pieces(board_a) == 1.5 #Black's turn, up a knight but white has a pawn in its pocket


