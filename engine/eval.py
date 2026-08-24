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
    "knight": 3.5,
    "bishop": 3,
    "rook": 4.5,
    "queen": 9,
    "king": 0
}


def evaluate(board) -> float:
    """Return material balance from the CURRENT PLAYER TO MOVE's
    perspective (not always White's) -- positive favors board.turn.
    Include pocket pieces, not just pieces on the board -- a piece in
    hand is still yours, it just hasn't been placed yet.
    """
    return(score_pieces(board))

def score_pieces(board) -> float:
  """ 
   sums PIECE_VALUES for board.turn's pieces (board + pocket) minus
   the opponent's, using board.piece_type_at / board.pockets.
  """
  current_points = 0.0
  opponent_points = 0.0

  current_player = board.turn #1 if white, 0 if black
  if not current_player:
    player = chess.BLACK
  else:
    player = chess.WHITE
  

  for square, piece in board.piece_map().items():
    if piece.color == player:
      current_points += PIECE_VALUES[chess.piece_name(piece.piece_type)]
    else:
      opponent_points += PIECE_VALUES[chess.piece_name(piece.piece_type)]
  
  for piece_type in chess.PIECE_TYPES:
    count = board.pockets[current_player-1].count(piece_type)
    if count > 0:
        current_points += PIECE_VALUES[chess.piece_name(piece_type)]
    opponent_count = board.pockets[current_player].count(piece_type)
    if opponent_count > 0:
      opponent_points += PIECE_VALUES[chess.piece_name(piece_type)]
    
  return current_points-opponent_points
        