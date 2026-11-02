"""
Python AST parser for extracting functions, methods, classes, signatures, imports, and call sites.
Supports Python 3.8-3.12 syntax including positional-only parameters, keyword-only parameters,
and static/class method decorators.
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional

from prism.parsers.base import CallSite, ParsedFile, Symbol


class PythonASTVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str, code_lines: List[str]):
        self.file_path = file_path
        self.code_lines = code_lines
        self.symbols: List[Symbol] = []
        self.call_sites: List[CallSite] = []
        self.imports: Dict[str, str] = {}  # local symbol/alias -> source module or file
        self.scope_stack: List[str] = ["<module>"]
        self.current_class: Optional[str] = None
        self.is_test_file = (
            "test" in Path(file_path).parts
            or Path(file_path).name.startswith("test_")
            or Path(file_path).name.endswith("_test.py")
        )

    @property
    def current_scope(self) -> str:
        return self.scope_stack[-1]

    def _get_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.code_lines):
            return self.code_lines[lineno - 1].strip()
        return ""

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        # Handle relative imports
        if node.level > 0:
            rel_prefix = "." * node.level
            mod = f"{rel_prefix}{mod}" if mod else rel_prefix

        for alias in node.names:
            local_name = alias.asname or alias.name
            target = f"{mod}::{alias.name}" if mod else alias.name
            self.imports[local_name] = target
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def _handle_function(self, node, is_async: bool):
        kind = "async_function" if is_async else "function"
        is_method = self.current_class is not None and len(self.scope_stack) > 1

        # Check decorators for staticmethod or classmethod
        decorator_names = set()
        for d in node.decorator_list:
            if isinstance(d, ast.Name):
                decorator_names.add(d.id)
            elif isinstance(d, ast.Attribute):
                decorator_names.add(d.attr)

        is_static = "staticmethod" in decorator_names
        is_classmethod = "classmethod" in decorator_names
        if is_method:
            kind = "method"

        # 1. Positional-only params (Python 3.8+)
        posonly_names = [a.arg for a in getattr(node.args, "posonlyargs", [])]

        # 2. Regular positional / keyword params
        standard_pos_names = [a.arg for a in node.args.args]

        all_pos_names = posonly_names + standard_pos_names

        # Positional defaults map from right of all_pos_names
        defaults = node.args.defaults
        num_pos_defaults = len(defaults)

        # Exclude self/cls for instance and class methods (not for staticmethod)
        first_arg_offset = 0
        if is_method and not is_static and all_pos_names:
            if all_pos_names[0] in ("self", "cls") or is_classmethod:
                first_arg_offset = 1

        # Determine required positional params (excluding self/cls)
        pos_without_self = all_pos_names[first_arg_offset:]
        num_required_pos = max(0, len(pos_without_self) - num_pos_defaults)
        required_pos_params = pos_without_self[:num_required_pos]

        # 3. Keyword-only params
        kwonly_names = [a.arg for a in node.args.kwonlyargs]
        required_kwonly_params = []
        for i, kwarg in enumerate(node.args.kwonlyargs):
            # If corresponding kw_default is None, it is required
            if i < len(node.args.kw_defaults) and node.args.kw_defaults[i] is None:
                required_kwonly_params.append(kwarg.arg)

        # All params for signature and dictionary
        all_params = pos_without_self + kwonly_names
        all_required = required_pos_params + required_kwonly_params
        min_required = len(all_required)

        has_varargs = node.args.vararg is not None
        has_kwargs = node.args.kwarg is not None
        max_positional = None if has_varargs else len(pos_without_self)

        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)

        # Build clean signature
        sig_prefix = "async def" if is_async else "def"
        sig_parts = []
        if posonly_names:
            sig_parts.append(", ".join(posonly_names))
            sig_parts.append("/")
        if standard_pos_names:
            sig_parts.append(", ".join(standard_pos_names))
        if kwonly_names:
            if not has_varargs and (posonly_names or standard_pos_names):
                sig_parts.append("*")
            elif not has_varargs:
                sig_parts.append("*")
            sig_parts.append(", ".join(kwonly_names))
        if has_varargs:
            sig_parts.append(f"*{node.args.vararg.arg}")
        if has_kwargs:
            sig_parts.append(f"**{node.args.kwarg.arg}")

        signature = f"{sig_prefix} {node.name}({', '.join(sig_parts)})"
        docstring = ast.get_docstring(node)
        is_test = self.is_test_file or node.name.startswith("test_")

        symbol = Symbol(
            name=node.name,
            kind=kind,
            file_path=self.file_path,
            line_number=start_line,
            end_line_number=end_line,
            params=all_params,
            posonly_params=[p for p in posonly_names if p not in ("self", "cls")],
            positional_params=pos_without_self,
            kwonly_params=kwonly_names,
            required_params=all_required,
            min_required_params=min_required,
            max_positional_params=max_positional,
            has_varargs=has_varargs,
            has_kwargs=has_kwargs,
            signature=signature,
            docstring=docstring,
            parent_class=self.current_class,
            is_test=is_test,
        )
        self.symbols.append(symbol)

        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef):
        is_test = self.is_test_file or node.name.startswith("Test")
        decorator_names = set()
        for d in node.decorator_list:
            if isinstance(d, ast.Name):
                decorator_names.add(d.id)
            elif isinstance(d, ast.Attribute):
                decorator_names.add(d.attr)
            elif isinstance(d, ast.Call):
                if isinstance(d.func, ast.Name):
                    decorator_names.add(d.func.id)
                elif isinstance(d.func, ast.Attribute):
                    decorator_names.add(d.func.attr)

        is_dataclass = "dataclass" in decorator_names

        # Look for __init__ or dataclass fields
        init_node = None
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
                init_node = item
                break

        class_params = []
        class_pos_params = []
        class_req_params = []
        has_varargs = False
        has_kwargs = False
        min_required = 0

        if init_node:
            posonly_names = [a.arg for a in getattr(init_node.args, "posonlyargs", [])]
            standard_pos_names = [a.arg for a in init_node.args.args]
            all_pos_names = posonly_names + standard_pos_names
            defaults = init_node.args.defaults
            first_offset = 1 if all_pos_names and all_pos_names[0] in ("self", "cls") else 0
            pos_without_self = all_pos_names[first_offset:]
            num_pos_defaults = len(defaults)
            num_req_pos = max(0, len(pos_without_self) - num_pos_defaults)
            req_pos = pos_without_self[:num_req_pos]

            kwonly_names = [a.arg for a in init_node.args.kwonlyargs]
            req_kwonly = []
            for i, kwarg in enumerate(init_node.args.kwonlyargs):
                if i < len(init_node.args.kw_defaults) and init_node.args.kw_defaults[i] is None:
                    req_kwonly.append(kwarg.arg)

            class_params = pos_without_self + kwonly_names
            class_pos_params = pos_without_self
            class_req_params = req_pos + req_kwonly
            min_required = len(class_req_params)
            has_varargs = init_node.args.vararg is not None
            has_kwargs = init_node.args.kwarg is not None
        elif is_dataclass:
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field_name = item.target.id
                    class_params.append(field_name)
                    class_pos_params.append(field_name)
                    if item.value is None:
                        class_req_params.append(field_name)
            min_required = len(class_req_params)
        else:
            has_varargs = True
            has_kwargs = True

        max_positional = None if has_varargs else len(class_pos_params)

        symbol = Symbol(
            name=node.name,
            kind="class",
            file_path=self.file_path,
            line_number=node.lineno,
            end_line_number=getattr(node, "end_lineno", node.lineno),
            params=class_params,
            positional_params=class_pos_params,
            required_params=class_req_params,
            min_required_params=min_required,
            max_positional_params=max_positional,
            has_varargs=has_varargs,
            has_kwargs=has_kwargs,
            signature=f"class {node.name}({', '.join(class_params)})",
            docstring=ast.get_docstring(node),
            is_test=is_test,
        )
        self.symbols.append(symbol)

        prev_class = self.current_class
        self.current_class = node.name
        self.scope_stack.append(node.name)

        self.generic_visit(node)

        self.scope_stack.pop()
        self.current_class = prev_class

    def visit_Call(self, node: ast.Call):
        callee_name: Optional[str] = None
        callee_module: Optional[str] = None
        is_method_call = False

        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
            if callee_name in self.imports:
                callee_module = self.imports[callee_name]
        elif isinstance(node.func, ast.Attribute):
            callee_name = node.func.attr
            is_method_call = True
            # If object is module name: e.g. os.path or tax.calculate_tax
            if isinstance(node.func.value, ast.Name):
                obj_name = node.func.value.id
                if obj_name in self.imports:
                    callee_module = f"{self.imports[obj_name]}::{callee_name}"
                else:
                    callee_module = f"{obj_name}::{callee_name}"

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
                callee_module=callee_module,
                is_method_call=is_method_call,
            )
            self.call_sites.append(call_site)

        self.generic_visit(node)


def parse_python_file(file_path: str, code: str) -> ParsedFile:
    """Parse Python source code and return symbols, call sites, and imports."""
    lines = code.splitlines()
    try:
        tree = ast.parse(code, filename=file_path)
        visitor = PythonASTVisitor(file_path, lines)
        visitor.visit(tree)
        return ParsedFile(
            file_path=file_path,
            symbols=visitor.symbols,
            call_sites=visitor.call_sites,
            imports=visitor.imports,
            is_test_file=visitor.is_test_file,
        )
    except Exception:
        # Graceful fallback for partially edited/incomplete files
        return ParsedFile(file_path=file_path)
