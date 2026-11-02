from prism.core.contracts import ContractViolation
from prism.core.sarif import export_sarif


def test_export_sarif_empty():
    doc = export_sarif([])
    assert doc["version"] == "2.1.0"
    assert len(doc["runs"]) == 1
    assert doc["runs"][0]["tool"]["driver"]["name"] == "PRISM"
    assert len(doc["runs"][0]["results"]) == 0


def test_export_sarif_with_violations():
    v1 = ContractViolation(
        callee_name="calculate_tax",
        callee_file="tax.py",
        caller_identifier="order_service.py::checkout",
        caller_file="order_service.py",
        caller_line=45,
        severity="CRITICAL",
        reason="Missing 1 required argument: 'jurisdiction'",
        snippet="calculate_tax(order.total)",
        suggested_fix="Pass 'jurisdiction' parameter",
    )
    v2 = ContractViolation(
        callee_name="calculate_tax",
        callee_file="tax.py",
        caller_identifier="worker.py::run",
        caller_file="worker.py",
        caller_line=10,
        severity="HIGH",
        reason="Unexpected keyword argument 'exempt'",
        snippet="calculate_tax(100, exempt=True)",
        suggested_fix="Remove 'exempt'",
    )

    doc = export_sarif([v1, v2])
    results = doc["runs"][0]["results"]
    assert len(results) == 2

    r1 = results[0]
    assert r1["ruleId"] == "prism/missing-required-argument"
    assert r1["level"] == "error"
    assert r1["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "order_service.py"
    assert r1["locations"][0]["physicalLocation"]["region"]["startLine"] == 45

    r2 = results[1]
    assert r2["ruleId"] == "prism/unexpected-keyword-argument"
    assert r2["level"] == "warning"
    assert r2["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "worker.py"
