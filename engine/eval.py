"""
Phase 0 evaluation: plain material count. Nothing fancier yet -- no king
safety, no reserve value, no bughouse-adjusted weights. Those come later,
once there's a working self-play harness to benchmark changes against.

IMPORTANT: this function is only ever called on NON-terminal positions.
Checkmate/stalemate detection is the search's job (board.is_game_over()),
not this function's -- material alone has no way to represent "the game
just ended," and conflating the two is a real, easy-to-miss bug source.
See project notes.
"""
import chess

PIECE_VALUES = {
    "pawn": 1,
    "knight": 2.5,
    "bishop": 3,
    "rook": 4.5,
    "queen": 4,
    "king": 0
}

KING_ZONE_WEIGHTS = {
    "enemy_piece_adjacent": 1,
    "empty_diagonal": 0.5,
    "empty_orthogonal": 0.25,
    "occupied_diagonal": 0.25,   
    "occupied_orthogonal": 0.1,
}

VULNERABILITY_MARGIN = 1 

def evaluate(board) -> float:
    """Return material balance from the CURRENT PLAYER TO MOVE's
    perspective (not always White's) -- positive favors board.turn.
    Include pocket pieces, not just pieces on the board -- a piece in
    hand is still yours, it just hasn't been placed yet.
    """

    current_turn = board.turn #True if white, False if black

    if current_turn:
      player = chess.WHITE
    else:
      player = chess.BLACK
  
    own_danger = _king_vulnerability(board, board.turn)
    opp_danger = _king_vulnerability(board, not board.turn)

    if board.roles[board.turn] == "defender":
      king_term = -1.5 * own_danger - 0.3 * opp_danger
    else:  # attacker
      king_term = -0.5 * own_danger - 1.5 * opp_danger
    return(score_pieces(board, player) + king_term)

def _is_diagonal(king_square: chess.Square, other_square: chess.Square) -> bool:
    file_diff = abs(chess.square_file(king_square) - chess.square_file(other_square))
    rank_diff = abs(chess.square_rank(king_square) - chess.square_rank(other_square))
    return file_diff == 1 and rank_diff == 1

def _king_zone(king_square: chess.Square) -> list[chess.Square]:
  """The up-to-8 squares immediately adjacent to a king. Naturally
  shrinks to 5 on an edge, 3 in a corner -- chess.square()'s bounds
  handle that, no special-casing needed for the edges/corners
  themselves."""

  king_file = chess.square_file(king_square)
  king_rank = chess.square_rank(king_square)
  zone = []
  for df in (-1, 0, 1):
      for dr in (-1, 0, 1):
          if df == 0 and dr == 0:
              continue  # skip the king's own square
          f, r = king_file + df, king_rank + dr
          if 0 <= f <= 7 and 0 <= r <= 7:
              zone.append(chess.square(f, r))
  return zone

def _king_vulnerability(board, king_color) -> float:
  king_square = board.king(king_color)
  danger = 0.0 
  for square in _king_zone(king_square): #Iterates through all the squares surrounding the king. 
        defenders = len(board.attackers(king_color, square))
        attackers = len(board.attackers(not king_color, square))
        margin = max(0, attackers - defenders + VULNERABILITY_MARGIN)
        if margin == 0: #At least 1 more defender than attacker. 
            continue
        piece = board.piece_at(square)
        if piece is None: #No piece on the square next to the king. 
          weight = KING_ZONE_WEIGHTS["empty_diagonal" if _is_diagonal(king_square=king_square, other_square=square) else "empty_orthogonal"]
          if len(board.partner.pockets[not king_color]) == 0: #If opponent has no pieces to place down, empty space not as big of a deal. 
            weight *= 0.5 
        elif piece.color != king_color: 
          weight = KING_ZONE_WEIGHTS["enemy_piece_adjacent"]
        elif _is_diagonal(king_square, other_square=square):
          weight = KING_ZONE_WEIGHTS["occupied_diagonal"]
        else:
          weight = KING_ZONE_WEIGHTS["occupied_orthogonal"]
        danger += weight * margin
  return danger



def score_pieces(board, player) -> float:
  """ 
   sums PIECE_VALUES for board.turn's pieces (board + pocket) minus
   the opponent's, using board.piece_type_at / board.pockets.
  """
  current_points = 0.0
  opponent_points = 0.0

  for square, piece in board.piece_map().items():
    if piece.color == player:
      current_points += PIECE_VALUES[chess.piece_name(piece.piece_type)]
    else:
      opponent_points += PIECE_VALUES[chess.piece_name(piece.piece_type)]
  
  for piece_type in chess.PIECE_TYPES:
    count = board.pockets[player-1].count(piece_type)
    if count > 0:
        current_points += PIECE_VALUES[chess.piece_name(piece_type)]
    opponent_count = board.pockets[player].count(piece_type)
    if opponent_count > 0:
      opponent_points += PIECE_VALUES[chess.piece_name(piece_type)]
    
  return current_points-opponent_points
        