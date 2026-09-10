#!/usr/bin/env python3
"""Play one bughouse game and watch it move by move.

One agent or two: `--x` / `--y` take agent specs (mcts:3000, mcts:80, greedy,
random, random:7). With neither, both sides are mcts:<--iterations> (the old
self-play behaviour). Team X is always White-on-A + Black-on-B.

Each ply prints the move plus the state you need to reason about a bughouse
position: eval, both kings' vulnerability, and all four pockets -- so a
partner-board opportunity the mover missed is visible.

Examples:
    python scripts/selfplay.py
    python scripts/selfplay.py --x mcts:3000 --y mcts:80 --seed 1
    python scripts/selfplay.py --x greedy --y random --opening-plies 0
    python scripts/selfplay.py --x mcts:800 --dump-tree h5h7 --out ""
"""

import argparse
import sys
from pathlib import Path

# Run directly (python scripts/selfplay.py) without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chess  # noqa: E402

from engine.board import BughouseGame, pocket_text  # noqa: E402
from engine.eval import _king_vulnerability, evaluate  # noqa: E402
from search.arena import build_agent, two_agent_dispatch  # noqa: E402
from search.mcts import DEFAULT_ITERATIONS, search  # noqa: E402
from search.tree_viz import export_tree_html  # noqa: E402


def _mcts_iters(spec: str) -> int | None:
    """Iteration count if `spec` is an mcts spec, else None."""
    name, _, arg = spec.partition(":")
    if name != "mcts":
        return None
    return int(arg) if arg else DEFAULT_ITERATIONS


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--x", default=None, metavar="SPEC",
                   help="agent for team X (default: mcts:<--iterations>)")
    p.add_argument("--y", default=None, metavar="SPEC",
                   help="agent for team Y (default: same as --x)")
    p.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS,
                   help=f"MCTS iterations when --x/--y are unset (default: {DEFAULT_ITERATIONS})")
    p.add_argument("--opening-plies", type=int, default=0,
                   help="seeded-random plies before the agents take over (default: 0)")
    p.add_argument("--max-moves", type=int, default=200,
                   help="ply cap before the game is abandoned (default: 200)")
    p.add_argument("--seed", type=int, default=0,
                   help="seeds the opening + any random agents (default: 0)")
    p.add_argument("--roles", dest="roles", action="store_true", default=True,
                   help="call BughouseGame.assign_roles() (default: on)")
    p.add_argument("--no-roles", dest="roles", action="store_false")
    p.add_argument("--out", default="saved_games/game_1.json",
                   help="write SAN logs here for the frontend replay tool; pass '' to skip")
    p.add_argument("--dump-tree", dest="dump_tree", action="append", default=[], metavar="UCI",
                   help="when an MCTS agent picks this move, export its tree to "
                        "<UCI>_investigation.html (repeatable)")
    p.add_argument("--quiet", action="store_true", help="suppress per-ply lines")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    x_spec = args.x or f"mcts:{args.iterations}"
    y_spec = args.y or x_spec

    game = BughouseGame()
    if args.roles:
        game.assign_roles()

    agent_x = build_agent(x_spec, fallback_seed=args.seed)
    agent_y = build_agent(y_spec, fallback_seed=args.seed + 10_000)
    dispatch, movers = two_agent_dispatch(
        agent_x, agent_y, x_is_team_a=True,
        opening_seed=args.seed, opening_plies=args.opening_plies,
    )

    dump_targets = set(args.dump_tree)
    spec_iters = {"x": _mcts_iters(x_spec), "y": _mcts_iters(y_spec)}

    def dispatch_and_dump(board):
        move = dispatch(board)          # appends to `movers`; does not mutate `board`
        iters = spec_iters.get(movers[-1])
        if move.uci() in dump_targets and iters:
            _, root = search(board, iters, return_tree=True)
            path = f"{move.uci()}_investigation.html"
            export_tree_html(root, path)
            print(f"  -> wrote {path}")
        return move

    def log(ply, board, move):
        if args.quiet:
            return
        board_label = "A" if ply % 2 == 0 else "B"
        moved = not board.turn  # board is post-move; the mover's colour flipped away
        own_kv = _king_vulnerability(board, moved)
        opp_kv = _king_vulnerability(board, board.turn)
        pockets = (f"Aw:{pocket_text(game.board_a, chess.WHITE)} "
                   f"Ab:{pocket_text(game.board_a, chess.BLACK)} "
                   f"Bw:{pocket_text(game.board_b, chess.WHITE)} "
                   f"Bb:{pocket_text(game.board_b, chess.BLACK)}")
        print(f"{ply:3} {board_label} {movers[ply]:4} {board.san_log[-1]:7} "
              f"eval(stm)={evaluate(board):+.2f} "
              f"Kvuln own/opp={own_kv:.2f}/{opp_kv:.2f}   {pockets}")

    num_turns, _ = game.run_self_play_game(
        dispatch_and_dump, max_moves=args.max_moves, on_move=log
    )

    over, msg = game.winner()
    outcome = game.result()  # 'A' | 'B' | 'draw' | None  (X is always team A here)
    x_result = {"A": "X wins", "B": "Y wins", "draw": "draw",
                None: "unfinished (hit --max-moves)"}[outcome]
    print("-" * 72)
    print(f"X = {x_spec}    Y = {y_spec}")
    print(f"plies: {num_turns}   {msg if over else 'unfinished'}   ->  {x_result}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        game.save_game_logs(str(out))
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
