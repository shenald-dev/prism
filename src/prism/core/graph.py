"""
Directed Dependency & Call Graph engine for calculating caller cascades and dependencies.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from prism.parsers.base import CallSite, Symbol


@dataclass
class CallerNode:
    caller_symbol: str  # file_path::name
    file_path: str
    line_number: int
    depth: int
    args_count: int = 0
    kwargs_names: List[str] = field(default_factory=list)
    snippet: str = ""
    children: List["CallerNode"] = field(default_factory=list)

    def to_dict(self):
        return {
            "caller_symbol": self.caller_symbol,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "depth": self.depth,
            "args_count": self.args_count,
            "kwargs_names": self.kwargs_names,
            "snippet": self.snippet,
            "children": [c.to_dict() for c in self.children],
        }


class DependencyGraph:
    def __init__(self):
        # symbol_name -> list of Symbol definitions
        self.symbols_by_name: Dict[str, List[Symbol]] = defaultdict(list)
        # symbol_identifier (file::name) -> Symbol
        self.symbols_by_id: Dict[str, Symbol] = {}
        # callee_name -> list of CallSites that call it
        self.incoming_calls: Dict[str, List[CallSite]] = defaultdict(list)
        # caller_id -> list of callee names
        self.outgoing_calls: Dict[str, List[str]] = defaultdict(list)

    def add_symbol(self, symbol: Symbol):
        self.symbols_by_name[symbol.name].append(symbol)
        self.symbols_by_id[symbol.identifier] = symbol

    def add_call_site(self, call: CallSite):
        self.incoming_calls[call.callee_name].append(call)
        self.outgoing_calls[call.caller_identifier].append(call.callee_name)

    def get_direct_callers(self, symbol_name: str) -> List[CallSite]:
        """Return all call sites that directly invoke symbol_name."""
        return self.incoming_calls.get(symbol_name, [])

    def compute_blast_tree(
        self, symbol: Symbol, max_depth: int = 5
    ) -> Tuple[List[CallerNode], Set[str], Set[str]]:
        """
        Compute the transitive caller cascade (blast tree) for a given symbol.
        Returns:
            - root_caller_nodes: Tree representation of callers
            - affected_functions: Set of all affected function identifiers
            - affected_files: Set of all affected file paths
        """
        visited_callers: Set[str] = set()
        affected_functions: Set[str] = {symbol.identifier}
        affected_files: Set[str] = {symbol.file_path}

        def _traverse(current_name: str, depth: int) -> List[CallerNode]:
            if depth > max_depth:
                return []

            nodes = []
            direct_calls = self.incoming_calls.get(current_name, [])

            for call in direct_calls:
                call_id = f"{call.file_path}::{call.caller_name}:{call.line_number}"
                if call_id in visited_callers:
                    continue
                visited_callers.add(call_id)

                affected_functions.add(call.caller_identifier)
                affected_files.add(call.file_path)

                node = CallerNode(
                    caller_symbol=call.caller_identifier,
                    file_path=call.file_path,
                    line_number=call.line_number,
                    depth=depth,
                    args_count=call.args_count,
                    kwargs_names=call.kwargs_names,
                    snippet=call.snippet,
                )

                # Transitive traversal if caller is a known function
                if call.caller_name != "<module>":
                    node.children = _traverse(call.caller_name, depth + 1)

                nodes.append(node)

            return nodes

        blast_tree = _traverse(symbol.name, depth=1)
        return blast_tree, affected_functions, affected_files
