import statistics

import pytest

from engine.board import BughouseGame
from search import mcts


def _board(fen: str):
    game = BughouseGame()
    game.assign_roles()
    game.board_a.set_fen(fen)
    return game.board_a


FREE_QUEEN = "4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1"   # e4xd5 wins the queen
BACK_RANK_MATE = "7k/5ppp/8/8/8/8/5PPP/R6K w - - 0 1"  # Ra1-a8#


def test_finds_the_free_capture():
    assert mcts.search(_board(FREE_QUEEN), 300).uci() == "e4d5"


def test_finds_mate_in_one():
    assert mcts.search(_board(BACK_RANK_MATE), 300).uci() == "a1a8"


def test_visits_concentrate_on_the_best_move():
    # Post-A.6: selection is normalised + progressively widened, so a clearly
    # best move should dominate the visit count -- not the old near-uniform
    # spread where 80 iters == 1000 iters.
    _, root = mcts.search(_board(FREE_QUEEN), 400, return_tree=True)
    by_visits = sorted((c.visits for c in root.children), reverse=True)
    assert by_visits[0] >= 3 * by_visits[1]


def test_more_iterations_sharpen_the_pick():
    _, root = mcts.search(_board(FREE_QUEEN), 600, return_tree=True)
    best = max(root.children, key=lambda c: c.visits)
    others = statistics.median(c.visits for c in root.children if c is not best)
    assert best.visits >= 5 * others


@pytest.mark.slow
def test_more_budget_plays_stronger():
    # Pre-A.6 this was a coin flip (mcts:80 ~= mcts:1000). Post-A.6 the
    # bigger budget should win the match.
    from search.arena import play_match

    rec = play_match("mcts:400", "mcts:60", games=8, seed=0)
    assert rec.wins > rec.losses
