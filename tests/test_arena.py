import pytest

from search.arena import build_agent, elo_delta, play_match


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


@pytest.mark.slow
def test_mcts_outscores_random():
    rec = play_match("mcts:200", "random", games=6, seed=0)
    assert rec.wins > rec.losses
