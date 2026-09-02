import chess
from engine.board import BughouseGame
from engine import eval
from engine.eval import PIECE_VALUES

#Tests that evaluate functions as expected

def test_score_pieces():
    #Tests that the eval sums all the points on the board correctly. 
    game = BughouseGame()
    game.assign_roles()
    board_a = game.board_a
    board_b = game.board_b
    assert eval.score_pieces(board_a, board_a.turn) == 0.0
    assert eval.score_pieces(board_b, board_b.turn) == 0.0

    board_a.push_san("e4")
    board_a.push_san("e5")
    board_b.push_san("e4")
    board_b.push_san("d5")
    board_b.push_san("exd5")

    assert eval.score_pieces(board_a, board_a.turn) == PIECE_VALUES["pawn"] #Currently white's turn, and white has an extra pawn in its pocket.
    assert eval.score_pieces(board_b, board_b.turn) == -PIECE_VALUES["pawn"] #Black's turn, and white took one of his pawns. 

    board_a.push_san("Nf3")
    board_a.push_san("Nc6")
    board_a.push_san("Nxe5")
    board_a.push_san("Nxe5")

    assert eval.score_pieces(board_a, board_a.turn) == 2 * PIECE_VALUES["pawn"] - PIECE_VALUES["knight"] # White's turn, has one pawn in pocket and has captured a pawn but is missing a knight
    assert eval.score_pieces(board_b, board_b.turn) == PIECE_VALUES["knight"] - 2 * PIECE_VALUES["pawn"] #Black's turn, is down a pawn but has a knight in pocket

    board_a.push_san("h3")

    assert eval.score_pieces(board_a, board_a.turn) ==  PIECE_VALUES["knight"] - 2* PIECE_VALUES["pawn"] #Black's turn, up a knight but white has a pawn in its pocket and an extra pawn

# def test_pocket_material_increases_diagonal_vulnerability():
    # Tests that pocket contents will increase 


