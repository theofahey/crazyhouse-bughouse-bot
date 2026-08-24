"""
Day 1, task 2 target. python-chess's CrazyhouseBoard is trusted as-is (it's
a well-tested library, not something we need to re-verify move-by-move) --
these tests only cover the bughouse-specific behavior we're adding on top:
diagonal pocket routing on capture.
"""

import chess
from engine.board import BughouseGame
import search.random_agent as random_agent
import search.mcts as mcts



def test_capture_goes_to_partners_pocket_not_own():
    #Tests that a capture by board_a white ends up in board_b black's pocket. 
    game = BughouseGame()
    board_a = game.board_a
    board_b = game.board_b
    board_a.push_san("e4")
    board_a.push_san("d5")
    board_b.push_san("e4")
    board_a.push_san("exd5")
    assert len(board_a.pockets[0]) == 0
    assert len(board_a.pockets[1]) == 0
    assert len(board_b.pockets[1]) == 0
    assert len(board_b.pockets[0]) == 1
    assert board_b.pockets[0].count(chess.PAWN) == 1


def test_black_capture_goes_to_white_partner_pocket():
    # Mirror case: Black-B captures -> should land in White-A's pocket.
    game = BughouseGame()
    board_a = game.board_a
    board_b = game.board_b
    board_b.push_san("e4")
    board_b.push_san("c5")
    board_a.push_san("d4")
    board_a.push_san("d5")
    board_b.push_san("Nf3")
    board_b.push_san("Nc6")
    board_b.push_san("Ne5")
    board_b.push_san("Nxe5")
    assert len(board_a.pockets[0]) == 0
    assert len(board_a.pockets[1]) == 1
    assert len(board_b.pockets[1]) == 0
    assert len(board_b.pockets[0]) == 0
    assert board_a.pockets[1].count(chess.KNIGHT) == 1


def test_promoted_piece_still_reverts_to_pawn_when_routed_to_partner():
    # Same reversion rule as crazyhouse (verified in isolation already),
    # but now the pawn should land in the PARTNER's pocket, not the
    # capturing board's own.
    game = BughouseGame()
    board_a = game.board_a
    board_b = game.board_b
    #Obviously not a realistic game, for the sake of simplicity (Danish Gambit gone wrong I guess)
    board_a.push_san("e4")
    board_a.push_san("e5")
    board_a.push_san("d4")
    board_a.push_san("exd4")
    board_a.push_san("c3")
    board_a.push_san("dxc3")
    board_a.push_san("Bc4")
    board_a.push_san("cxb2")
    board_a.push_san("Nc3")
    board_a.push_san("bxc1=Q")
    board_a.push_san("Qxc1")
    assert len(board_b.pockets[0]) == 1
    assert board_b.pockets[0].count(chess.PAWN) == 1

def test_run_self_play_game_with_random_agent():
    # Will run a round of self play chess with a max steps value of 3,000.
    # Will test to ensure the game reaches an end state, and max_steps hasn't been reached. 
    # It's theoretically possible for max_steps to be reached (without any errors) since moves are chosen randomly but it's essentially impossible
    game = BughouseGame()
    num_turns, res = game.run_self_play_game(random_agent.pick_move, max_moves=1000)
    print(res)
    assert num_turns < 1000
    assert game.winner()[0]

def test_run_self_play_game_with_mcts_agent():
    game = BughouseGame()
    num_turns, res = game.run_self_play_game(mcts.search, max_moves=200)

    print([move.uci() for move in game.board_a.move_stack])
    print([move.uci() for move in game.board_b.move_stack])
    print("----------------------------")

    print(res)
    assert num_turns < 300
    assert game.winner()[0]

    assert False

