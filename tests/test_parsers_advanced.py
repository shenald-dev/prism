from prism.parsers.js_ts_parser import _parse_params, _split_top_level_commas, parse_js_ts_file
from prism.parsers.python_parser import parse_python_file


def test_split_top_level_commas():
    # Simple
    assert _split_top_level_commas("a, b, c") == ["a", "b", "c"]
    # With nested braces
    assert _split_top_level_commas("x, { id: 1, org: 2 }, y") == ["x", "{ id: 1, org: 2 }", "y"]
    # With nested brackets and parens
    assert _split_top_level_commas("[1, 2], fn(3, 4)") == ["[1, 2]", "fn(3, 4)"]
    # With quoted commas
    assert _split_top_level_commas('"hello, world", 42') == ['"hello, world"', "42"]


def test_parse_js_ts_params():
    params, min_req, has_rest = _parse_params("id: string, name?: string, ...tags: string[]")
    assert params == ["id", "name", "tags"]
    assert min_req == 1  # name is optional, tags is rest
    assert has_rest is True


def test_parse_js_ts_advanced_imports():
    code = """
import { calculateTax, formatCurrency as fmt } from './tax';
import defaultLogger from './logger';
import * as utils from './utils';

export function runInvoice(amount: number): void {
    const tax = calculateTax(amount);
    fmt(tax);
    defaultLogger(tax);
}
"""
    parsed = parse_js_ts_file("invoice.ts", code)
    assert parsed.imports["calculateTax"] == "./tax::calculateTax"
    assert parsed.imports["fmt"] == "./tax::formatCurrency"
    assert parsed.imports["defaultLogger"] == "./logger"
    assert parsed.imports["utils"] == "./utils"

    callee_names = [c.callee_name for c in parsed.call_sites]
    assert "calculateTax" in callee_names
    assert "fmt" in callee_names
    assert "defaultLogger" in callee_names


def test_python_parser_decorators_and_methods():
    code = """
class MathService:
    @staticmethod
    def add(a: int, b: int) -> int:
        return a + b

    @classmethod
    def create(cls, config: dict):
        return cls()

    def multiply(self, factor: int):
        return factor * 2
"""
    parsed = parse_python_file("service.py", code)
    syms = {s.name: s for s in parsed.symbols}

    add_sym = syms["add"]
    assert add_sym.min_required_params == 2  # staticmethod: does not drop first arg
    assert add_sym.positional_params == ["a", "b"]

    create_sym = syms["create"]
    assert create_sym.min_required_params == 1  # classmethod: drops cls
    assert create_sym.positional_params == ["config"]

    mult_sym = syms["multiply"]
    assert mult_sym.min_required_params == 1  # instance method: drops self
    assert mult_sym.positional_params == ["factor"]


def test_python_parser_imports_and_attributes():
    code = """
from services.billing import process_charge, TaxCalculator as Calc
import os.path as osp
from .models import Order

def handle_order(order_id: str):
    Calc.run(order_id)
    process_charge(order_id, 100)
"""
    parsed = parse_python_file("orders.py", code)
    assert parsed.imports["process_charge"] == "services.billing::process_charge"
    assert parsed.imports["Calc"] == "services.billing::TaxCalculator"
    assert parsed.imports["osp"] == "os.path"
    assert parsed.imports["Order"] == ".models::Order"

    calls = {c.callee_name: c for c in parsed.call_sites}
    assert "process_charge" in calls
    assert calls["process_charge"].callee_module == "services.billing::process_charge"
    assert calls["process_charge"].args_count == 2


def test_python_class_and_dataclass_contract_extraction():
    code = """
from dataclasses import dataclass

@dataclass
class UserRecord:
    user_id: str
    email: str
    role: str = "member"

class DatabaseClient:
    def __init__(self, host: str, port: int = 5432):
        self.host = host
        self.port = port
"""
    parsed = parse_python_file("models.py", code)
    syms = {s.name: s for s in parsed.symbols}

    user_cls = syms["UserRecord"]
    assert user_cls.kind == "class"
    assert user_cls.params == ["user_id", "email", "role"]
    assert user_cls.required_params == ["user_id", "email"]
    assert user_cls.min_required_params == 2

    db_cls = syms["DatabaseClient"]
    assert db_cls.kind == "class"
    assert db_cls.params == ["host", "port"]
    assert db_cls.required_params == ["host"]
    assert db_cls.min_required_params == 1

