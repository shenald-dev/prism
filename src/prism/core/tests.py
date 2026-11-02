"""
Intelligent Test Impact Radar and Runner.
Traces modified symbols to affected test suites, detects coverage gaps,
and executes only impacted tests for instantaneous feedback loops.
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from prism.parsers.base import Symbol


@dataclass
class TestImpactSummary:
    __test__ = False
    impacted_test_files: List[str] = field(default_factory=list)
    impacted_test_cases: List[str] = field(default_factory=list)
    untested_symbols: List[str] = field(default_factory=list)
    recommended_command: Optional[str] = None
    execution_result: Optional[str] = None
    execution_success: Optional[bool] = None

    def to_dict(self):
        return {
            "impacted_test_files": self.impacted_test_files,
            "impacted_test_cases": self.impacted_test_cases,
            "untested_symbols": self.untested_symbols,
            "recommended_command": self.recommended_command,
            "execution_result": self.execution_result,
            "execution_success": self.execution_success,
        }


def analyze_test_impact(
    modified_symbols: List[Symbol],
    all_affected_functions: Set[str],
    all_affected_files: Set[str],
) -> TestImpactSummary:
    """Analyze which tests are impacted by the modified symbols and identify test coverage gaps."""
    impacted_files: Set[str] = set()
    impacted_cases: Set[str] = set()

    for func_id in all_affected_functions:
        file_part, func_name = func_id.split("::", 1) if "::" in func_id else (func_id, "")
        is_test = (
            "test" in file_part.lower()
            or func_name.startswith("test_")
            or func_name.startswith("Test")
        )
        if is_test:
            impacted_files.add(file_part)
            if func_name and func_name != "<module>":
                impacted_cases.add(f"{file_part}::{func_name}")

    # Detect untested modified symbols (symbols whose blast tree has 0 test callers)
    untested: List[str] = []
    for sym in modified_symbols:
        has_test = any(
            sym.identifier in func_id or sym.name in func_id
            for func_id in impacted_cases
        )
        if not has_test and not sym.is_test:
            untested.append(sym.identifier)

    # Build recommended command
    recommended_cmd: Optional[str] = None
    py_tests = [f for f in impacted_files if f.endswith(".py")]
    ts_tests = [f for f in impacted_files if f.endswith((".ts", ".js", ".tsx", ".jsx"))]

    if py_tests:
        recommended_cmd = f"pytest {' '.join(sorted(py_tests))}"
    elif ts_tests:
        recommended_cmd = f"npm test -- {' '.join(sorted(ts_tests))}"

    return TestImpactSummary(
        impacted_test_files=sorted(impacted_files),
        impacted_test_cases=sorted(impacted_cases),
        untested_symbols=untested,
        recommended_command=recommended_cmd,
    )


def run_impacted_tests(
    test_summary: TestImpactSummary, root: Path
) -> TestImpactSummary:
    """Execute the impacted tests via their recommended command."""
    if not test_summary.recommended_command:
        test_summary.execution_result = "No impacted tests to execute."
        test_summary.execution_success = True
        return test_summary

    cmd_parts = test_summary.recommended_command.split()
    try:
        res = subprocess.run(
            cmd_parts,
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        test_summary.execution_success = (res.returncode == 0)
        output = res.stdout if res.stdout else res.stderr
        # Truncate output to last 20 lines if large
        lines = output.splitlines()
        trimmed_output = "\n".join(lines[-20:]) if len(lines) > 20 else output
        test_summary.execution_result = trimmed_output.strip()
    except subprocess.TimeoutExpired:
        test_summary.execution_success = False
        test_summary.execution_result = "Test execution timed out after 60s."
    except Exception as e:
        test_summary.execution_success = False
        test_summary.execution_result = f"Failed to execute tests: {e}"

    return test_summary
