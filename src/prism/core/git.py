"""
Git integration for extracting working tree modifications, revision diff hunks,
and touched symbols across branches, commits, and uncommitted changes.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set

from prism.parsers.base import ParsedFile, Symbol

SUPPORTED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".next",
    "dist",
    "build",
    "venv",
    ".venv",
    "env",
    ".env",
    "target",
    "out",
    ".tox",
    ".mypy_cache",
}
TEST_DIRS = {"tests", "test", "__tests__"}


def is_git_repo(root: Path) -> bool:
    """Check if root is inside a git repository."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        return res.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def _parse_unified_diff(stdout: str) -> Dict[str, Set[int]]:
    """Parse git diff --unified=0 output into a mapping of file_path -> set of modified line numbers."""
    diff_lines: Dict[str, Set[int]] = {}
    current_file: Optional[str] = None

    for line in stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip().replace("\\", "/")
            if current_file not in diff_lines:
                diff_lines[current_file] = set()
        elif line.startswith("@@ ") and current_file:
            try:
                hunk_header = line.split("@@")[1].strip()
                plus_part = hunk_header.split()[1]  # +12,5 or +12
                start_line = int(plus_part[1:].split(",")[0])
                count = 1
                if "," in plus_part:
                    count = int(plus_part.split(",")[1])
                for l_num in range(start_line, start_line + max(count, 1)):
                    diff_lines[current_file].add(l_num)
            except (ValueError, IndexError):
                continue

    return diff_lines


def get_git_diff_lines(
    root: Path,
    base: Optional[str] = None,
    head: Optional[str] = None,
    staged: bool = False,
    commit: Optional[str] = None,
) -> Dict[str, Set[int]]:
    """
    Return a mapping of relative file path -> set of modified line numbers.
    Supports working tree diffs, staged-only diffs, revision comparisons (base...head),
    and specific commits.
    """
    diff_lines: Dict[str, Set[int]] = {}
    if not is_git_repo(root):
        return diff_lines

    try:
        # Determine git command
        cmd = ["git", "diff", "--unified=0"]

        if commit:
            # Show changes introduced by specific commit
            cmd.extend([f"{commit}^!"])
        elif staged:
            # Staged changes only
            cmd.extend(["--cached"])
        elif base and head:
            # Range diff
            cmd.extend([f"{base}...{head}"])
        elif base:
            # Diff against base branch or reference
            cmd.extend([base])
        else:
            # Auto-detect GitHub Actions PR base if clean checkout
            ci_base = os.getenv("GITHUB_BASE_REF")
            if ci_base:
                cmd.extend([f"origin/{ci_base}...HEAD"])
            else:
                # Default: unstaged + staged working tree changes against HEAD
                cmd.extend(["HEAD"])

        res = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            diff_lines = _parse_unified_diff(res.stdout)

        # In working tree mode (no commit or range specified), also capture untracked files
        if not commit and not base:
            status_res = subprocess.run(
                ["git", "status", "--porcelain", "-uall"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )
            if status_res.returncode == 0:
                for line in status_res.stdout.splitlines():
                    if not line.strip():
                        continue
                    code = line[:2]
                    rel_path = line[3:].strip().split(" -> ")[-1].strip().replace("\\", "/")
                    if code.strip() in ("??", "A") and rel_path not in diff_lines:
                        diff_lines[rel_path] = set()  # empty set represents whole file is new
    except (subprocess.SubprocessError, OSError):
        pass

    return diff_lines


def discover_all_source_files(root: Path, include_tests: bool = True) -> List[Path]:
    """Recursively discover all supported source files in the project."""
    files: List[Path] = []
    ignored = set(IGNORED_DIRS)
    if not include_tests:
        ignored.update(TEST_DIRS)

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignored and not d.startswith(".")]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                files.append(Path(dirpath) / f)
    return files


def identify_modified_symbols(
    diff_lines: Dict[str, Set[int]], parsed_files: Dict[str, ParsedFile]
) -> List[Symbol]:
    """Identify which symbols intersect with git modified lines."""
    modified_symbols = []
    for rel_path, lines in diff_lines.items():
        if rel_path in parsed_files:
            parsed = parsed_files[rel_path]
            # Empty set signifies newly added / untracked file -> all symbols modified
            if not lines:
                modified_symbols.extend(parsed.symbols)
            else:
                for sym in parsed.symbols:
                    sym_range = range(sym.line_number, sym.end_line_number + 1)
                    if any(line_no in sym_range for line_no in lines):
                        modified_symbols.append(sym)
    return modified_symbols
