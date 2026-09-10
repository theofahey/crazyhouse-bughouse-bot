"""
Day 1, task 2 target. python-chess's CrazyhouseBoard is trusted as-is (it's
a well-tested library, not something we need to re-verify move-by-move) --
these tests only cover the bughouse-specific behavior we're adding on top:
diagonal pocket routing on capture.
"""

import pytest
import chess
from engine.board import BughouseGame

import search.random_agent as random_agent
import search.mcts as mcts

TOTAL_NON_KING_PIECES = 60


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
    assert len(board_a.pockets[chess.BLACK]) == 0
    assert len(board_a.pockets[chess.WHITE]) == 1
    assert len(board_b.pockets[chess.BLACK]) == 0
    assert len(board_b.pockets[chess.WHITE]) == 0
    assert board_a.pockets[chess.WHITE].count(chess.KNIGHT) == 1


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

def _non_king_piece_count(game: BughouseGame) -> int:
    """Total non-king pieces across both boards AND both pockets on each
    board. Should be an invariant -- nothing in bughouse ever creates or
    destroys a piece, only moves it between board and pocket, or changes
    its owning color/type. If this ever isn't 60, something in the
    capture/drop/routing pipeline dropped or duplicated a piece."""
    total = 0
    for board in (game.board_a, game.board_b):
        total += chess.popcount(board.occupied & ~board.kings)
        total += len(board.pockets[chess.WHITE])
        total += len(board.pockets[chess.BLACK])
    return total


def test_material_conserved_throughout_random_game():
    """Stronger than the test above: checks the conservation invariant
    after every single move, not just at the end, so a failure points at
    roughly which move introduced the bug rather than just 'somewhere'."""
    game = BughouseGame()
    boards = [game.board_a, game.board_b]

    assert _non_king_piece_count(game) == TOTAL_NON_KING_PIECES

    agent = random_agent.make_random_agent(seed=0)
    moves_played = 0
    while not game.winner()[0] and moves_played < 300:
        board = boards[moves_played % 2]
        move = agent(board)
        game.on_move_made(board, move)
        moves_played += 1

        assert _non_king_piece_count(game) == TOTAL_NON_KING_PIECES, (
            f"piece count invariant broken after move {moves_played}"
        )

def test_run_self_play_game_with_random_agent():
    # A random game essentially always reaches a terminal state well before
    # the cap; hitting max_moves without error is possible but vanishingly
    # unlikely. Seeded so any failure reproduces.
    game = BughouseGame()
    agent = random_agent.make_random_agent(seed=0)
    num_turns, res = game.run_self_play_game(agent, max_moves=1000)
    assert num_turns < 1000
    assert game.winner()[0]

def test_run_self_play_game_with_mcts_agent():
    # Fast smoke test: the MCTS agent plays legal moves through the harness
    # without crashing and conserves material. MCTS has no RNG, so this is
    # deterministic -- but assertions stay structural, not pinned to the
    # current eval's exact result. The full-length game lives in the
    # slow-marked test below.
    game = BughouseGame()
    game.assign_roles()
    agent = mcts.make_mcts_agent(iterations=120)
    num_turns, res = game.run_self_play_game(agent, max_moves=80)

    assert 1 <= num_turns <= 80
    assert _non_king_piece_count(game) == TOTAL_NON_KING_PIECES
    over, msg = game.winner()
    # winner()[1] is a human-readable result string (or None); run_self_play_game
    # hands it back as `res`. If the game ended before the cap it must be terminal
    # with a message.
    assert res == msg
    if num_turns < 80:
        assert over and isinstance(msg, str)


@pytest.mark.slow
def test_mcts_self_play_full_game():
    # Fuller exercise: a complete game at a realistic iteration budget.
    # Skipped by default (see pyproject addopts); run with `pytest -m slow`.
    game = BughouseGame()
    game.assign_roles()
    agent = mcts.make_mcts_agent(iterations=800)
    num_turns, res = game.run_self_play_game(agent, max_moves=200)

    assert num_turns <= 200
    assert game.winner()[0], "expected the game to reach a terminal state"
    assert _non_king_piece_count(game) == TOTAL_NON_KING_PIECES

