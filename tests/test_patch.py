"""Tests for Call-site Remediation Patch Generator."""

from prism.core.contracts import ContractViolation
from prism.core.patch import PatchGenerator


def test_remediate_snippet_unawaited():
    v1 = ContractViolation(
        callee_name="fetch_data",
        callee_file="api.py",
        caller_identifier="main.py::run",
        caller_file="main.py",
        caller_line=10,
        severity="CRITICAL",
        reason="Unawaited coroutine call: 'fetch_data' is an async function",
        snippet="result = fetch_data()",
        suggested_fix="Add await",
    )
    orig, repl = PatchGenerator.remediate_snippet(v1)
    assert orig == "result = fetch_data()"
    assert repl == "result = await fetch_data()"


def test_remediate_snippet_await_on_sync():
    v2 = ContractViolation(
        callee_name="calc",
        callee_file="math.py",
        caller_identifier="main.py::run",
        caller_file="main.py",
        caller_line=15,
        severity="HIGH",
        reason="Awaiting synchronous function: 'calc' is synchronous",
        snippet="res = await calc()",
        suggested_fix="Remove await",
    )
    orig, repl = PatchGenerator.remediate_snippet(v2)
    assert "await" not in repl


def test_generate_patch_and_apply(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def run():\n    data = fetch_users()\n    return data\n")

    v = ContractViolation(
        callee_name="fetch_users",
        callee_file="db.py",
        caller_identifier="app.py::run",
        caller_file="app.py",
        caller_line=2,
        severity="CRITICAL",
        reason="Unawaited coroutine call: 'fetch_users' is an async function",
        snippet="data = fetch_users()",
        suggested_fix="Add await",
    )

    patch_str = PatchGenerator.generate_patch([v], tmp_path)
    assert "--- a/app.py" in patch_str
    assert "-  data = fetch_users()" in patch_str
    assert "+  data = await fetch_users()" in patch_str

    count = PatchGenerator.apply_fixes([v], tmp_path)
    assert count == 1
    new_content = f.read_text()
    assert "data = await fetch_users()" in new_content
