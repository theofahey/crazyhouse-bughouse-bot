"""
Evaluation function.

Standard chess piece values don't directly apply once drops are in play:
  - Knights are often worth more than rooks (knight drops create contact
    checks that can't be blocked by interposing a dropped piece)
  - Pieces in reserve have value too, not just pieces on the board
  - King safety matters more -- diagonal weaknesses are exposed to drops

TODO: start with material count using the weights below, benchmark via
self-play, then layer in king safety / reserve value / mobility.
"""

# Placeholder starting weights -- tune via self-play benchmarking (Phase 0/2).
PIECE_VALUES = {
    "pawn": 1,
    "knight": 3.5,  # bumped up from standard 3 -- drop/contact-check value
    "bishop": 3,
    "rook": 4.5,    # slightly reduced -- less mobile once board fills with drops
    "queen": 9,
}


def evaluate(board) -> float:
    """Return a score from White's perspective. Positive favors White."""
    raise NotImplementedError
