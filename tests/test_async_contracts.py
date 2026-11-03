"""Tests for Async/Sync Invariant Contract Checking."""

from prism.core.contracts import check_contract_violations
from prism.parsers.js_ts_parser import parse_js_ts_file
from prism.parsers.python_parser import parse_python_file


def test_python_unawaited_coroutine_call():
    code_callee = """
async def fetch_user_data(user_id: int) -> dict:
    return {"id": user_id}
"""
    code_caller = """
def process():
    user = fetch_user_data(42)
"""
    p_callee = parse_python_file("service.py", code_callee)
    p_caller = parse_python_file("caller.py", code_caller)

    callee_sym = p_callee.symbols[0]
    caller_call = p_caller.call_sites[0]

    assert callee_sym.is_async is True
    assert caller_call.is_awaited is False

    violations = check_contract_violations(callee_sym, [caller_call])
    assert len(violations) == 1
    assert violations[0].severity == "CRITICAL"
    assert "Unawaited coroutine" in violations[0].reason


def test_python_properly_awaited_coroutine_call():
    code_callee = """
async def save_order(order_id: str):
    pass
"""
    code_caller = """
async def checkout():
    await save_order("ord_123")
"""
    p_callee = parse_python_file("db.py", code_callee)
    p_caller = parse_python_file("handler.py", code_caller)

    callee_sym = p_callee.symbols[0]
    caller_call = p_caller.call_sites[0]

    assert callee_sym.is_async is True
    assert caller_call.is_awaited is True

    violations = check_contract_violations(callee_sym, [caller_call])
    assert len(violations) == 0


def test_python_await_on_synchronous_function():
    code_callee = """
def calculate_tax(amount: float) -> float:
    return amount * 0.15
"""
    code_caller = """
async def checkout():
    tax = await calculate_tax(100.0)
"""
    p_callee = parse_python_file("calc.py", code_callee)
    p_caller = parse_python_file("cart.py", code_caller)

    callee_sym = p_callee.symbols[0]
    caller_call = p_caller.call_sites[0]

    assert callee_sym.is_async is False
    assert caller_call.is_awaited is True

    violations = check_contract_violations(callee_sym, [caller_call])
    assert len(violations) == 1
    assert violations[0].severity == "HIGH"
    assert "Awaiting synchronous function" in violations[0].reason


def test_js_ts_async_and_await_detection():
    code = """
async function queryDb(query) {
    return [];
}

const syncHelper = (x) => x * 2;

async function run() {
    const unawaited = queryDb("SELECT *");
    const awaited = await queryDb("SELECT 1");
    const badAwait = await syncHelper(5);
}
"""
    parsed = parse_js_ts_file("app.ts", code)
    assert len(parsed.symbols) >= 3

    sym_async = [s for s in parsed.symbols if s.name == "queryDb"][0]
    sym_sync = [s for s in parsed.symbols if s.name == "syncHelper"][0]

    assert sym_async.is_async is True
    assert sym_sync.is_async is False

    calls_to_async = [c for c in parsed.call_sites if c.callee_name == "queryDb"]
    assert len(calls_to_async) == 2
    assert calls_to_async[0].is_awaited is False
    assert calls_to_async[1].is_awaited is True

    # Check unawaited violation
    violations_async = check_contract_violations(sym_async, [calls_to_async[0]])
    assert len(violations_async) == 1
    assert "Unawaited coroutine" in violations_async[0].reason

    # Check properly awaited
    violations_awaited = check_contract_violations(sym_async, [calls_to_async[1]])
    assert len(violations_awaited) == 0
