#!/usr/bin/env python3
"""Play a match between two agent configs; print W/D/L and a rough Elo delta.

Examples:
    python scripts/arena.py --x mcts:800 --y random --games 20
    python scripts/arena.py --x mcts:800 --y mcts:200 --games 40 --seed 1
    python scripts/arena.py --x mcts:400 --y random --games 10 --quiet
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search.arena import OPENING_PLIES, play_match  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--x", required=True, help="agent spec: mcts:800, random, random:7, ...")
    p.add_argument("--y", required=True, help="opponent agent spec")
    p.add_argument("--games", type=int, default=20)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--opening-plies", type=int, default=OPENING_PLIES,
                   help=f"seeded-random plies before the agents take over (default {OPENING_PLIES})")
    p.add_argument("--quiet", action="store_true", help="suppress per-game progress")
    args = p.parse_args(argv)

    def on_game(i, r, w, d, l):
        if not args.quiet:
            print(f"  game {i + 1:3}/{args.games}: {r:5} running +{w} ={d} -{l}")

    rec = play_match(args.x, args.y, games=args.games, seed=args.seed,
                     opening_plies=args.opening_plies, on_game=on_game)
    print("-" * 50)
    print(rec)


if __name__ == "__main__":
    main()
