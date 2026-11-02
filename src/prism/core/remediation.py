"""
AI Agent Remediation & Context Generator.
Generates high-density, zero-hallucination prompt context and actionable fix instructions
for autonomous agent coding loops (Claude Code, Cursor, Copilot, Aider, Devin).
"""

from typing import List

from prism.core.contracts import ContractViolation
from prism.parsers.base import Symbol


def generate_agent_remediation_prompt(
    modified_symbols: List[Symbol],
    violations: List[ContractViolation],
    risk_level: str,
    impact_score: int,
) -> str:
    """Generate high-density prompt context for autonomous agents to self-heal callers."""
    lines = [
        "### 💎 PRISM INVARIANT RADAR: CONTRACT REMEDIATION CONTEXT",
        f"**Risk Level:** `{risk_level}` | **Topological Impact Score:** `{impact_score}/100`",
        "",
        "A recent code change has introduced contract mismatches or broken downstream callers.",
        "Please review the updated symbol signatures and fix each broken callsite accordingly.",
        "",
        "#### 📦 Updated Target Signatures:",
    ]

    for sym in modified_symbols:
        lines.append(f"- **`{sym.name}`** (`{sym.file_path}:{sym.line_number}`)")
        lines.append(f"  ```python\n  {sym.signature}\n  ```")
        if sym.required_params:
            req_str = ", ".join(f"`{p}`" for p in sym.required_params)
            lines.append(f"  - Required arguments: {req_str}")
        if sym.max_positional_params is not None:
            lines.append(f"  - Max positional arguments: `{sym.max_positional_params}`")

    lines.append("")
    lines.append(f"#### 🚨 Contract Violations to Remediate ({len(violations)}):")

    if not violations:
        lines.append("*No broken contracts detected. Call sites conform to updated signatures.*")
    else:
        for i, v in enumerate(violations, start=1):
            lines.append(f"**{i}. Caller:** `{v.caller_file}:{v.caller_line}` in `{v.caller_identifier}`")
            lines.append(f"- **Target Callee:** `{v.callee_file}::{v.callee_name}`")
            lines.append(f"- **Severity:** `{v.severity}`")
            lines.append(f"- **Diagnosis:** {v.reason}")
            if v.snippet:
                lines.append(f"- **Current Code:**\n  ```text\n  {v.snippet}\n  ```")
            lines.append(f"- **Action Required:** {v.suggested_fix}")
            lines.append("")

    lines.append("#### 🛠️ Instructions for Agent:")
    lines.append("1. Open the caller files listed above.")
    lines.append("2. Update each call site to match the target function's updated signature.")
    lines.append("3. Re-run `prism scan --strict` to verify all contracts are satisfied before committing.")

    return "\n".join(lines)
