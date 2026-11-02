from prism.core.contracts import check_contract_violations
from prism.parsers.base import CallSite, Symbol


def test_detects_duplicate_unexpected_kwargs():
    sym = Symbol(
        name="my_func",
        kind="function",
        file_path="f.py",
        line_number=1,
        end_line_number=5,
        params=["a"],
        positional_params=["a"],
        min_required_params=1,
    )
    call = CallSite(
        caller_name="caller",
        callee_name="my_func",
        file_path="c.py",
        line_number=10,
        args_count=0,
        kwargs_names=["unexpected", "unexpected"]
    )
    violations = check_contract_violations(sym, [call])
    # Expect 1 missing 'a', and only 1 'unexpected' error (deduplicated)
    assert len(violations) == 2
    reasons = [v.reason for v in violations]
    unexpected = [r for r in reasons if "Unexpected keyword argument" in r]
    assert len(unexpected) == 1
    assert "unexpected" in unexpected[0]

def test_correct_total_supplied_count():
    sym = Symbol(
        name="my_func",
        kind="function",
        file_path="f.py",
        line_number=1,
        end_line_number=5,
        params=["a", "b"],
        positional_params=["a", "b"],
        min_required_params=2,
    )
    call = CallSite(
        caller_name="caller",
        callee_name="my_func",
        file_path="c.py",
        line_number=10,
        args_count=1,  # 'a' is passed positionally
        kwargs_names=["a"] # 'a' is ALSO passed via kwarg
    )
    violations = check_contract_violations(sym, [call])

    # We expect 2 violations: Duplicate parameter 'a', and Missing required 'b'
    assert len(violations) == 2
    reasons = [v.reason for v in violations]
    missing = [r for r in reasons if "Missing" in r]
    dup = [r for r in reasons if "Duplicate" in r]
    assert len(missing) == 1
    assert "Missing 1 required argument(s): 'b'" in missing[0]
    assert len(dup) == 1
    assert "Duplicate parameter binding" in dup[0]
