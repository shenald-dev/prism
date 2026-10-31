"""
Contract and signature invariant violation detector.
Catches argument count mismatches, missing required parameters, and broken caller contracts.
"""

from dataclasses import dataclass
from typing import List

from prism.parsers.base import CallSite, Symbol


@dataclass
class ContractViolation:
    callee_name: str
    callee_file: str
    caller_identifier: str
    caller_file: str
    caller_line: int
    severity: str  # "CRITICAL", "HIGH", "WARNING"
    reason: str
    snippet: str
    suggested_fix: str

    def to_dict(self):
        return {
            "callee_name": self.callee_name,
            "callee_file": self.callee_file,
            "caller_identifier": self.caller_identifier,
            "caller_file": self.caller_file,
            "caller_line": self.caller_line,
            "severity": self.severity,
            "reason": self.reason,
            "snippet": self.snippet,
            "suggested_fix": self.suggested_fix,
        }


def check_contract_violations(
    symbol: Symbol, incoming_calls: List[CallSite]
) -> List[ContractViolation]:
    """Check all callers of a symbol for contract and signature mismatches."""
    violations: List[ContractViolation] = []

    for call in incoming_calls:
        # Don't check calls from the same definition line
        if call.file_path == symbol.file_path and call.line_number == symbol.line_number:
            continue

        total_args_passed = call.args_count + len(call.kwargs_names)

        # 1. Check for Missing Required Arguments
        # Caller might have passed enough total arguments, but missed required ones
        if symbol.min_required_params > 0:
            required_params = symbol.params[:symbol.min_required_params]
            provided_req_count = call.args_count
            for kw in call.kwargs_names:
                if kw in required_params:
                    provided_req_count += 1
            if provided_req_count < symbol.min_required_params:
                missing_count = symbol.min_required_params - provided_req_count
                violations.append(
                    ContractViolation(
                        callee_name=symbol.name,
                        callee_file=symbol.file_path,
                        caller_identifier=call.caller_identifier,
                        caller_file=call.file_path,
                        caller_line=call.line_number,
                        severity="CRITICAL",
                        reason=f"Missing {missing_count} required argument(s). '{symbol.name}' requires at least {symbol.min_required_params} arg(s), but caller only provided {provided_req_count} matching required parameter(s).",
                        snippet=call.snippet,
                        suggested_fix=f"Update callsite to pass all required parameters ({', '.join(symbol.params[:symbol.min_required_params])}).",
                    )
                )

        # 2. Check for Excess Positional Arguments
        # Caller passed more positional arguments than allowed (unless function has *args)
        if not symbol.has_varargs:
            max_pos = len(symbol.params)
            if call.args_count > max_pos:
                violations.append(
                    ContractViolation(
                        callee_name=symbol.name,
                        callee_file=symbol.file_path,
                        caller_identifier=call.caller_identifier,
                        caller_file=call.file_path,
                        caller_line=call.line_number,
                        severity="CRITICAL",
                        reason=f"Excess positional argument(s). '{symbol.name}' accepts up to {max_pos} positional arg(s), but caller passed {call.args_count}.",
                        snippet=call.snippet,
                        suggested_fix=f"Remove extra positional argument(s) at callsite or accept *args in '{symbol.name}'.",
                    )
                )

        # 3. Check for Unexpected Keyword Arguments
        # Caller passed a keyword arg that doesn't exist in parameter list (unless **kwargs allowed)
        if not symbol.has_kwargs and call.kwargs_names:
            for kw in call.kwargs_names:
                if kw not in symbol.params:
                    violations.append(
                        ContractViolation(
                            callee_name=symbol.name,
                            callee_file=symbol.file_path,
                            caller_identifier=call.caller_identifier,
                            caller_file=call.file_path,
                            caller_line=call.line_number,
                            severity="HIGH",
                            reason=f"Unexpected keyword argument '{kw}' passed to '{symbol.name}'.",
                            snippet=call.snippet,
                            suggested_fix=f"Remove '{kw}' or update definition of '{symbol.name}' to accept '{kw}' or **kwargs.",
                        )
                    )

    return violations
