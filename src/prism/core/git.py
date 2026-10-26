"""
Git integration for extracting working tree modifications, diff hunks, and touched symbols.
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
    "tests",
    "test",
}


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


def get_git_diff_lines(root: Path) -> Dict[str, Set[int]]:
    """Return a mapping of relative file path -> set of modified line numbers."""
    diff_lines: Dict[str, Set[int]] = {}
    if not is_git_repo(root):
        return diff_lines

    try:
        # Run diff against HEAD (both staged and unstaged changes)
        res = subprocess.run(
            ["git", "diff", "HEAD", "--unified=0"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            current_file: Optional[str] = None
            for line in res.stdout.splitlines():
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

        # Also capture untracked files from git status
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
                # If untracked file (??) or new file (A)
                if code.strip() in ("??", "A") and rel_path not in diff_lines:
                    diff_lines[rel_path] = set()  # empty set means whole file is new
    except (subprocess.SubprocessError, OSError):
        pass

    return diff_lines


def discover_all_source_files(root: Path) -> List[Path]:
    """Recursively discover all supported source files in the project."""
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".")]
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
            # If empty set, whole file is new/untracked -> all symbols modified
            if not lines:
                modified_symbols.extend(parsed.symbols)
            else:
                for sym in parsed.symbols:
                    # Symbol intersects if any diff line falls in [line_number, end_line_number]
                    sym_range = range(sym.line_number, sym.end_line_number + 1)
                    if any(line_no in sym_range for line_no in lines):
                        modified_symbols.append(sym)
    return modified_symbols
