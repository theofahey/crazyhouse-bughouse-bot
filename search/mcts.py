"""
Phase 0 baseline search: standard MCTS (perfect information -- single
crazyhouse board, no hidden partner state yet).

This becomes the foundation for ISMCTS in Phase 2: same selection/expansion/
simulation/backprop loop, but Phase 2 will sample a "determinization" of the
unknown partner board before each simulation instead of assuming full
knowledge.

TODO (after engine/board.py and engine/eval.py have working legal move
generation + evaluation): implement the four MCTS phases.
"""


class MCTSNode:
    def __init__(self, board, parent=None, move=None):
        self.board = board
        self.parent = parent
        self.move = move
        self.children = []
        self.visits = 0
        self.value = 0.0


def search(root_board, iterations: int = 1000):
    """Run MCTS from root_board, return the best move found."""
    raise NotImplementedError
