from prism.core.contracts import check_contract_violations
from prism.parsers.base import CallSite, Symbol
from prism.parsers.python_parser import parse_python_file


def test_positional_only_passed_as_keyword():
    sym = Symbol(
        name="divide",
        kind="function",
        file_path="math_ops.py",
        line_number=1,
        end_line_number=5,
        params=["a", "b"],
        posonly_params=["a", "b"],
        positional_params=["a", "b"],
        required_params=["a", "b"],
        min_required_params=2,
    )
    # Caller calls divide(a=10, b=2)
    bad_call = CallSite(
        caller_name="main",
        callee_name="divide",
        file_path="main.py",
        line_number=10,
        args_count=0,
        kwargs_names=["a", "b"],
        snippet="divide(a=10, b=2)",
    )
    violations = check_contract_violations(sym, [bad_call])
    assert any("Positional-only parameter(s)" in v.reason for v in violations)


def test_duplicate_parameter_binding():
    sym = Symbol(
        name="set_profile",
        kind="function",
        file_path="user.py",
        line_number=1,
        end_line_number=5,
        params=["name", "age"],
        positional_params=["name", "age"],
        required_params=["name"],
        min_required_params=1,
    )
    # Caller calls set_profile("Alice", name="Bob") -> duplicate 'name'
    bad_call = CallSite(
        caller_name="main",
        callee_name="set_profile",
        file_path="main.py",
        line_number=12,
        args_count=1,
        kwargs_names=["name"],
        snippet="set_profile('Alice', name='Bob')",
    )
    violations = check_contract_violations(sym, [bad_call])
    assert any("Duplicate parameter binding" in v.reason for v in violations)


def test_keyword_only_required_missing():
    code = """
def send_email(recipient: str, *, subject: str, body: str = ""):
    pass

def handler():
    send_email("alice@example.com")
"""
    parsed = parse_python_file("mailer.py", code)
    fn_sym = next(s for s in parsed.symbols if s.name == "send_email")
    assert "recipient" in fn_sym.positional_params
    assert "subject" in fn_sym.kwonly_params
    assert "subject" in fn_sym.required_params
    assert fn_sym.min_required_params == 2  # recipient + subject

    call = parsed.call_sites[0]
    violations = check_contract_violations(fn_sym, [call])
    assert len(violations) == 1
    assert "Missing 1 required argument" in violations[0].reason
    assert "'subject'" in violations[0].reason


def test_positional_only_ast_parsing():
    code = """
def clamp(val: float, min_val: float, max_val: float, /) -> float:
    return max(min_val, min(val, max_val))
"""
    parsed = parse_python_file("utils.py", code)
    sym = parsed.symbols[0]
    assert sym.posonly_params == ["val", "min_val", "max_val"]
    assert sym.max_positional_params == 3
    assert sym.min_required_params == 3
