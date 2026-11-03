from prism.core.graph import CallerNode, DependencyGraph
from prism.parsers.base import CallSite, Symbol


def test_graph_coverage():
    graph = DependencyGraph()
    sym = Symbol("func", "function", "a.py", 1, 5)

    # Test register_symbol
    graph.register_symbol(sym)

    # Test add_call_site with various callee_modules
    call_matching = CallSite("caller1", "func", "b.py", 1, callee_module="a")
    call_mismatch = CallSite("caller2", "func", "b.py", 2, callee_module="other")
    call_nomodule = CallSite("caller3", "func", "b.py", 3, callee_module=None)
    call_qualified = CallSite("caller4", "func", "b.py", 4, callee_module="a::func")

    graph.add_call_site(call_matching)
    graph.add_call_site(call_mismatch)
    graph.add_call_site(call_nomodule)
    graph.add_call_site(call_qualified)

    # Test get_direct_callers scoped logic
    callers = graph.get_direct_callers(sym)
    assert len(callers) == 4

    # Test CallerNode.to_dict
    node = CallerNode("b.py::caller1", "b.py", 1, 1)
    d = node.to_dict()
    assert d["caller_symbol"] == "b.py::caller1"
    assert d["file_path"] == "b.py"
    assert d["line_number"] == 1
    assert d["depth"] == 1
    assert d["args_count"] == 0
    assert d["kwargs_names"] == []
    assert d["snippet"] == ""
    assert d["is_test"] is False
    assert d["children"] == []


def test_graph_coverage_extra():
    graph = DependencyGraph()
    sym = Symbol("func", "function", "a.py", 1, 5)

    # Test line 77 (qualified name with mismatching module but matching ::name)
    call_weird_module = CallSite("caller5", "func", "b.py", 5, callee_module="weird::func")
    graph.add_call_site(call_weird_module)

    callers = graph.get_direct_callers(sym)
    assert len(callers) == 1
    assert callers[0].caller_name == "caller5"
