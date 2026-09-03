import pytest
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
    board_a.push_san("Nf3")

    assert eval.score_pieces(board_a, board_a.turn) == PIECE_VALUES["pawn"] #Currently white's turn, and black has an extra pawn in its pocket.
    assert eval.score_pieces(board_b, board_b.turn) == -PIECE_VALUES["pawn"] #Black's turn, and white took one of his pawns. 


    board_a.push_san("Nc6")
    board_a.push_san("Nxe5")
    board_a.push_san("Nxe5")

    assert eval.score_pieces(board_a, board_a.turn) == PIECE_VALUES["pawn"] - PIECE_VALUES["knight"] - PIECE_VALUES["pawn"] # White's turn, has one pawn in pocket and has captured a pawn but is missing a knight
    assert eval.score_pieces(board_b, board_b.turn) == - PIECE_VALUES["knight"]  #Black's turn, is down a pawn but has a knight in pocket

    board_a.push_san("h3")


# --- evaluate() -------------------------------------------------------------
#
# evaluate() == score_pieces(side to move) + king_term, where king_term
# weights the two _king_vulnerability() readings by the moving seat's role.
# own_danger hurts us, opp_danger helps us:
#     defender : -1.5 * own_danger + 0.3 * opp_danger
#     attacker : -0.5 * own_danger + 1.5 * opp_danger

# White king walked out to e4, black rook raking the d-file, black king
# tucked behind its pawns. Equal material except Black is up the rook
# -> own_danger > 0, opp_danger == 0.
_OWN_KING_EXPOSED_FEN = "3r2k1/ppp2ppp/8/8/4K3/8/PPP2PPP/8 w - - 0 1"

# Vertical mirror: now it's BLACK's king exposed on e5 with a white rook
# raking the d-file, white king safe on g1, White to move
# -> own_danger == 0, opp_danger > 0.
_OPP_KING_EXPOSED_FEN = "8/ppp2ppp/8/4k3/8/8/PPP2PPP/3R2K1 w - - 0 1"


def _board_with_roles(fen=None, roles=None):
    game = BughouseGame()
    game.assign_roles()
    board = game.board_a
    if fen is not None:
        board.set_fen(fen)
    if roles is not None:
        board.roles = roles
    return board


def test_assign_roles_maps_every_seat_to_its_team():
    # Regression: board_b's Black seat is on TEAM A, so it must take
    # team_a_roles[1], not team_b_roles[1].
    game = BughouseGame()
    game.assign_roles(team_a_roles=("attacker", "attacker"),
                      team_b_roles=("defender", "defender"))
    assert game.board_a.roles[chess.WHITE] == "attacker"   # White on A -> TEAM A
    assert game.board_b.roles[chess.BLACK] == "attacker"   # Black on B -> TEAM A
    assert game.board_a.roles[chess.BLACK] == "defender"   # Black on A -> TEAM B
    assert game.board_b.roles[chess.WHITE] == "defender"   # White on B -> TEAM B


@pytest.mark.parametrize("role", ["attacker", "defender"])
def test_evaluate_start_position_is_balanced(role):
    board = _board_with_roles(roles={chess.WHITE: role, chess.BLACK: role})
    assert eval.evaluate(board) == pytest.approx(0.0)


def test_evaluate_is_material_plus_role_weighted_king_term():
    board = _board_with_roles(_OWN_KING_EXPOSED_FEN)
    own = eval._king_vulnerability(board, board.turn)
    opp = eval._king_vulnerability(board, not board.turn)
    material = eval.score_pieces(board, chess.WHITE)
    assert own > 0 and opp == 0

    board.roles[chess.WHITE] = "defender"
    assert eval.evaluate(board) == pytest.approx(material - 1.5 * own + 0.3 * opp)

    board.roles[chess.WHITE] = "attacker"
    assert eval.evaluate(board) == pytest.approx(material - 0.5 * own + 1.5 * opp)


def test_opponent_king_danger_helps_the_side_to_move():
    board = _board_with_roles(_OPP_KING_EXPOSED_FEN)
    own = eval._king_vulnerability(board, board.turn)
    opp = eval._king_vulnerability(board, not board.turn)
    material = eval.score_pieces(board, chess.WHITE)
    assert own == 0 and opp > 0

    board.roles[chess.WHITE] = "defender"
    defender_eval = eval.evaluate(board)
    board.roles[chess.WHITE] = "attacker"
    attacker_eval = eval.evaluate(board)

    # opp_danger is ADDED, not subtracted: exposing the enemy king raises
    # our eval above the bare material count under either role...
    assert defender_eval == pytest.approx(material + 0.3 * opp)
    assert attacker_eval == pytest.approx(material + 1.5 * opp)
    assert defender_eval > material
    assert attacker_eval > material
    # ...and an attacker cashes in on it harder than a defender.
    assert attacker_eval > defender_eval


def test_attacker_discounts_own_king_danger_relative_to_defender():
    defender = _board_with_roles(_OWN_KING_EXPOSED_FEN,
                                 {chess.WHITE: "defender", chess.BLACK: "defender"})
    attacker = _board_with_roles(_OWN_KING_EXPOSED_FEN,
                                 {chess.WHITE: "attacker", chess.BLACK: "defender"})
    own = eval._king_vulnerability(defender, chess.WHITE)
    # Only own_danger is in play here; the attacker/defender own-king
    # coefficients differ by exactly 1.0, so the eval gap is one own_danger.
    assert eval.evaluate(attacker) - eval.evaluate(defender) == pytest.approx(own)


# def test_pocket_material_increases_diagonal_vulnerability():
    # Tests that pocket contents will increase


