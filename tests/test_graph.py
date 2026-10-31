from prism.core.graph import DependencyGraph
from prism.parsers.base import CallSite, Symbol


def test_graph_direct_and_transitive_callers():
    graph = DependencyGraph()

    # 3 symbols: A -> calls B -> calls C
    sym_c = Symbol("func_c", "function", "c.py", 1, 5)
    Symbol("func_b", "function", "b.py", 1, 5)
    Symbol("func_a", "function", "a.py", 1, 5)

    # b calls c
    graph.add_call_site(CallSite("func_b", "func_c", "b.py", 3, args_count=0))
    # a calls b
    graph.add_call_site(CallSite("func_a", "func_b", "a.py", 3, args_count=0))

    direct_to_c = graph.get_direct_callers("func_c")
    assert len(direct_to_c) == 1
    assert direct_to_c[0].caller_name == "func_b"

    # Blast tree for C
    tree, affected_funcs, affected_files = graph.compute_blast_tree(sym_c, max_depth=5)
    assert len(tree) == 1
    node_b = tree[0]
    assert node_b.depth == 1
    assert node_b.caller_symbol == "b.py::func_b"

    # Node B should have child A at depth 2
    assert len(node_b.children) == 1
    node_a = node_b.children[0]
    assert node_a.depth == 2
    assert node_a.caller_symbol == "a.py::func_a"

    assert "a.py" in affected_files
    assert "b.py" in affected_files
    assert "c.py" in affected_files

def test_graph_handles_cycles():
    graph = DependencyGraph()
    sym_x = Symbol("func_x", "function", "x.py", 1, 5)
    Symbol("func_y", "function", "y.py", 1, 5)

    # X calls Y, and Y calls X (circular)
    graph.add_call_site(CallSite("func_x", "func_y", "x.py", 3))
    graph.add_call_site(CallSite("func_y", "func_x", "y.py", 3))

    tree, affected_funcs, affected_files = graph.compute_blast_tree(sym_x, max_depth=5)
    # Must terminate without infinite recursion
    assert len(tree) == 1
    assert "x.py::func_x" in affected_funcs
    assert "y.py::func_y" in affected_funcs

def test_graph_max_depth():
    graph = DependencyGraph()
    sym_a = Symbol("func_a", "function", "a.py", 1, 5)

    # D -> calls C -> calls B -> calls A
    graph.add_call_site(CallSite("func_d", "func_c", "d.py", 3))
    graph.add_call_site(CallSite("func_c", "func_b", "c.py", 3))
    graph.add_call_site(CallSite("func_b", "func_a", "b.py", 3))

    tree, _, _ = graph.compute_blast_tree(sym_a, max_depth=1)

    # Should only get B, not C or D
    assert len(tree) == 1
    node_b = tree[0]
    assert node_b.caller_symbol == "b.py::func_b"
    assert len(node_b.children) == 0

    tree2, _, _ = graph.compute_blast_tree(sym_a, max_depth=2)
    assert len(tree2) == 1
    node_b2 = tree2[0]
    assert len(node_b2.children) == 1
    node_c2 = node_b2.children[0]
    assert node_c2.caller_symbol == "c.py::func_c"
    assert len(node_c2.children) == 0
