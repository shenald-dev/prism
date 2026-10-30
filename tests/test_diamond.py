from prism.core.graph import DependencyGraph
from prism.parsers.base import CallSite, Symbol


def test_graph_diamond():
    graph = DependencyGraph()
    sym_e = Symbol("E", "function", "f.py", 1, 5)

    # A calls B
    graph.add_call_site(CallSite("A", "B", "f.py", 2))

    # B calls C
    graph.add_call_site(CallSite("B", "C", "f.py", 3))

    # B calls D
    graph.add_call_site(CallSite("B", "D", "f.py", 4))

    # C calls E
    graph.add_call_site(CallSite("C", "E", "f.py", 5))

    # D calls E
    graph.add_call_site(CallSite("D", "E", "f.py", 6))

    tree, _, _ = graph.compute_blast_tree(sym_e)

    # C and D call E
    assert len(tree) == 2

    node_c = next(n for n in tree if n.caller_symbol == "f.py::C")
    node_d = next(n for n in tree if n.caller_symbol == "f.py::D")

    assert len(node_c.children) == 1
    assert node_c.children[0].caller_symbol == "f.py::B"
    assert len(node_c.children[0].children) == 1
    assert node_c.children[0].children[0].caller_symbol == "f.py::A"

    assert len(node_d.children) == 1
    assert node_d.children[0].caller_symbol == "f.py::B"
    # This should be 1 because A calls B, but since A calls B is visited, it might be 0!
    assert len(node_d.children[0].children) == 1
    assert node_d.children[0].children[0].caller_symbol == "f.py::A"
