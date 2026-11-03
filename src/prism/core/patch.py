"""
Automated Call-site Remediation Patch Generator.
Generates unified diff patches and applies fixes for contract invariant violations.
"""

from pathlib import Path
from typing import List, Tuple

from prism.core.contracts import ContractViolation


class PatchGenerator:
    """Generates unified diff patches and applies call-site remediations."""

    @staticmethod
    def remediate_snippet(violation: ContractViolation) -> Tuple[str, str]:
        """Produce (original_line, replacement_line) for a violation snippet."""
        orig = violation.snippet.strip()
        callee = violation.callee_name

        # Case 1: Unawaited coroutine call
        if "Unawaited coroutine" in violation.reason:
            # Add 'await ' before callee invocation if not present
            if f"{callee}(" in orig and not orig.startswith("await "):
                # If assigned: x = callee(...) -> x = await callee(...)
                if "=" in orig:
                    left, right = orig.split("=", 1)
                    repl = f"{left.strip()} = await {right.strip()}"
                elif orig.startswith("return "):
                    repl = orig.replace("return ", "return await ", 1)
                else:
                    repl = f"await {orig}"
                return orig, repl

        # Case 2: Awaiting synchronous function
        if "Awaiting synchronous function" in violation.reason:
            if "await " in orig:
                repl = orig.replace("await ", "", 1).strip()
                return orig, repl

        return orig, orig

    @classmethod
    def generate_patch(cls, violations: List[ContractViolation], root_path: Path) -> str:
        """Generate a unified diff patch string for all resolvable violations."""
        diff_chunks = []
        files_seen = set()

        for v in violations:
            caller_file = root_path / v.caller_file
            if not caller_file.is_file():
                continue

            orig_line, repl_line = cls.remediate_snippet(v)
            if orig_line == repl_line:
                continue

            rel_path = v.caller_file.replace("\\", "/")
            header = f"--- a/{rel_path}\n+++ b/{rel_path}\n@@ -{v.caller_line},1 +{v.caller_line},1 @@\n"
            chunk = f"{header}-  {orig_line}\n+  {repl_line}\n"
            diff_chunks.append(chunk)
            files_seen.add(rel_path)

        return "".join(diff_chunks)

    @classmethod
    def apply_fixes(cls, violations: List[ContractViolation], root_path: Path) -> int:
        """Directly modify the caller files to fix resolvable violations."""
        applied_count = 0

        for v in violations:
            caller_file = root_path / v.caller_file
            if not caller_file.is_file():
                continue

            orig_line, repl_line = cls.remediate_snippet(v)
            if orig_line == repl_line:
                continue

            try:
                content = caller_file.read_text(encoding="utf-8")
                lines = content.splitlines()
                if 1 <= v.caller_line <= len(lines):
                    current_line = lines[v.caller_line - 1]
                    if orig_line in current_line:
                        # Replace matching snippet while preserving indentation
                        indent = current_line[: len(current_line) - len(current_line.lstrip())]
                        lines[v.caller_line - 1] = f"{indent}{repl_line.strip()}"
                        caller_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
                        applied_count += 1
            except Exception:
                continue

        return applied_count
