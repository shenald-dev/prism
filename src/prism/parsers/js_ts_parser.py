"""
Parser for JavaScript and TypeScript files extracting functions, methods, classes, signatures,
imports, and call sites. Supports ES6+, TypeScript type annotations, arrow functions,
and multi-line parameter lists.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from prism.parsers.base import CallSite, ParsedFile, Symbol

# Multi-line or single-line function declaration
# export [default] [async] function name(...)
FN_DECL_REGEX = re.compile(
    r'(?:export\s+)?(?:default\s+)?(?:async\s+)?function(?:\s+([A-Za-z0-9_$]+))?\s*\(([\s\S]*?)\)',
    re.MULTILINE,
)

# Arrow functions
# const/let/var name = [async] (...) =>
ARROW_FN_REGEX = re.compile(
    r'(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(([\s\S]*?)\)\s*(?::\s*[^=]+)?=>',
    re.MULTILINE,
)

# Class method definitions
METHOD_DECL_REGEX = re.compile(
    r'^\s*(?:public|private|protected|static|async)*\s*([A-Za-z0-9_$]+)\s*\(([\s\S]*?)\)\s*(?::\s*[^{]+)?\{',
    re.MULTILINE,
)

# ES Module imports
# import { a, b as c } from './module'
IMPORT_NAMED_REGEX = re.compile(
    r'import\s+\{([^}]+)\}\s+from\s+[\'"]([^\'"]+)[\'"]',
    re.MULTILINE,
)
# import defaultExport from './module'
IMPORT_DEFAULT_REGEX = re.compile(
    r'import\s+([A-Za-z0-9_$]+)\s+from\s+[\'"]([^\'"]+)[\'"]',
    re.MULTILINE,
)
# import * as namespace from './module'
IMPORT_STAR_REGEX = re.compile(
    r'import\s+\*\s+as\s+([A-Za-z0-9_$]+)\s+from\s+[\'"]([^\'"]+)[\'"]',
    re.MULTILINE,
)

CALL_INVOCATION_REGEX = re.compile(
    r'(?<!function\s)(?<!class\s)\b([A-Za-z0-9_$]+)\s*\(([\s\S]*?)\)'
)


def _split_top_level_commas(s: str) -> List[str]:
    """Split string by comma, ignoring commas nested inside (), [], or {}."""
    parts = []
    current = []
    depth_paren = 0
    depth_bracket = 0
    depth_brace = 0
    in_single_quote = False
    in_double_quote = False

    for ch in s:
        if ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote

        if not in_single_quote and not in_double_quote:
            if ch == "(":
                depth_paren += 1
            elif ch == ")":
                depth_paren = max(0, depth_paren - 1)
            elif ch == "[":
                depth_bracket += 1
            elif ch == "]":
                depth_bracket = max(0, depth_bracket - 1)
            elif ch == "{":
                depth_brace += 1
            elif ch == "}":
                depth_brace = max(0, depth_brace - 1)
            elif ch == "," and depth_paren == 0 and depth_bracket == 0 and depth_brace == 0:
                parts.append("".join(current).strip())
                current = []
                continue

        current.append(ch)

    if current:
        last = "".join(current).strip()
        if last:
            parts.append(last)

    return parts


def _parse_params(param_str: str) -> Tuple[List[str], int, bool]:
    """
    Parse parameter string and return:
    - params: List of parameter names
    - min_required: Count of required parameters
    - has_rest: bool (whether rest parameter ...args is present)
    """
    params = []
    min_required = 0
    has_rest = False
    clean_str = param_str.strip()
    if not clean_str:
        return params, min_required, has_rest

    raw_parts = _split_top_level_commas(clean_str)
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue

        # Check for rest parameter
        if part.startswith("..."):
            has_rest = True
            param_name = part[3:].split(":")[0].strip()
            params.append(param_name)
            continue

        # Check default value or optional marker
        has_default = "=" in part or "?" in part

        # Strip TypeScript type annotation: 'name: string = "default"' -> 'name'
        clean_part = part.split(":")[0].strip()
        param_name = clean_part.split("=")[0].strip().rstrip("?")

        params.append(param_name)
        if not has_default:
            min_required += 1

    return params, min_required, has_rest


def _extract_imports(code: str) -> Dict[str, str]:
    """Extract imported identifiers and their source modules."""
    imports: Dict[str, str] = {}

    for m in IMPORT_NAMED_REGEX.finditer(code):
        names_str, module_path = m.group(1), m.group(2)
        for item in _split_top_level_commas(names_str):
            item = item.strip()
            if " as " in item:
                orig, alias = item.split(" as ")
                imports[alias.strip()] = f"{module_path}::{orig.strip()}"
            else:
                imports[item] = f"{module_path}::{item}"

    for m in IMPORT_DEFAULT_REGEX.finditer(code):
        name, module_path = m.group(1), m.group(2)
        imports[name] = module_path

    for m in IMPORT_STAR_REGEX.finditer(code):
        alias, module_path = m.group(1), m.group(2)
        imports[alias] = module_path

    return imports


def parse_js_ts_file(file_path: str, code: str) -> ParsedFile:
    """Parse JS/TS source code and extract symbols, call sites, and imports."""
    lines = code.splitlines()
    symbols: List[Symbol] = []
    call_sites: List[CallSite] = []
    imports = _extract_imports(code)

    is_test_file = (
        "test" in Path(file_path).parts
        or "__tests__" in Path(file_path).parts
        or Path(file_path).name.endswith((".test.ts", ".test.js", ".spec.ts", ".spec.js"))
    )

    # 1. Extract Symbols
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*")):
            continue

        # Function declaration
        m_fn = FN_DECL_REGEX.match(stripped)
        if m_fn and m_fn.group(1):
            name, raw_params = m_fn.group(1), m_fn.group(2)
            params, min_req, has_rest = _parse_params(raw_params)
            sig_params = " ".join(raw_params.split())
            symbols.append(
                Symbol(
                    name=name,
                    kind="function",
                    file_path=file_path,
                    line_number=lineno,
                    end_line_number=lineno,
                    params=params,
                    positional_params=params,
                    required_params=params[:min_req],
                    min_required_params=min_req,
                    has_varargs=has_rest,
                    signature=f"function {name}({sig_params})",
                    is_test=is_test_file or name.startswith("test"),
                )
            )
            continue

        # Arrow function
        m_arrow = ARROW_FN_REGEX.match(stripped)
        if m_arrow:
            name, raw_params = m_arrow.group(1), m_arrow.group(2)
            params, min_req, has_rest = _parse_params(raw_params)
            sig_params = " ".join(raw_params.split())
            symbols.append(
                Symbol(
                    name=name,
                    kind="function",
                    file_path=file_path,
                    line_number=lineno,
                    end_line_number=lineno,
                    params=params,
                    positional_params=params,
                    required_params=params[:min_req],
                    min_required_params=min_req,
                    has_varargs=has_rest,
                    signature=f"const {name} = ({sig_params}) =>",
                    is_test=is_test_file or name.startswith("test"),
                )
            )
            continue

        # Method
        m_method = METHOD_DECL_REGEX.match(line)
        if m_method:
            name, raw_params = m_method.group(1), m_method.group(2)
            if name not in ("if", "for", "while", "switch", "catch"):
                params, min_req, has_rest = _parse_params(raw_params)
                sig_params = " ".join(raw_params.split())
                symbols.append(
                    Symbol(
                        name=name,
                        kind="method",
                        file_path=file_path,
                        line_number=lineno,
                        end_line_number=lineno,
                        params=params,
                        positional_params=params,
                        required_params=params[:min_req],
                        min_required_params=min_req,
                        has_varargs=has_rest,
                        signature=f"{name}({sig_params})",
                        is_test=is_test_file or name.startswith("test"),
                    )
                )

    # 2. Extract Callsites
    current_symbol = "<module>"
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*")):
            continue

        matching_syms = [s for s in symbols if s.line_number == lineno]
        if matching_syms:
            current_symbol = matching_syms[0].name

        for m_call in CALL_INVOCATION_REGEX.finditer(line):
            callee = m_call.group(1)
            raw_args = m_call.group(2).strip()

            if callee in (
                "if",
                "for",
                "while",
                "switch",
                "catch",
                "return",
                "function",
                "import",
                "require",
                "typeof",
            ):
                continue

            # Accurate argument count taking nested objects/arrays into account
            args_count = 0
            if raw_args:
                arg_tokens = _split_top_level_commas(raw_args)
                args_count = len(arg_tokens)

            callee_mod: Optional[str] = imports.get(callee)

            call_sites.append(
                CallSite(
                    caller_name=current_symbol,
                    callee_name=callee,
                    file_path=file_path,
                    line_number=lineno,
                    args_count=args_count,
                    snippet=stripped,
                    callee_module=callee_mod,
                )
            )

    return ParsedFile(
        file_path=file_path,
        symbols=symbols,
        call_sites=call_sites,
        imports=imports,
        is_test_file=is_test_file,
    )
