"""
Base representations for AST symbols, function signatures, call sites, and import mappings.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Symbol:
    name: str
    kind: str  # "function", "async_function", "method", "class", "test"
    file_path: str
    line_number: int
    end_line_number: int
    params: List[str] = field(default_factory=list)
    posonly_params: List[str] = field(default_factory=list)
    positional_params: List[str] = field(default_factory=list)
    kwonly_params: List[str] = field(default_factory=list)
    required_params: List[str] = field(default_factory=list)
    min_required_params: int = 0
    max_positional_params: Optional[int] = None
    has_varargs: bool = False
    has_kwargs: bool = False
    signature: str = ""
    docstring: Optional[str] = None
    parent_class: Optional[str] = None
    is_test: bool = False

    @property
    def identifier(self) -> str:
        return f"{self.file_path}::{self.name}"

    def to_dict(self):
        return {
            "name": self.name,
            "kind": self.kind,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "end_line_number": self.end_line_number,
            "params": self.params,
            "posonly_params": self.posonly_params,
            "kwonly_params": self.kwonly_params,
            "required_params": self.required_params,
            "min_required_params": self.min_required_params,
            "max_positional_params": self.max_positional_params,
            "has_varargs": self.has_varargs,
            "has_kwargs": self.has_kwargs,
            "signature": self.signature,
            "is_test": self.is_test,
        }


@dataclass
class CallSite:
    caller_name: str
    callee_name: str
    file_path: str
    line_number: int
    args_count: int = 0
    kwargs_names: List[str] = field(default_factory=list)
    snippet: str = ""
    callee_module: Optional[str] = None
    is_method_call: bool = False

    @property
    def caller_identifier(self) -> str:
        return f"{self.file_path}::{self.caller_name}"

    def to_dict(self):
        return {
            "caller_name": self.caller_name,
            "callee_name": self.callee_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "args_count": self.args_count,
            "kwargs_names": self.kwargs_names,
            "snippet": self.snippet,
            "callee_module": self.callee_module,
            "is_method_call": self.is_method_call,
        }


@dataclass
class ParsedFile:
    file_path: str
    symbols: List[Symbol] = field(default_factory=list)
    call_sites: List[CallSite] = field(default_factory=list)
    imports: Dict[str, str] = field(default_factory=dict)  # imported name/alias -> source module/file
    is_test_file: bool = False
