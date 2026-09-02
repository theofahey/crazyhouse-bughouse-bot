"""
Phase 0 baseline search: MCTS with a direct leaf-value estimate instead of
a full random rollout to game end (see project notes on why -- rollouts to
checkmate are expensive and unnecessary given we have evaluate()).

Node.value convention: value is accumulated from the perspective of
whoever was about to move AT THAT NODE. Flip the sign at every step during
backpropagation -- turns alternate, so a good outcome one level down is a
bad outcome at the level above it. Get this backwards and the search will
still run and still produce a number, it'll just be silently wrong.
"""

from math import sqrt
import math
from engine.eval import evaluate

MATERIAL_SCALE = 6  # tuned so a rook+pawn material edge lands ~0.5;

class MCTSNode:
    def __init__(self, board, parent=None, move=None):
        self.board = board
        self.parent = parent
        self.move = move
        self.children = []
        self.untried_moves = list(board.legal_moves)  
        self.visits = 0
        self.value = 0.0

    def is_terminal(self) -> bool:
        return self.board.is_over_board()[0]

    def is_fully_expanded(self) -> bool:
        return len(self.untried_moves) == 0

    def ucb1(self, exploration=math.sqrt(2)) -> float:

        exploit = -self.value /self.visits
        explore = exploration * sqrt(math.log(self.parent.visits) / self.visits)

        return exploit + explore 
        
def _leaf_value(board) -> float:
    over, res = board.is_over_board()
    if over: 
        if res == 1 or res == 2: 
            return -1.0
        else: 
            return 0.0
    else: 
        return math.tanh(evaluate(board) / MATERIAL_SCALE)

def _select(node: MCTSNode) -> MCTSNode:
    """Walk down via UCB1 until we hit a node that's either terminal or
    still has untried moves."""
    while not node.is_terminal() and node.is_fully_expanded():
        node = max(node.children, key=lambda c: c.ucb1())
    return node


def _expand(node: MCTSNode) -> MCTSNode:
    """Called on non-terminal nodes with untried moves. Pops a move,
    creates exactly one new child."""
    new_move = node.untried_moves.pop()
    new_board = node.board.copy()
    new_board.push(new_move)
    new_node = MCTSNode(new_board, parent=node, move=new_move)
    node.children.append(new_node)

    return new_node


def _backpropagate(node: MCTSNode, value: float) -> None:
    """Walk from node up to the root. Flip the sign at every step -- see
    project notes on why. """
    while node is not None:
        node.visits += 1
        node.value += value
        value = -value
        node = node.parent

def search(root_board, iterations: int = 300):
    """Run MCTS from root_board, return the move with the most visits
    (not highest raw value -- visit count reflects how much the search
    actually trusts a branch, which is the more robust choice at the end).
    """
    root = MCTSNode(root_board.copy())
    for i in range(iterations):
        leaf = _select(root)
        if not leaf.is_terminal():
            leaf = _expand(leaf)
        value = _leaf_value(leaf.board)
        _backpropagate(leaf, value)

    best_child = max(root.children, key=lambda c: c.visits)
    return best_child.move

