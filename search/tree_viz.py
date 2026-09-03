"""
Renders an MCTS search tree (or subtree) as a self-contained HTML file
using native <details>/<summary> elements -- click-to-expand for free,
no JavaScript needed. Meant to be called right after search(root_board,
iterations, return_tree=True), while the tree still exists in memory.

Node.value is accumulated in THAT NODE'S OWN perspective (see project
notes on MCTS backpropagation) -- so a node's own average, from the
perspective of whoever is looking AT it from its parent, is -value/visits,
not value/visits. This file applies that correction uniformly at every
depth, the same way dump_children()/find_child_by_move() do. The ROOT is
the one exception -- its own value already accumulates in YOUR perspective
directly (the sign-flip in backpropagate starts at the leaf and applies
uniformly all the way up, root included), so it's shown unnegated.
"""

MAX_DEPTH_DEFAULT = 6
MIN_VISITS_DEFAULT = 1
TOP_N_DEFAULT = 10

TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>MCTS Tree</title>
<style>
  body {{ background:#14171c; color:#e7e4dd; font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;
          padding:24px 32px; }}
  h1 {{ font-size:18px; margin-bottom:4px; }}
  .subtitle {{ color:#8b93a1; font-size:13px; margin-bottom:20px; }}
  details {{ margin-left:18px; }}
  summary {{ cursor:pointer; padding:2px 4px; border-radius:3px; list-style-position:outside; }}
  summary:hover {{ background:rgba(255,255,255,0.06); }}
  .move {{ font-family:"SF Mono",Consolas,monospace; font-weight:600; }}
  .stats {{ color:#8b93a1; font-size:12px; margin-left:8px; }}
  .good {{ color:#7fbf7f; }}
  .bad {{ color:#d97f7f; }}
  .neutral {{ color:#c9c4b8; }}
  .pruned {{ color:#5a6070; font-size:12px; margin-left:22px; font-style:italic; }}
</style></head>
<body>
<h1>MCTS Tree</h1>
<div class="subtitle">Click any move to expand its replies. Branches under {min_visits} visits or past depth {max_depth} are collapsed away as noise.</div>
{body}
</body></html>
"""


def _node_label(node, is_root: bool) -> str:
    move_str = "root" if is_root else node.move.uci()
    if node.visits == 0:
        return f'<span class="move">{move_str}</span> <span class="stats">unvisited</span>'
    avg = node.value / node.visits if is_root else -node.value / node.visits
    cls = "good" if avg > 0.05 else ("bad" if avg < -0.05 else "neutral")
    return (f'<span class="move">{move_str}</span> '
            f'<span class="stats {cls}">visits={node.visits} avg={avg:+.3f}</span>')


def _render(node, depth, is_root, max_depth, min_visits, top_n) -> str:
    label = _node_label(node, is_root)

    eligible = sorted(
        (c for c in node.children if c.visits >= min_visits),
        key=lambda c: c.visits, reverse=True,
    )
    shown = eligible[:top_n]
    pruned_count = len(node.children) - len(shown)

    if depth >= max_depth or not node.children:
        return f'<div>{label}</div>'

    children_html = "".join(
        _render(c, depth + 1, False, max_depth, min_visits, top_n) for c in shown
    )
    pruned_note = (f'<div class="pruned">{pruned_count} more branch(es) below the visit '
                    f'threshold, not shown</div>') if pruned_count > 0 else ""

    open_attr = "open" if depth < 1 else ""
    return f'<details {open_attr}><summary>{label}</summary>{children_html}{pruned_note}</details>'


def export_tree_html(root, path="tree.html", max_depth=MAX_DEPTH_DEFAULT,
                      min_visits=MIN_VISITS_DEFAULT, top_n=TOP_N_DEFAULT) -> None:
    body = _render(root, 0, True, max_depth, min_visits, top_n)
    html = TEMPLATE.format(body=body, min_visits=min_visits, max_depth=max_depth)
    with open(path, "w") as f:
        f.write(html)