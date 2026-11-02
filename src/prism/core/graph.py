"""
Directed Dependency & Call Graph engine for calculating caller cascades, blast trees,
and transitive impact shockwaves.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Union

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
    is_test: bool = False
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
            "is_test": self.is_test,
            "children": [c.to_dict() for c in self.children],
        }


class DependencyGraph:
    def __init__(self):
        # callee_name -> list of CallSites that call it
        self.incoming_calls: Dict[str, List[CallSite]] = defaultdict(list)
        # qualified callee (file/module::name) -> list of CallSites
        self.incoming_by_module: Dict[str, List[CallSite]] = defaultdict(list)
        # symbol_identifier -> Symbol
        self.symbols: Dict[str, Symbol] = {}

    def register_symbol(self, symbol: Symbol):
        """Register a symbol in the graph index."""
        self.symbols[symbol.identifier] = symbol
        self.symbols[symbol.name] = symbol

    def add_call_site(self, call: CallSite):
        """Add a call site to graph indices."""
        self.incoming_calls[call.callee_name].append(call)
        if call.callee_module:
            self.incoming_by_module[call.callee_module].append(call)

    def get_direct_callers(self, target: Union[Symbol, str]) -> List[CallSite]:
        """
        Return all call sites that directly invoke target symbol.
        Accepts either a Symbol instance or a string name.
        """
        target_name = target.name if isinstance(target, Symbol) else target
        calls = self.incoming_calls.get(target_name, [])

        if isinstance(target, Symbol):
            # Prioritize matching file/module if available
            scoped_calls = []
            target_file_stem = target.file_path.split("/")[-1].split(".")[0]
            for call in calls:
                if call.callee_module:
                    # Check if callee_module matches file path or module name
                    if target.file_path in call.callee_module or target_file_stem in call.callee_module:
                        scoped_calls.append(call)
                    elif "::" in call.callee_module and call.callee_module.endswith(f"::{target.name}"):
                        scoped_calls.append(call)
                    else:
                        scoped_calls.append(call)
                else:
                    scoped_calls.append(call)
            return scoped_calls

        return calls

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
        affected_functions: Set[str] = {symbol.identifier}
        affected_files: Set[str] = {symbol.file_path}

        def _traverse(current_name: str, depth: int, visited_path: Set[str]) -> List[CallerNode]:
            if depth > max_depth:
                return []

            nodes = []
            direct_calls = self.incoming_calls.get(current_name, [])

            for call in direct_calls:
                call_id = f"{call.file_path}::{call.caller_name}:{call.line_number}"
                if call_id in visited_path:
                    continue

                affected_functions.add(call.caller_identifier)
                affected_files.add(call.file_path)

                # Check if caller is known to be a test
                caller_sym = self.symbols.get(call.caller_identifier)
                is_test = (
                    (caller_sym.is_test if caller_sym else False)
                    or call.caller_name.startswith("test_")
                    or "test" in call.file_path.lower()
                )

                node = CallerNode(
                    caller_symbol=call.caller_identifier,
                    file_path=call.file_path,
                    line_number=call.line_number,
                    depth=depth,
                    args_count=call.args_count,
                    kwargs_names=call.kwargs_names,
                    snippet=call.snippet,
                    is_test=is_test,
                )

                # Transitive traversal if caller is a defined function/method
                if call.caller_name != "<module>":
                    node.children = _traverse(
                        call.caller_name,
                        depth + 1,
                        visited_path | {call_id},
                    )

                nodes.append(node)

            return nodes

        blast_tree = _traverse(symbol.name, depth=1, visited_path=set())
        return blast_tree, affected_functions, affected_files
