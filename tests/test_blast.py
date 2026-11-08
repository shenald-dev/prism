from prism.core.blast import compute_blast_radius
from prism.core.graph import DependencyGraph
from prism.parsers.base import CallSite, Symbol


def test_isolated_symbol_has_low_risk():
    graph = DependencyGraph()
    sym = Symbol("helper", "function", "utils.py", 1, 5)

    report = compute_blast_radius(
        modified_symbols=[sym],
        graph=graph,
        total_files_scanned=1,
        duration_seconds=0.05,
    )
    assert report.impact_score <= 20
    assert report.risk_level == "LOW"
    assert len(report.all_violations) == 0

def test_broken_contract_escalates_to_critical():
    graph = DependencyGraph()
    sym = Symbol("auth", "function", "auth.py", 1, 5, params=["token", "secret"], min_required_params=2)

    # Broken call (only passes 1 arg)
    graph.add_call_site(CallSite("login", "auth", "api.py", 10, args_count=1))

    report = compute_blast_radius(
        modified_symbols=[sym],
        graph=graph,
        total_files_scanned=2,
        duration_seconds=0.05,
    )
    assert report.risk_level == "CRITICAL"
    assert len(report.all_violations) == 1

def test_blast_risk_moderate():
    graph = DependencyGraph()
    sym = Symbol("func", "function", "f.py", 1, 5)

    # 2 direct callers = 12 pts, 2 files (f.py, a.py) = 10 pts. Total = 22 pts -> MODERATE
    graph.add_call_site(CallSite("A", "func", "a.py", 1))
    graph.add_call_site(CallSite("B", "func", "a.py", 2))

    report = compute_blast_radius([sym], graph, 3, 0.0)
    assert report.risk_level == "MODERATE"
    assert report.impact_score == 22

def test_blast_risk_elevated():
    graph = DependencyGraph()
    sym = Symbol("func", "function", "f.py", 1, 5)

    # Need score >= 40 and < 70
    # 5 direct callers = 30 pts, 3 files (f.py, f1.py, f2.py) = 15 pts. Total = 45 pts -> ELEVATED
    for i in range(5):
        file_path = "f1.py" if i < 3 else "f2.py"
        graph.add_call_site(CallSite(f"caller_{i}", "func", file_path, 1))

    report = compute_blast_radius([sym], graph, 6, 0.0)
    assert report.risk_level == "ELEVATED"
    assert report.impact_score == 45


def test_transitive_callers_count_with_shared_direct_callers():
    s1 = Symbol(name="fn1", kind="function", file_path="core.py", line_number=1, end_line_number=3)
    s2 = Symbol(name="fn2", kind="function", file_path="core.py", line_number=5, end_line_number=7)
    graph = DependencyGraph()
    graph.register_symbol(s1)
    graph.register_symbol(s2)

    # direct_caller invokes both fn1 and fn2
    graph.add_call_site(CallSite(caller_name="direct_caller", callee_name="fn1", file_path="app.py", line_number=10))
    graph.add_call_site(CallSite(caller_name="direct_caller", callee_name="fn2", file_path="app.py", line_number=11))
    # transitive_caller invokes direct_caller
    graph.add_call_site(CallSite(caller_name="transitive_caller", callee_name="direct_caller", file_path="outer.py", line_number=20))

    report = compute_blast_radius([s1, s2], graph, total_files_scanned=3, duration_seconds=0.01)

    assert report.modified_symbols_count == 2
    assert report.direct_callers_count == 2  # Total direct caller edges
    assert report.transitive_callers_count == 1  # outer.py::transitive_caller should not be zeroed out
    assert "outer.py::transitive_caller" in report.all_affected_functions

