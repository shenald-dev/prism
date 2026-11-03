"""Tests for Visual Mermaid & DOT Diagram Exporters."""

from prism.core.blast import BlastRadiusReport, SymbolBlast
from prism.core.contracts import ContractViolation
from prism.core.graph import CallerNode
from prism.core.visual import export_dot, export_mermaid
from prism.parsers.base import Symbol


def _build_test_report():
    target_sym = Symbol(
        name="authenticate_user",
        kind="function",
        file_path="src/auth.py",
        line_number=10,
        end_line_number=20,
        signature="def authenticate_user(token)",
    )

    child_node = CallerNode(
        caller_symbol="src/api.py::login_endpoint",
        file_path="src/api.py",
        line_number=55,
        depth=2,
    )

    caller_node = CallerNode(
        caller_symbol="src/middleware.py::auth_middleware",
        file_path="src/middleware.py",
        line_number=30,
        depth=1,
        children=[child_node],
    )

    test_node = CallerNode(
        caller_symbol="tests/test_auth.py::test_login",
        file_path="tests/test_auth.py",
        line_number=12,
        depth=1,
        is_test=True,
    )

    violation = ContractViolation(
        callee_name="authenticate_user",
        callee_file="src/auth.py",
        caller_identifier="src/middleware.py::auth_middleware",
        caller_file="src/middleware.py",
        caller_line=30,
        severity="CRITICAL",
        reason="Missing required argument 'token'",
        snippet="authenticate_user()",
        suggested_fix="Pass token",
    )

    sb = SymbolBlast(
        symbol=target_sym,
        blast_tree=[caller_node, test_node],
        affected_functions={"src/auth.py::authenticate_user", "src/middleware.py::auth_middleware"},
        affected_files={"src/auth.py", "src/middleware.py", "tests/test_auth.py"},
        violations=[violation],
    )

    return BlastRadiusReport(
        symbol_blasts=[sb],
        total_files_scanned=3,
        duration_seconds=0.05,
        all_affected_functions={"src/auth.py::authenticate_user", "src/middleware.py::auth_middleware"},
        all_affected_files={"src/auth.py", "src/middleware.py", "tests/test_auth.py"},
        all_violations=[violation],
    )


def test_export_mermaid():
    report = _build_test_report()
    mermaid = export_mermaid(report)
    assert "```mermaid" in mermaid
    assert "graph TD" in mermaid
    assert "authenticate_user" in mermaid
    assert "auth_middleware" in mermaid
    assert "test_login" in mermaid
    assert "classDef target" in mermaid
    assert "classDef broken" in mermaid


def test_export_dot():
    report = _build_test_report()
    dot = export_dot(report)
    assert "digraph PrismBlastRadius" in dot
    assert "authenticate_user" in dot
    assert "auth_middleware" in dot
    assert "test_login" in dot


def test_report_methods():
    report = _build_test_report()
    assert "graph TD" in report.to_mermaid()
    assert "digraph PrismBlastRadius" in report.to_dot()
