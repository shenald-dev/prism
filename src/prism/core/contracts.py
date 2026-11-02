"""
Contract and signature invariant violation detector.
Catches argument count mismatches, missing required parameters, positional-only violations,
duplicate bindings, and broken caller contracts across Python and TypeScript.
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

    # Derive positional and keyword metadata if not already computed
    positional_params = (
        symbol.positional_params
        if symbol.positional_params or not symbol.params
        else [p for p in symbol.params if p not in symbol.kwonly_params]
    )
    posonly_params = set(symbol.posonly_params)
    kwonly_params = set(symbol.kwonly_params)
    all_known_params = set(symbol.params) | kwonly_params | posonly_params

    max_positional = (
        symbol.max_positional_params
        if symbol.max_positional_params is not None
        else len(positional_params)
    )

    # Compute required parameter sets
    if symbol.required_params:
        required_all = set(symbol.required_params)
    elif symbol.min_required_params > 0 and symbol.params:
        required_all = set(symbol.params[: symbol.min_required_params])
    else:
        required_all = set()

    for call in incoming_calls:
        # Don't check calls from the exact definition line of the symbol itself
        if call.file_path == symbol.file_path and call.line_number == symbol.line_number:
            continue

        args_count = call.args_count
        kwargs_set = set(call.kwargs_names)

        # 1. Check for Positional-Only parameters passed via keyword
        posonly_passed_as_kw = kwargs_set & posonly_params
        if posonly_passed_as_kw:
            kw_list = ", ".join(f"'{k}'" for k in sorted(posonly_passed_as_kw))
            violations.append(
                ContractViolation(
                    callee_name=symbol.name,
                    callee_file=symbol.file_path,
                    caller_identifier=call.caller_identifier,
                    caller_file=call.file_path,
                    caller_line=call.line_number,
                    severity="CRITICAL",
                    reason=f"Positional-only parameter(s) {kw_list} passed as keyword argument(s) to '{symbol.name}'.",
                    snippet=call.snippet,
                    suggested_fix=f"Pass {kw_list} as positional argument(s) without keyword names.",
                )
            )

        # 2. Check for Duplicate parameter bindings (passed both positionally and as keyword)
        bound_positional = positional_params[: min(args_count, len(positional_params))]
        duplicates = set(bound_positional) & kwargs_set
        if duplicates:
            dup_list = ", ".join(f"'{d}'" for d in sorted(duplicates))
            violations.append(
                ContractViolation(
                    callee_name=symbol.name,
                    callee_file=symbol.file_path,
                    caller_identifier=call.caller_identifier,
                    caller_file=call.file_path,
                    caller_line=call.line_number,
                    severity="CRITICAL",
                    reason=f"Duplicate parameter binding: {dup_list} received both positional and keyword values in '{symbol.name}'.",
                    snippet=call.snippet,
                    suggested_fix=f"Remove duplicate keyword argument(s) {dup_list} from the callsite.",
                )
            )

        # 3. Check for Excess Positional Arguments
        if not symbol.has_varargs and args_count > max_positional:
            violations.append(
                ContractViolation(
                    callee_name=symbol.name,
                    callee_file=symbol.file_path,
                    caller_identifier=call.caller_identifier,
                    caller_file=call.file_path,
                    caller_line=call.line_number,
                    severity="CRITICAL",
                    reason=f"Excess positional argument(s). '{symbol.name}' accepts up to {max_positional} positional arg(s), but caller passed {args_count}.",
                    snippet=call.snippet,
                    suggested_fix=f"Remove extra positional argument(s) at callsite or accept *args in '{symbol.name}'.",
                )
            )

        # 4. Check for Unexpected Keyword Arguments
        if not symbol.has_kwargs and call.kwargs_names:
            unexpected_kws = [kw for kw in call.kwargs_names if kw not in all_known_params]
            for kw in unexpected_kws:
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

        # 5. Check for Missing Required Arguments
        # Determine which required parameters have been supplied
        supplied_params = set(bound_positional) | (kwargs_set & all_known_params)
        missing_params = required_all - supplied_params

        # Fallback check if caller args count is simply less than min_required_params
        if not missing_params and symbol.min_required_params > 0:
            total_supplied = min(args_count, max_positional) + len(kwargs_set & all_known_params)
            if total_supplied < symbol.min_required_params:
                missing_count = symbol.min_required_params - total_supplied
                missing_params = set(symbol.params[: symbol.min_required_params]) - supplied_params

        if missing_params:
            missing_count = len(missing_params)
            missing_names = ", ".join(f"'{m}'" for m in sorted(missing_params))
            provided_count = len(supplied_params & required_all)
            violations.append(
                ContractViolation(
                    callee_name=symbol.name,
                    callee_file=symbol.file_path,
                    caller_identifier=call.caller_identifier,
                    caller_file=call.file_path,
                    caller_line=call.line_number,
                    severity="CRITICAL",
                    reason=(
                        f"Missing {missing_count} required argument(s): {missing_names}. "
                        f"'{symbol.name}' requires at least {symbol.min_required_params} arg(s), "
                        f"but caller only provided {provided_count} matching required parameter(s)."
                    ),
                    snippet=call.snippet,
                    suggested_fix=f"Update callsite to pass all required parameters ({missing_names}).",
                )
            )

    return violations
