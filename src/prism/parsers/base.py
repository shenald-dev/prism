"""
Base representations for AST symbols, function signatures, and call sites.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Symbol:
    name: str
    kind: str  # "function", "async_function", "method", "class"
    file_path: str
    line_number: int
    end_line_number: int
    params: List[str] = field(default_factory=list)
    min_required_params: int = 0
    has_varargs: bool = False
    has_kwargs: bool = False
    signature: str = ""
    docstring: Optional[str] = None

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
            "min_required_params": self.min_required_params,
            "has_varargs": self.has_varargs,
            "has_kwargs": self.has_kwargs,
            "signature": self.signature,
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
        }


@dataclass
class ParsedFile:
    file_path: str
    symbols: List[Symbol] = field(default_factory=list)
    call_sites: List[CallSite] = field(default_factory=list)
