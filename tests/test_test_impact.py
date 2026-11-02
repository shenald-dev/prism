from pathlib import Path

from prism.core.tests import TestImpactSummary, analyze_test_impact, run_impacted_tests
from prism.parsers.base import Symbol


def test_analyze_test_impact_identifies_tests():
    sym1 = Symbol("calculate_tax", "function", "tax.py", 1, 10)
    sym2 = Symbol("format_currency", "function", "currency.py", 1, 10)

    all_affected_functions = {
        "tax.py::calculate_tax",
        "orders.py::checkout",
        "tests/test_tax.py::test_calculate_tax",
    }
    all_affected_files = {"tax.py", "orders.py", "tests/test_tax.py"}

    summary = analyze_test_impact(
        modified_symbols=[sym1, sym2],
        all_affected_functions=all_affected_functions,
        all_affected_files=all_affected_files,
    )

    assert "tests/test_tax.py" in summary.impacted_test_files
    assert "tests/test_tax.py::test_calculate_tax" in summary.impacted_test_cases
    assert summary.recommended_command == "pytest tests/test_tax.py"
    # sym2 has no test callers
    assert "currency.py::format_currency" in summary.untested_symbols


def test_run_impacted_tests_empty(tmp_path: Path):
    summary = TestImpactSummary()
    updated = run_impacted_tests(summary, tmp_path)
    assert updated.execution_success is True
    assert "No impacted tests" in updated.execution_result
