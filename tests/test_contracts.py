from prism.core.contracts import check_contract_violations
from prism.parsers.base import CallSite, Symbol

def test_detects_missing_required_arguments():
    # func expects 2 required parameters
    sym = Symbol(
        name="create_user",
        kind="function",
        file_path="auth.py",
        line_number=10,
        end_line_number=20,
        params=["username", "email"],
        min_required_params=2,
    )
    
    # Caller only passed 1 argument
    bad_call = CallSite(
        caller_name="login",
        callee_name="create_user",
        file_path="api.py",
        line_number=45,
        args_count=1,
        kwargs_names=[],
        snippet="create_user('alice')",
    )
    
    violations = check_contract_violations(sym, [bad_call])
    assert len(violations) == 1
    assert violations[0].severity == "CRITICAL"
    assert "Missing 1 required argument" in violations[0].reason

def test_detects_excess_positional_arguments():
    # func takes only 1 parameter, no *args
    sym = Symbol(
        name="square",
        kind="function",
        file_path="math_utils.py",
        line_number=5,
        end_line_number=10,
        params=["x"],
        min_required_params=1,
        has_varargs=False,
    )
    
    # Caller passed 2 arguments
    bad_call = CallSite(
        caller_name="calc",
        callee_name="square",
        file_path="main.py",
        line_number=12,
        args_count=2,
        snippet="square(2, 4)",
    )
    
    violations = check_contract_violations(sym, [bad_call])
    assert len(violations) == 1
    assert violations[0].severity == "CRITICAL"
    assert "Excess positional argument" in violations[0].reason

def test_detects_unexpected_keyword_argument():
    sym = Symbol(
        name="fetch_data",
        kind="function",
        file_path="api.py",
        line_number=1,
        end_line_number=10,
        params=["url", "timeout"],
        has_kwargs=False,
    )
    
    # Caller passed bogus_kw
    bad_call = CallSite(
        caller_name="worker",
        callee_name="fetch_data",
        file_path="jobs.py",
        line_number=30,
        args_count=1,
        kwargs_names=["bogus_kw"],
        snippet="fetch_data(url, bogus_kw=True)",
    )
    
    violations = check_contract_violations(sym, [bad_call])
    assert len(violations) == 1
    assert violations[0].severity == "HIGH"
    assert "Unexpected keyword argument 'bogus_kw'" in violations[0].reason
