"""
Phase 0 baseline search: MCTS with a direct leaf-value estimate instead of
a full random rollout to game end (see project notes on why -- rollouts to
checkmate are expensive and unnecessary given we have evaluate()).

Node.value convention: value is accumulated from the perspective of
whoever was about to move AT THAT NODE. Flip the sign at every step during
backpropagation -- turns alternate, so a good outcome one level down is a
bad outcome at the level above it. Get this backwards and the search will
still run and still produce a number, it'll just be silently wrong.

Selection (A.6): plain UCB1 was useless here -- leaf values are
tanh(evaluate/scale) ~= +/-0.05 near balance, so the exploration term
dwarfed exploitation ~10-50x and every child got visited round-robin
regardless of budget. Two fixes:
  * the exploitation term is min-max normalised across siblings, so the
    exploration constant stays meaningful no matter how evaluate() is scaled;
  * progressive widening (children capped at ~C_PW*sqrt(visits)) plus a
    cheap capture / king-attacking-drop move order, so the budget goes
    DEEP on a few plausible moves instead of one visit each across 100+.

EXPLORATION (A.7c): sqrt(2) is the classical UCB1 constant, derived for
rewards that are raw win-probabilities in [0,1]. It was never re-derived
after A.6 made `exploit` a per-selection, sibling-relative min-max
normalisation -- which is *always* rescaled to fill exactly [0,1], however
large the real value gap is. Consequence: even a maximally-confident
exploitation signal (normalised exploit = 1.0, the best possible) barely
edges out a 4-visit sibling's explore bonus, and past ~35 visits the
maxed-out child's OWN score starts *decreasing* relative to an unvisited
rival -- the search actively drifts away from a proven-best move instead of
confirming it. Root cause of MCTS missing forced continuations (hanging
material, missing short mates) regardless of iteration budget; see project
notes / the A.7 investigation. Swept against a depth-2 minimax oracle
(blunder-gap vs. the safest legal move) across ~14 mid-game positions, and
against pick-stability as the iteration budget grows 1200->2400->4800:
0.8 cut the average blunder gap ~5.5x (0.77 -> 0.14) and was the only
candidate with zero flipped picks across all budgets (values below ~0.6
start reintroducing instability -- premature lock-on to an early lucky
sample that more budget then overturns, the mirror-image failure).
"""

from math import sqrt
import math

import chess

from engine.eval import evaluate

MATERIAL_SCALE = 6  # tuned so a rook+pawn material edge lands ~0.5;
DEFAULT_ITERATIONS = 4000  # simulations per move; retuned later against the match harness
EXPLORATION = 0.8  # see "EXPLORATION (A.7c)" above -- was sqrt(2), miscalibrated for normalised exploit
C_PW = 2.0  # progressive-widening constant: children <= ceil(C_PW * sqrt(visits))


def _move_priority(board, move) -> int:
    """Cheap ordering key (higher = expand sooner). Captures first, then
    drops next to the enemy king, then everything else. No board mutation."""
    score = 0
    if board.is_capture(move):
        score += 2
    if move.drop is not None:
        enemy_king = board.king(not board.turn)
        if enemy_king is not None and chess.square_distance(move.to_square, enemy_king) <= 2:
            score += 1
    return score


class MCTSNode:
    def __init__(self, board, parent=None, move=None):
        self.board = board
        self.parent = parent
        self.move = move
        self.children = []
        # sorted so untried_moves.pop() (from the end) yields the
        # highest-priority move first; stable, so ties keep legal-move order.
        self.untried_moves = sorted(board.legal_moves, key=lambda m: _move_priority(board, m))
        self.visits = 0
        self.value = 0.0

    def is_terminal(self) -> bool:
        return self.board.is_over_board()[0]

    def q(self) -> float:
        """Mean value from the PARENT's perspective (good child = bad for
        the node above it, hence the sign flip)."""
        return -self.value / self.visits if self.visits else 0.0

    def widening_cap(self) -> int:
        return max(1, math.ceil(C_PW * sqrt(self.visits)))

    def can_expand(self) -> bool:
        return bool(self.untried_moves) and len(self.children) < self.widening_cap()


def _leaf_value(board) -> float:
    over, res = board.is_over_board()
    if over:
        if res == 0 or res == 1:
            return -1.0
        else:
            return 0.0
    else:
        return math.tanh(evaluate(board) / MATERIAL_SCALE)


def _best_child(node: MCTSNode) -> MCTSNode:
    """UCB1 with the exploitation term min-max normalised across siblings."""
    qs = [c.q() for c in node.children]
    lo, hi = min(qs), max(qs)
    span = (hi - lo) or 1.0
    log_n = math.log(node.visits)
    best, best_score = None, -math.inf
    for child, qv in zip(node.children, qs):
        score = (qv - lo) / span + EXPLORATION * sqrt(log_n / child.visits)
        if score > best_score:
            best, best_score = child, score
    return best


def _select(node: MCTSNode) -> MCTSNode:
    """Walk down until we hit a node that's terminal or still has room to
    widen (an untried move under the widening cap)."""
    while not node.is_terminal() and not node.can_expand():
        node = _best_child(node)
    return node


def _expand(node: MCTSNode) -> MCTSNode:
    """Called on non-terminal nodes with room to widen. Pops the
    highest-priority untried move, creates exactly one new child."""
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

def find_child_by_move(node, uci):
    for child in node.children:
        if child.move.uci() == uci:
            return child
    return None

def search(root_board, iterations: int = DEFAULT_ITERATIONS, *, return_tree: bool = False):
    """Run MCTS from root_board, return the move with the most visits
    (not highest raw value -- visit count reflects how much the search
    actually trusts a branch, which is the more robust choice at the end).
    With return_tree=True, return (move, root_node) so callers can inspect
    the tree (e.g. search.tree_viz.export_tree_html).
    """
    root = MCTSNode(root_board.copy())
    for i in range(iterations):
        leaf = _select(root)
        if not leaf.is_terminal():
            leaf = _expand(leaf)
        value = _leaf_value(leaf.board)
        _backpropagate(leaf, value)

    best_child = max(root.children, key=lambda c: c.visits)
    if return_tree:
        return best_child.move, root
    return best_child.move


def make_mcts_agent(iterations: int = DEFAULT_ITERATIONS):
    """Return a ``(board) -> Move`` agent that runs MCTS for ``iterations``
    simulations per move."""
    return lambda board: search(board, iterations)
