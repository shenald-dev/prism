from prism.parsers.js_ts_parser import parse_js_ts_file
from prism.parsers.python_parser import parse_python_file


def test_python_function_and_call_extraction():
    code = """
def calculate_tax(amount: float, rate: float = 0.2) -> float:
    return amount * rate

async def process_order(order_id: str, amount: float):
    tax = calculate_tax(amount)
    return tax
"""
    parsed = parse_python_file("service.py", code)
    assert len(parsed.symbols) == 2

    fn_tax = next(s for s in parsed.symbols if s.name == "calculate_tax")
    assert fn_tax.kind == "function"
    assert fn_tax.params == ["amount", "rate"]
    assert fn_tax.min_required_params == 1  # rate has default

    fn_order = next(s for s in parsed.symbols if s.name == "process_order")
    assert fn_order.kind == "async_function"
    assert fn_order.min_required_params == 2

    assert len(parsed.call_sites) == 1
    call = parsed.call_sites[0]
    assert call.callee_name == "calculate_tax"
    assert call.caller_name == "process_order"
    assert call.args_count == 1

def test_python_methods_and_classes():
    code = """
class PaymentGateway:
    def charge(self, user_id: str, amount: int, *args, **kwargs):
        pass
"""
    parsed = parse_python_file("gateway.py", code)
    assert any(s.kind == "class" and s.name == "PaymentGateway" for s in parsed.symbols)
    method = next(s for s in parsed.symbols if s.name == "charge")
    assert method.kind == "method"
    assert method.min_required_params == 2  # excludes self
    assert method.has_varargs is True
    assert method.has_kwargs is True

def test_js_ts_function_and_calls():
    code = """
export async function authenticate(token: string, timeout = 5000): Promise<boolean> {
    const valid = verifyToken(token);
    return valid;
}

const handleLogin = (req, res) => {
    authenticate(req.token);
};
"""
    parsed = parse_js_ts_file("auth.ts", code)
    assert len(parsed.symbols) == 2

    auth_sym = next(s for s in parsed.symbols if s.name == "authenticate")
    assert auth_sym.min_required_params == 1
    assert "token" in auth_sym.params

    login_sym = next(s for s in parsed.symbols if s.name == "handleLogin")
    assert login_sym.min_required_params == 2

    callee_names = [c.callee_name for c in parsed.call_sites]
    assert "verifyToken" in callee_names
    assert "authenticate" in callee_names
