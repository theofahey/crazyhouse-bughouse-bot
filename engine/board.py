"""
TODO (Day 1, task 2): override _push_capture on BughouseBoard so it adds to
self.partner's pocket instead of self's own. Work out the destination color
expression yourself before looking anything up -- given the diagonal
pairing, and given that the base class's `self.pockets[self.turn]` is
already known to resolve to "the color that just captured" (verified
above), what expression on the PARTNER board gets you their pocket?
"""

from search import mcts
import chess
import chess.variant as variant


class BughouseBoard(variant.CrazyhouseBoard):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.partner: "BughouseBoard | None" = None  # linked by BughouseGame
        self.position_counts = {} #For determining 3-fold repetition

    def _push_capture(self, move, capture_square, piece_type, was_promoted):
        if was_promoted: 
            self.partner.pockets[not self.turn].add(chess.PAWN)
        else:
            self.partner.pockets[not self.turn].add(piece_type)
    
    def push_tracked(self, move: chess.Move) -> None: 
        self.push(move)
        key = self.epd()
        self.position_counts[key] = self.position_counts.get(key, 0) + 1

    def copy(self, *, stack=True) -> "BughouseBoard":
        new_self = variant.CrazyhouseBoard.copy(self, stack=stack)
        new_self.position_counts = dict(self.position_counts)  #Copy Move History
        if self.partner is not None:
            # Call the PARENT's copy directly on partner, not partner.copy() --
            # that would recurse into this same override via partner's own
            # .partner (which is self), infinitely.
            new_partner = variant.CrazyhouseBoard.copy(self.partner, stack=stack)
            new_self.partner = new_partner
            new_partner.partner = new_self
        else:
            new_self.partner = None
        return new_self
    
    def is_over_board(self) -> tuple[bool, int]:
        if self.is_checkmate():
            return (True, int(not self.turn))
        if self.is_stalemate():
            return (True, 2)
        if max(self.position_counts.values(), default=0) >= 3:
            return (True, 3)
        return (False, None)

    def refresh_opportunity_score(self):
        pass

class BughouseGame:
    """Owns the two linked boards. Turn/clock coordination TBD -- see the
    open questions in the project notes before building this out further."""

    def __init__(self):
        self.board_a = BughouseBoard()
        self.board_b = BughouseBoard()
        self.board_a.partner = self.board_b
        self.board_b.partner = self.board_a

    def winner(self) -> tuple[bool, str | None]: 
        """
        TEAM_A = White on Board A + Black on Board B
        TEAM_B = Black on Board A + White on Board B 
        """
        for board, label in ((self.board_a, 'A') , (self.board_b, 'B')):
            over , res  = board.is_over_board()
            if over: 
                if label == 'A' and res == 1:
                    return (True,"TEAM A (" +f"\033[4m{"White on A"}\033[0m"  ", Black on B) WINS!")
                elif label == 'B' and res == 0:
                    return (True,"TEAM A (White on A, " + f"\033[4m{"Black on B"}\033[0m" + ") WINS!")
                elif label == 'A' and res == 0:
                    return (True,"TEAM A (White on B, " + f"\033[4m{"Black on A"}\033[0m" + ") WINS!")
                elif label == 'B' and res == 1:
                    return (True,"TEAM A (" +f"\033[4m{"White on B"}\033[0m"  ", Black on A) WINS!")
                elif res == 2:
                    return (True, "DRAW (Stalemate)")
                elif res == 3:
                    return (True, "DRAW (Repetition)")
                else:
                    return "UNKNOWN RESULT"

        return (False, None)

    def on_move_made(self, board: BughouseBoard, move: chess.Move) -> None:
        board.push_tracked(move)
        board.refresh_opportunity_score()
    

    def run_self_play_game(self, move: chess.Move, max_moves: int = 500) -> int:
        boards = [self.board_a, self.board_b]
        turn = 0
        over = 0
        res = None
        while not over and turn < max_moves:
            current_board = boards[turn%2]
            next_move = move(current_board)
            self.on_move_made(current_board, next_move)
            turn += 1 #Alternates board turns, i.e moves on board 1 first then moves on board 2
            over, res = self.winner()
        return (turn, res)
        
