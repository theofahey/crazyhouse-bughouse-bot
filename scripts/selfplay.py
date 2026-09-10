#!/usr/bin/env python3
"""Run an MCTS self-play game and inspect it.

Replaces the old habit of editing tests/test_bughouse_logic.py to add prints,
regenerate saved_games/game_1.json, and export an MCTS search tree.

Examples:
    python scripts/selfplay.py
    python scripts/selfplay.py --seed 1 --iterations 800 --max-moves 200
    python scripts/selfplay.py --dump-tree h5h7 --dump-tree e2e4
    python scripts/selfplay.py --out ""          # analyse only, write nothing
"""

import argparse
import sys
from pathlib import Path

# Run directly (python scripts/selfplay.py) without installing the package:
# put the repo root on the path so `engine` / `search` import.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.board import BughouseGame  # noqa: E402
from engine.eval import evaluate  # noqa: E402
from search.mcts import DEFAULT_ITERATIONS, search  # noqa: E402
from search.tree_viz import export_tree_html  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS,
                   help=f"MCTS simulations per move (default: {DEFAULT_ITERATIONS})")
    p.add_argument("--max-moves", type=int, default=200,
                   help="ply cap before the game is abandoned (default: 200)")
    p.add_argument("--seed", type=int, default=None,
                   help="unused by MCTS (no RNG); reserved for future stochastic agents")
    p.add_argument("--roles", dest="roles", action="store_true", default=True,
                   help="call BughouseGame.assign_roles() (default: on)")
    p.add_argument("--no-roles", dest="roles", action="store_false")
    p.add_argument("--out", default="saved_games/game_1.json",
                   help="write SAN logs here for the frontend replay tool; pass '' to skip")
    p.add_argument("--dump-tree", dest="dump_tree", action="append", default=[], metavar="UCI",
                   help="when this move is chosen, export its tree to <UCI>_investigation.html (repeatable)")
    p.add_argument("--quiet", action="store_true", help="suppress per-ply lines")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    game = BughouseGame()
    if args.roles:
        game.assign_roles()

    dump_targets = set(args.dump_tree)

    def agent(board):
        # return_tree so a --dump-tree hit can export the tree that produced
        # this move; the root is only available here, pre-push.
        move, root = search(board, args.iterations, return_tree=True)
        if move.uci() in dump_targets:
            path = f"{move.uci()}_investigation.html"
            export_tree_html(root, path)
            print(f"  -> wrote {path}")
        return move

    def log(ply, board, move):
        if args.quiet:
            return
        # eval is from the side-to-move's perspective at the resulting
        # position (i.e. the opponent on that board), matching what the
        # search sees at that node.
        label = "A" if ply % 2 == 0 else "B"
        print(f"{ply:3} {label} {board.san_log[-1]:8} eval(stm)={evaluate(board):+.3f}")

    num_turns, res = game.run_self_play_game(
        agent, max_moves=args.max_moves, on_move=log
    )

    over, msg = game.winner()
    print("-" * 40)
    print(f"plies: {num_turns}   result: {msg if over else 'unfinished (hit --max-moves)'}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        game.save_game_logs(str(out))
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
