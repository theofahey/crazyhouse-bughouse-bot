"""
Crazyhouse board representation.

Wraps python-chess's Board and adds the piece reserve ("pieces in hand")
needed for drop moves. Standard chess.Board already tracks position and
legal moves for regular chess moves -- what we need to add:

  1. A reserve: dict[chess.Color, dict[chess.PieceType, int]] tracking how
     many of each piece type each side can drop.
  2. When a piece is captured, it should be added to the CAPTURING side's
     reserve (as its own color, and demoted to a pawn if it was promoted --
     this is a real crazyhouse/bughouse rule, not just bughouse).
  3. Drop moves aren't representable by chess.Move directly, so we'll need
     our own move representation (or encode drops as a special UCI-like
     string, e.g. "P@e4" for "drop a pawn on e4" -- this is the convention
     python-chess-variant engines and lichess both use).

TODO (first task): implement CrazyhouseBoard.__init__ and reserve tracking.
"""

import chess


class CrazyhouseBoard:
    def __init__(self):
        self.board = chess.Board()
        # TODO: reserve[color][piece_type] -> count
        self.reserve = None

    def legal_drops(self, color: chess.Color) -> list:
        """Return legal drop squares for pieces currently in `color`'s reserve.

        Rules to encode here:
          - No pawn drops on rank 1 or rank 8
          - Target square must be empty
          - (later) a drop that doesn't resolve check is illegal, same as
            any other move
        """
        raise NotImplementedError

    def push_drop(self, piece_type: chess.PieceType, square: chess.Square):
        """Apply a drop move: remove one piece_type from reserve, place it."""
        raise NotImplementedError
