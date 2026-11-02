from prism.core.contracts import ContractViolation
from prism.core.remediation import generate_agent_remediation_prompt
from prism.parsers.base import Symbol


def test_generate_agent_remediation_prompt():
    sym = Symbol(
        name="authenticate",
        kind="function",
        file_path="auth.py",
        line_number=12,
        end_line_number=20,
        params=["user_id", "token", "org_id"],
        required_params=["user_id", "token", "org_id"],
        signature="def authenticate(user_id, token, org_id)",
    )
    v = ContractViolation(
        callee_name="authenticate",
        callee_file="auth.py",
        caller_identifier="api/sessions.py::login",
        caller_file="api/sessions.py",
        caller_line=30,
        severity="CRITICAL",
        reason="Missing 1 required argument: 'org_id'",
        snippet="authenticate(user.id, token)",
        suggested_fix="Update callsite to pass 'org_id'",
    )

    prompt = generate_agent_remediation_prompt(
        modified_symbols=[sym],
        violations=[v],
        risk_level="CRITICAL",
        impact_score=85,
    )

    assert "PRISM INVARIANT RADAR" in prompt
    assert "CRITICAL" in prompt
    assert "85/100" in prompt
    assert "def authenticate(user_id, token, org_id)" in prompt
    assert "api/sessions.py:30" in prompt
    assert "Missing 1 required argument" in prompt
