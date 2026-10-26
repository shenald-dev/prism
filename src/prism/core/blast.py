"""
Blast Radius calculation engine.
Computes impact scores, ripple shockwaves, and overall risk levels across repositories.
"""

from dataclasses import dataclass, field
from typing import List, Set

from prism.core.contracts import ContractViolation, check_contract_violations
from prism.core.graph import CallerNode, DependencyGraph
from prism.parsers.base import Symbol


@dataclass
class SymbolBlast:
    symbol: Symbol
    blast_tree: List[CallerNode]
    affected_functions: Set[str]
    affected_files: Set[str]
    violations: List[ContractViolation]


@dataclass
class BlastRadiusReport:
    symbol_blasts: List[SymbolBlast]
    total_files_scanned: int
    duration_seconds: float
    all_affected_functions: Set[str] = field(default_factory=set)
    all_affected_files: Set[str] = field(default_factory=set)
    all_violations: List[ContractViolation] = field(default_factory=list)
    impact_score: int = 0
    risk_level: str = "LOW"  # LOW, MODERATE, ELEVATED, CRITICAL
    color: str = "green"

    @property
    def modified_symbols_count(self) -> int:
        return len(self.symbol_blasts)

    @property
    def direct_callers_count(self) -> int:
        count = 0
        for sb in self.symbol_blasts:
            count += len(sb.blast_tree)
        return count

    @property
    def transitive_callers_count(self) -> int:
        return max(0, len(self.all_affected_functions) - self.modified_symbols_count - self.direct_callers_count)

    def to_dict(self):
        return {
            "impact_score": self.impact_score,
            "risk_level": self.risk_level,
            "duration_seconds": round(self.duration_seconds, 3),
            "files_scanned": self.total_files_scanned,
            "metrics": {
                "modified_symbols": self.modified_symbols_count,
                "direct_callers": self.direct_callers_count,
                "transitive_callers": self.transitive_callers_count,
                "total_affected_files": len(self.all_affected_files),
                "contract_violations": len(self.all_violations),
            },
            "violations": [v.to_dict() for v in self.all_violations],
            "symbols": [
                {
                    "name": sb.symbol.name,
                    "kind": sb.symbol.kind,
                    "file_path": sb.symbol.file_path,
                    "signature": sb.symbol.signature,
                    "affected_functions": list(sb.affected_functions),
                    "affected_files": list(sb.affected_files),
                    "violations": [v.to_dict() for v in sb.violations],
                    "tree": [node.to_dict() for node in sb.blast_tree],
                }
                for sb in self.symbol_blasts
            ],
        }


def compute_blast_radius(
    modified_symbols: List[Symbol],
    graph: DependencyGraph,
    total_files_scanned: int,
    duration_seconds: float,
    max_depth: int = 5,
) -> BlastRadiusReport:
    """Analyze modified symbols and compute comprehensive blast radius report."""
    symbol_blasts = []
    all_affected_functions: Set[str] = set()
    all_affected_files: Set[str] = set()
    all_violations: List[ContractViolation] = []

    for sym in modified_symbols:
        tree, affected_funcs, affected_files = graph.compute_blast_tree(sym, max_depth=max_depth)
        incoming_calls = graph.get_direct_callers(sym.name)
        violations = check_contract_violations(sym, incoming_calls)

        all_affected_functions.update(affected_funcs)
        all_affected_files.update(affected_files)
        all_violations.extend(violations)

        symbol_blasts.append(
            SymbolBlast(
                symbol=sym,
                blast_tree=tree,
                affected_functions=affected_funcs,
                affected_files=affected_files,
                violations=violations,
            )
        )

    # Compute Impact Score (0 - 100)
    raw_score = 0
    # Direct callers: +6 pts each
    raw_score += sum(len(sb.blast_tree) * 6 for sb in symbol_blasts)
    # Transitive callers: +3 pts each
    raw_score += max(0, len(all_affected_functions) - len(symbol_blasts)) * 3
    # Affected files: +5 pts each
    raw_score += len(all_affected_files) * 5
    # Violations: +25 pts each
    raw_score += len(all_violations) * 25

    impact_score = min(100, raw_score)

    # Determine Risk Level
    has_critical_violations = any(v.severity == "CRITICAL" for v in all_violations)
    if has_critical_violations or impact_score >= 70:
        risk_level = "CRITICAL"
        color = "red"
    elif all_violations or impact_score >= 40:
        risk_level = "ELEVATED"
        color = "yellow"
    elif impact_score >= 15:
        risk_level = "MODERATE"
        color = "cyan"
    else:
        risk_level = "LOW"
        color = "green"

    return BlastRadiusReport(
        symbol_blasts=symbol_blasts,
        total_files_scanned=total_files_scanned,
        duration_seconds=duration_seconds,
        all_affected_functions=all_affected_functions,
        all_affected_files=all_affected_files,
        all_violations=all_violations,
        impact_score=impact_score,
        risk_level=risk_level,
        color=color,
    )
