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
