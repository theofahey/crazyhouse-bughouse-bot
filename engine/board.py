"""
TODO (Day 1, task 2): override _push_capture on BughouseBoard so it adds to
self.partner's pocket instead of self's own. Work out the destination color
expression yourself before looking anything up -- given the diagonal
pairing, and given that the base class's `self.pockets[self.turn]` is
already known to resolve to "the color that just captured" (verified
above), what expression on the PARTNER board gets you their pocket?
"""

import chess
import chess.variant as variant


class BughouseBoard(variant.CrazyhouseBoard):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.partner: "BughouseBoard | None" = None  # linked by BughouseGame

    def _push_capture(self, move, capture_square, piece_type, was_promoted):
        if was_promoted: 
            self.partner.pockets[not self.turn].add(chess.PAWN)
        else:
            self.partner.pockets[not self.turn].add(piece_type)


class BughouseGame:
    """Owns the two linked boards. Turn/clock coordination TBD -- see the
    open questions in the project notes before building this out further."""

    def __init__(self):
        self.board_a = BughouseBoard()
        self.board_b = BughouseBoard()
        self.board_a.partner = self.board_b
        self.board_b.partner = self.board_a
