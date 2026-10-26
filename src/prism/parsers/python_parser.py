"""
Python AST parser for extracting functions, methods, classes, signatures, and call sites.
"""

import ast
from typing import List, Optional

from prism.parsers.base import CallSite, ParsedFile, Symbol


class PythonASTVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str, code_lines: List[str]):
        self.file_path = file_path
        self.code_lines = code_lines
        self.symbols: List[Symbol] = []
        self.call_sites: List[CallSite] = []
        self.scope_stack: List[str] = ["<module>"]

    @property
    def current_scope(self) -> str:
        return self.scope_stack[-1]

    def _get_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.code_lines):
            return self.code_lines[lineno - 1].strip()
        return ""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def _handle_function(self, node, is_async: bool):
        kind = "async_function" if is_async else "function"
        if len(self.scope_stack) > 1 and not self.scope_stack[-1].startswith("<"):
            kind = "method"

        params = []
        # Positional arguments
        for arg in node.args.args:
            params.append(arg.arg)

        # Calculate minimum required positional parameters
        defaults_count = len(node.args.defaults)
        num_pos = len(node.args.args)
        # Exclude 'self' or 'cls' if method
        first_arg_offset = 1 if (kind == "method" and params and params[0] in ("self", "cls")) else 0
        min_required = max(0, (num_pos - first_arg_offset) - defaults_count)

        # Keyword-only arguments
        for i, kwarg in enumerate(node.args.kwonlyargs):
            params.append(kwarg.arg)
            # If kw_default is None, it is required
            if i < len(node.args.kw_defaults) and node.args.kw_defaults[i] is None:
                min_required += 1

        has_varargs = node.args.vararg is not None
        has_kwargs = node.args.kwarg is not None

        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)

        # Build clean signature string
        sig_prefix = "async def" if is_async else "def"
        sig_params = ", ".join(params)
        if has_varargs:
            sig_params += f", *{node.args.vararg.arg}"
        if has_kwargs:
            sig_params += f", **{node.args.kwarg.arg}"
        signature = f"{sig_prefix} {node.name}({sig_params})"

        docstring = ast.get_docstring(node)

        symbol = Symbol(
            name=node.name,
            kind=kind,
            file_path=self.file_path,
            line_number=start_line,
            end_line_number=end_line,
            params=params,
            min_required_params=min_required,
            has_varargs=has_varargs,
            has_kwargs=has_kwargs,
            signature=signature,
            docstring=docstring,
        )
        self.symbols.append(symbol)

        # Enter function scope and continue traversal
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef):
        symbol = Symbol(
            name=node.name,
            kind="class",
            file_path=self.file_path,
            line_number=node.lineno,
            end_line_number=getattr(node, "end_lineno", node.lineno),
            signature=f"class {node.name}",
            docstring=ast.get_docstring(node),
        )
        self.symbols.append(symbol)

        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Call(self, node: ast.Call):
        callee_name: Optional[str] = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = node.func.attr

        if callee_name:
            args_count = len(node.args)
            kwargs_names = [kw.arg for kw in node.keywords if kw.arg is not None]
            snippet = self._get_snippet(node.lineno)

            call_site = CallSite(
                caller_name=self.current_scope,
                callee_name=callee_name,
                file_path=self.file_path,
                line_number=node.lineno,
                args_count=args_count,
                kwargs_names=kwargs_names,
                snippet=snippet,
            )
            self.call_sites.append(call_site)

        self.generic_visit(node)


def parse_python_file(file_path: str, code: str) -> ParsedFile:
    """Parse Python source code and return symbols and call sites."""
    lines = code.splitlines()
    try:
        tree = ast.parse(code, filename=file_path)
        visitor = PythonASTVisitor(file_path, lines)
        visitor.visit(tree)
        return ParsedFile(file_path=file_path, symbols=visitor.symbols, call_sites=visitor.call_sites)
    except Exception:
        # Fallback if code has invalid syntax (e.g. partial edits in progress)
        return ParsedFile(file_path=file_path)
