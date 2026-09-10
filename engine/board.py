
import json
import re

from search import mcts
import chess
import chess.variant as variant
import chess.pgn

#For parsing pgn notation to moves.
DROP_PATTERN = re.compile(r'^([PNBRQ]?)@([a-h][1-8])')
DROP_PIECE_TYPES = {
    "": chess.PAWN, "P": chess.PAWN, "N": chess.KNIGHT,
    "B": chess.BISHOP, "R": chess.ROOK, "Q": chess.QUEEN,
}
PIECE_LETTERS = {
    chess.QUEEN: "Q", chess.ROOK: "R", chess.BISHOP: "B",
    chess.KNIGHT: "N", chess.PAWN: "P",
}


def resolve_move(board: "BughouseBoard", san: str) -> chess.Move:
    """Turn a stored SAN token back into a Move, WITHOUT going through
    chess.pgn's board-reconstruction machinery -- that builds a
    disconnected, partner-less board from FEN/Variant headers alone, and
    chokes the instant it hits a drop sourced from cross-board material
    (i.e. most drops in a real bughouse game). Drops are fully
    self-describing text (exact piece, exact square) -- no disambiguation
    needed, so no reason parsing them should ever touch pocket state at
    all. Ordinary moves go through board.parse_san(), which IS safe here:
    disambiguation only depends on piece placement, never pockets, so
    it's unaffected by the cross-board issue entirely."""
    match = DROP_PATTERN.match(san)
    if match:
        letter, square_name = match.groups()
        piece_type = DROP_PIECE_TYPES[letter]
        square = chess.parse_square(square_name)
        return chess.Move(square, square, drop=piece_type)
    return board.parse_san(san)

def pocket_text(board: "BughouseBoard", color: chess.Color) -> str:
    pocket = board.pockets[color]
    letters = []
    for pt in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN):
        letters.append(PIECE_LETTERS[pt] * pocket.count(pt))
    return "".join(letters) or "\u2014"


class BughouseBoard(variant.CrazyhouseBoard):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.partner: "BughouseBoard | None" = None  # linked by BughouseGame
        self.position_counts = {} #For determining 3-fold repetition
        self.roles = {chess.WHITE: "defender", chess.BLACK: "defender"}
        self.san_log = []  # For converting games to pgn files


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
        new_self.roles = dict(self.roles)
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

    def assign_roles(self, team_a_roles=("attacker", "defender"), team_b_roles=("attacker", "defender")):
        """team_x_roles = (role of that team's Board-A seat, role of its Board-B seat).
        TEAM A holds White on A + Black on B; TEAM B holds Black on A + White on B."""
        self.board_a.roles = {chess.WHITE: team_a_roles[0], chess.BLACK: team_b_roles[0]}
        self.board_b.roles = {chess.WHITE: team_b_roles[1], chess.BLACK: team_a_roles[1]}

    def on_move_made(self, board: BughouseBoard, move: chess.Move) -> None:
        san_body = board._algebraic_without_suffix(move) 
        if move.drop == chess.PAWN:
            san_body = "P" + san_body
        board.push_tracked(move)
        if board.is_checkmate():
            san = san_body + "#"
        elif board.is_check():
            san = san_body + '+'
        else:
            san = san_body
        board.san_log.append(san)
        board.refresh_opportunity_score()

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
                    return (True,"TEAM B (White on B, " + f"\033[4m{"Black on A"}\033[0m" + ") WINS!")
                elif label == 'B' and res == 1:
                    return (True,"TEAM B (" +f"\033[4m{"White on B"}\033[0m"  ", Black on A) WINS!")
                elif res == 2:
                    return (True, "DRAW (Stalemate)")
                elif res == 3:
                    return (True, "DRAW (Repetition)")
                else:
                    return "UNKNOWN RESULT"

        return (False, None)
    
    def export_pgn_text(self, match_id: str = "game1") -> tuple[str, str]:
        """Hand-rolled, not chess.pgn -- that machinery reconstructs a
        disconnected board from headers alone and can't replay bughouse
        history correctly. See project notes."""
        result = "*"
        def render(board: "BughouseBoard", label: str) -> str:
            header = f'[Event "Bughouse match {match_id}"]\n[Board "{label}"]\n'f'[Variant "Crazyhouse"]\n'
            f'[Result "{result}"]\n\n'
            moves = []
            for i, san in enumerate(board.san_log):
                if i % 2 == 0:
                    moves.append(f"{i // 2 + 1}.{san}")
                else:
                    moves.append(san)
            return header + " ".join(moves) + f" {result}"

        return render(self.board_a, "A"), render(self.board_b, "B")

    def save_game_logs(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump({"a": self.board_a.san_log, "b": self.board_b.san_log}, f)

    @staticmethod
    def load_game_logs(path: str) -> tuple[list, list]:
        with open(path) as f:
            data = json.load(f)
        return data["a"], data["b"]

    def replay_with_frames(self, san_log_a: list, san_log_b: list) -> list:
        """Replay two stored per-board SAN logs, in true alternating ply
        order, through THIS game's own linked boards -- not chess.pgn's
        board reconstruction. Assumes self.board_a/board_b are freshly
        constructed (no moves played yet). Returns one frame per ply for
        a step-through GUI. Only the SVG of the board that actually moved
        is included per frame (halves the embedded image data versus
        capturing both boards every step); pockets are always included
        for all four seats, since a capture on either board can change
        either board's pocket via cross-board routing."""
        boards = [self.board_a, self.board_b]
        logs = [iter(san_log_a), iter(san_log_b)]
        total_plies = len(san_log_a) + len(san_log_b)

        frames = []
        for i in range(total_plies):
            label = "A" if i % 2 == 0 else "B"
            board = boards[i % 2]
            san = next(logs[i % 2])
            move = resolve_move(board, san)
            self.on_move_made(board, move)

            frames.append({
                "ply": i,
                "board": label,
                "san": board.san_log[-1],
                "svg": chess.svg.board(board, size=360, flipped=(label == "B")),
                "pockets": {
                    "a_w": pocket_text(self.board_a, chess.WHITE),
                    "a_b": pocket_text(self.board_a, chess.BLACK),
                    "b_w": pocket_text(self.board_b, chess.WHITE),
                    "b_b": pocket_text(self.board_b, chess.BLACK),
                },
            })
        return frames

    def run_self_play_game(self, agent, *, max_moves: int = 500, on_move=None) -> tuple[int, int | None]:
        """Play both boards with `agent`, a callable (BughouseBoard) -> Move,
        alternating boards each ply (board A, then board B, then A, ...).

        `on_move(ply, board, move)`, if given, is called after every move --
        a generic observer hook for logging/inspection, with no coupling to
        any particular agent. Returns (plies_played, result_code), where
        result_code is winner()'s second element (None if max_moves hit)."""
        boards = [self.board_a, self.board_b]
        turn = 0
        over = 0
        res = None
        while not over and turn < max_moves:
            current_board = boards[turn % 2]
            next_move = agent(current_board)
            self.on_move_made(current_board, next_move)
            if on_move is not None:
                on_move(turn, current_board, next_move)
            turn += 1
            over, res = self.winner()
        return (turn, res)
        
