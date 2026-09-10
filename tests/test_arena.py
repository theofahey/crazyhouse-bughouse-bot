import chess
import pytest

from search.arena import (
    _bt_ratings,
    build_agent,
    elo_delta,
    play_game,
    play_match,
    run_round_robin,
    two_agent_dispatch,
)


def test_elo_delta_even_record():
    elo, lo, hi = elo_delta(10, 0, 10)
    assert elo == pytest.approx(0.0)
    assert lo < 0 < hi


@pytest.mark.parametrize("w, d, l, expected", [
    (50, 0, 50, 0.0),
    (75, 0, 25, 190.85),   # score 0.75
    (90, 0, 10, 381.70),   # score 0.90
])
def test_elo_delta_known_scores(w, d, l, expected):
    assert elo_delta(w, d, l)[0] == pytest.approx(expected, abs=0.5)


def test_elo_delta_draws_count_half():
    assert elo_delta(0, 100, 0)[0] == pytest.approx(0.0)
    assert elo_delta(20, 60, 20)[0] == pytest.approx(0.0)


def test_elo_delta_saturates_on_clean_sweep():
    assert elo_delta(10, 0, 0)[0] == 800.0
    assert elo_delta(0, 0, 10)[0] == -800.0


def test_build_agent_specs():
    assert callable(build_agent("random"))
    assert callable(build_agent("random:3"))
    assert callable(build_agent("mcts:10"))
    with pytest.raises(ValueError):
        build_agent("bogus")


def test_play_match_is_deterministic_and_tallies():
    kw = dict(games=6, seed=0, opening_plies=2)
    r1 = play_match("random", "random", **kw)
    r2 = play_match("random", "random", **kw)
    assert (r1.wins, r1.draws, r1.losses) == (r2.wins, r2.draws, r2.losses)
    assert r1.wins + r1.draws + r1.losses == 6


def test_play_game_calls_on_move_once_per_ply():
    seen = []
    result = play_game(
        build_agent("random", fallback_seed=1),
        build_agent("random", fallback_seed=2),
        x_is_team_a=True, opening_seed=0, opening_plies=0, max_plies=40,
        on_move=lambda ply, board, move: seen.append((ply, move)),
    )
    assert [ply for ply, _ in seen] == list(range(len(seen)))  # 0,1,2,... contiguous
    assert all(isinstance(move, chess.Move) for _, move in seen)
    assert result in ("x", "y", "draw")


def test_two_agent_dispatch_labels_movers():
    from engine.board import BughouseGame

    game = BughouseGame()
    game.assign_roles()
    dispatch, movers = two_agent_dispatch(
        build_agent("random", fallback_seed=1),
        build_agent("random", fallback_seed=2),
        x_is_team_a=True, opening_seed=0, opening_plies=3,
    )
    game.run_self_play_game(dispatch, max_moves=20)
    assert movers[:3] == ["open", "open", "open"]
    assert set(movers[3:]) <= {"x", "y"}
    # ply 3 = board B, Black to move (White moved on ply 1) -> Black-on-B is team A -> X
    assert movers[3] == "x"


def test_bt_ratings_order_a_beats_b_beats_c():
    # synthetic round-robin: A sweeps B, B sweeps C, A sweeps C
    specs = ["A", "B", "C"]
    games = [[0, 10, 10], [10, 0, 10], [10, 10, 0]]
    total_wins = [20.0, 10.0, 0.0]
    r = _bt_ratings(specs, total_wins, games)
    assert r["A"] > r["B"] > r["C"]
    assert abs(r["A"] + r["B"] + r["C"]) < 1e-6  # mean 0


def test_run_round_robin_is_deterministic_and_ranks_greedy_over_random():
    kw = dict(games_per_pair=4, seed=0, opening_plies=2)
    r1 = run_round_robin(["greedy", "random", "random:1"], **kw)
    r2 = run_round_robin(["greedy", "random", "random:1"], **kw)
    assert r1.ratings == r2.ratings
    assert r1.ratings["greedy"] > r1.ratings["random"]
    # every agent's totals sum to games it played (2 opponents * 4 games)
    for spec, (w, d, l) in r1.totals.items():
        assert w + d + l == 8


@pytest.mark.slow
def test_mcts_outscores_random():
    rec = play_match("mcts:200", "random", games=6, seed=0)
    assert rec.wins > rec.losses
