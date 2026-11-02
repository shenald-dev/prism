"""
Blast Radius calculation engine.
Computes impact scores, ripple shockwaves, test impact, and overall risk levels across repositories.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from prism.core.config import PrismConfig
from prism.core.contracts import ContractViolation, check_contract_violations
from prism.core.graph import CallerNode, DependencyGraph
from prism.core.sarif import export_sarif
from prism.core.tests import TestImpactSummary, analyze_test_impact
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
    test_impact: Optional[TestImpactSummary] = None

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

    def to_dict(self) -> Dict[str, Any]:
        result = {
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
        if self.test_impact:
            result["test_impact"] = self.test_impact.to_dict()
        return result

    def to_sarif(self) -> Dict[str, Any]:
        return export_sarif(self.all_violations)

    def to_markdown(self) -> str:
        """Render a GitHub Flavored Markdown report for CI step summaries and PR comments."""
        risk_emojis = {
            "LOW": "🟢",
            "MODERATE": "🟡",
            "ELEVATED": "🟠",
            "CRITICAL": "🚨",
        }
        emoji = risk_emojis.get(self.risk_level, "💎")

        lines = [
            f"## {emoji} PRISM: Topological Blast Radius Report",
            f"**Impact Score:** `{self.impact_score}/100` | **Risk Level:** `{self.risk_level}` | **Scan Latency:** `{self.duration_seconds:.3f}s`",
            "",
            "| Metric | Count |",
            "| :--- | :--- |",
            f"| 📦 **Modified Symbols** | {self.modified_symbols_count} |",
            f"| 🎯 **Direct Callers (L1)** | {self.direct_callers_count} |",
            f"| 🌊 **Transitive Callers** | {self.transitive_callers_count} |",
            f"| 📁 **Affected Files** | {len(self.all_affected_files)} |",
            f"| 🚨 **Contract Violations** | {len(self.all_violations)} |",
            "",
        ]

        if self.all_violations:
            lines.extend([
                "### 🚨 Contract Invariant Violations",
                "",
                "| Severity | Caller Location | Target Function | Diagnosis | Suggested Fix |",
                "| :---: | :--- | :--- | :--- | :--- |",
            ])
            for v in self.all_violations:
                sev_badge = "🔴 **CRITICAL**" if v.severity == "CRITICAL" else "🟡 **HIGH**"
                loc = f"`{v.caller_file}:{v.caller_line}`"
                target = f"`{v.callee_name}`"
                diag = v.reason.replace("|", "\\|")
                fix = v.suggested_fix.replace("|", "\\|")
                lines.append(f"| {sev_badge} | {loc} | {target} | {diag} | {fix} |")
            lines.append("")

        if self.test_impact:
            lines.extend([
                "### 🧪 Test Impact Radar",
                f"- **Impacted Test Files:** `{len(self.test_impact.impacted_test_files)}`",
                f"- **Impacted Test Cases:** `{len(self.test_impact.impacted_test_cases)}`",
            ])
            if self.test_impact.recommended_command:
                lines.append(f"- **Recommended Test Command:** `{self.test_impact.recommended_command}`")
            if self.test_impact.untested_symbols:
                lines.append(f"- ⚠️ **Untested Symbols:** {', '.join(f'`{s}`' for s in self.test_impact.untested_symbols)}")
            lines.append("")

        return "\n".join(lines)


def compute_blast_radius(
    modified_symbols: List[Symbol],
    graph: DependencyGraph,
    total_files_scanned: int,
    duration_seconds: float,
    max_depth: int = 5,
    include_tests: bool = True,
    config: Optional[PrismConfig] = None,
) -> BlastRadiusReport:
    """Analyze modified symbols and compute comprehensive blast radius report."""
    cfg = config or PrismConfig()
    effective_depth = max_depth if max_depth != 5 else cfg.max_depth

    # Filter out ignored symbols if defined
    active_symbols = [
        sym for sym in modified_symbols
        if sym.name not in cfg.ignore_symbols
    ]

    symbol_blasts = []
    all_affected_functions: Set[str] = set()
    all_affected_files: Set[str] = set()
    all_violations: List[ContractViolation] = []

    for sym in active_symbols:
        tree, affected_funcs, affected_files = graph.compute_blast_tree(sym, max_depth=effective_depth)
        incoming_calls = graph.get_direct_callers(sym)
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
    direct_callers_count = sum(len(sb.blast_tree) for sb in symbol_blasts)
    transitive_callers_count = max(0, len(all_affected_functions) - len(symbol_blasts) - direct_callers_count)

    # Direct callers: +6 pts each
    raw_score += direct_callers_count * 6
    # Transitive callers: +3 pts each
    raw_score += transitive_callers_count * 3
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

    test_impact = None
    if include_tests:
        test_impact = analyze_test_impact(
            modified_symbols=active_symbols,
            all_affected_functions=all_affected_functions,
            all_affected_files=all_affected_files,
        )

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
        test_impact=test_impact,
    )
