#!/usr/bin/env python3
"""Round-robin tournament between several agent configs; print an Elo table.

Every unordered pair plays --games games (sides swapped, deterministic per
--seed). Ratings are Bradley-Terry, mean 0.

Examples:
    python scripts/ladder.py --agents mcts:80 mcts:200 mcts:800 --games 8
    python scripts/ladder.py --agents greedy random mcts:400 --games 12 --seed 1
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search.arena import OPENING_PLIES, run_round_robin  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--agents", nargs="+", required=True, metavar="SPEC",
                   help="agent specs, e.g. mcts:80 mcts:800 greedy random")
    p.add_argument("--games", type=int, default=8, help="games per pair (default: 8)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--opening-plies", type=int, default=OPENING_PLIES,
                   help=f"seeded-random plies before the agents take over (default {OPENING_PLIES})")
    p.add_argument("--quiet", action="store_true", help="suppress per-match progress")
    args = p.parse_args(argv)

    def on_match(si, sj, rec):
        if not args.quiet:
            print(f"  {si} vs {sj}: +{rec.wins} ={rec.draws} -{rec.losses}  "
                  f"(Elo Δ {rec.elo:+.0f})")

    result = run_round_robin(
        args.agents, games_per_pair=args.games, seed=args.seed,
        opening_plies=args.opening_plies, on_match=on_match,
    )
    print("-" * 60)
    print(result)


if __name__ == "__main__":
    main()
