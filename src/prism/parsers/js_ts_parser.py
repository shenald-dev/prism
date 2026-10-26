"""
Parser for JavaScript and TypeScript files extracting functions, signatures, and call sites.
"""

import re
from typing import List, Tuple
from prism.parsers.base import CallSite, ParsedFile, Symbol

# Function declarations
# function foo(a, b) or export async function bar(x)
FN_DECL_REGEX = re.compile(
    r'^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\)',
    re.MULTILINE,
)

# Arrow functions & expressions
# const foo = (a, b) => or export const foo = async (a, b) =>
ARROW_FN_REGEX = re.compile(
    r'^\s*(?:export\s+)?const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*(?::\s*[^=]+)?=>',
    re.MULTILINE,
)

# Class method definitions
# foo(a, b) { or async bar(a, b): Promise<void> {
METHOD_DECL_REGEX = re.compile(
    r'^\s*(?:public|private|protected|static|async)*\s*([A-Za-z0-9_$]+)\s*\(([^)]*)\)\s*(?::\s*[^{]+)?\{',
    re.MULTILINE,
)

# Function call invocation
# callee(...) or obj.callee(...)
CALL_INVOCATION_REGEX = re.compile(
    r'(?<!function\s)(?<!class\s)\b([A-Za-z0-9_$]+)\s*\(([^)]*)\)'
)


def _parse_params(param_str: str) -> Tuple[List[str], int]:
    """Parse parameter list and compute minimum required parameters."""
    params = []
    min_required = 0
    if not param_str.strip():
        return params, min_required

    # Split by comma (ignoring commas inside nested braces if simple)
    raw_parts = [p.strip() for p in param_str.split(",") if p.strip()]
    for part in raw_parts:
        # Strip TS type annotation: 'name: string = "default"' -> 'name = "default"'
        clean_part = part.split(":")[0].strip()
        # Extract param name
        has_default = "=" in part or "?" in part
        param_name = clean_part.split("=")[0].strip()
        if param_name.startswith("..."):
            param_name = param_name[3:]
            has_default = True  # rest parameter is optional
        params.append(param_name)
        if not has_default:
            min_required += 1

    return params, min_required


def parse_js_ts_file(file_path: str, code: str) -> ParsedFile:
    """Parse JS/TS source code and extract symbols and call sites."""
    lines = code.splitlines()
    symbols: List[Symbol] = []
    call_sites: List[CallSite] = []

    # 1. Extract Symbols
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*")):
            continue

        # Check function declaration
        m_fn = FN_DECL_REGEX.match(line)
        if m_fn:
            name, raw_params = m_fn.group(1), m_fn.group(2)
            params, min_req = _parse_params(raw_params)
            symbols.append(
                Symbol(
                    name=name,
                    kind="function",
                    file_path=file_path,
                    line_number=lineno,
                    end_line_number=lineno,
                    params=params,
                    min_required_params=min_req,
                    signature=f"function {name}({raw_params.strip()})",
                )
            )
            continue

        # Check arrow function
        m_arrow = ARROW_FN_REGEX.match(line)
        if m_arrow:
            name, raw_params = m_arrow.group(1), m_arrow.group(2)
            params, min_req = _parse_params(raw_params)
            symbols.append(
                Symbol(
                    name=name,
                    kind="function",
                    file_path=file_path,
                    line_number=lineno,
                    end_line_number=lineno,
                    params=params,
                    min_required_params=min_req,
                    signature=f"const {name} = ({raw_params.strip()}) =>",
                )
            )
            continue

        # Check method
        m_method = METHOD_DECL_REGEX.match(line)
        if m_method:
            name, raw_params = m_method.group(1), m_method.group(2)
            if name not in ("if", "for", "while", "switch", "catch"):
                params, min_req = _parse_params(raw_params)
                symbols.append(
                    Symbol(
                        name=name,
                        kind="method",
                        file_path=file_path,
                        line_number=lineno,
                        end_line_number=lineno,
                        params=params,
                        min_required_params=min_req,
                        signature=f"{name}({raw_params.strip()})",
                    )
                )

    # 2. Extract Callsites
    # Track current enclosing function by line numbers
    current_symbol = "<module>"
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*")):
            continue

        # Update enclosing symbol if line matches one
        matching_syms = [s for s in symbols if s.line_number == lineno]
        if matching_syms:
            current_symbol = matching_syms[0].name

        for m_call in CALL_INVOCATION_REGEX.finditer(line):
            callee = m_call.group(1)
            raw_args = m_call.group(2).strip()

            # Ignore language control keywords
            if callee in ("if", "for", "while", "switch", "catch", "return", "function", "import", "require"):
                continue

            args_count = 0
            if raw_args:
                args_count = len([a for a in raw_args.split(",") if a.strip()])

            call_sites.append(
                CallSite(
                    caller_name=current_symbol,
                    callee_name=callee,
                    file_path=file_path,
                    line_number=lineno,
                    args_count=args_count,
                    snippet=stripped,
                )
            )

    return ParsedFile(file_path=file_path, symbols=symbols, call_sites=call_sites)
