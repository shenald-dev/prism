from prism.core.graph import DependencyGraph
from prism.parsers.base import CallSite, Symbol


def test_graph_dag():
    graph = DependencyGraph()
    sym_w = Symbol("W", "function", "f.py", 1, 5)
    graph.add_symbol(sym_w)

    # X calls Y and Z
    graph.add_call_site(CallSite("X", "Y", "f.py", 2))
    graph.add_call_site(CallSite("X", "Z", "f.py", 3))

    # Y calls W
    graph.add_call_site(CallSite("Y", "W", "f.py", 4))

    # Z calls W
    graph.add_call_site(CallSite("Z", "W", "f.py", 5))

    tree, _, _ = graph.compute_blast_tree(sym_w)

    # W should have Y and Z as callers
    assert len(tree) == 2

    # Y should have X as caller
    # Z should have X as caller
    for node in tree:
        assert len(node.children) == 1
        assert node.children[0].caller_symbol == "f.py::X"
