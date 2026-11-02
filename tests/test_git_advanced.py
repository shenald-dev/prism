import subprocess
from pathlib import Path

from prism.core.git import (
    _parse_unified_diff,
    discover_all_source_files,
    get_git_diff_lines,
    identify_modified_symbols,
    is_git_repo,
)
from prism.parsers.base import ParsedFile, Symbol


def test_is_git_repo_true(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    assert is_git_repo(tmp_path) is True


def test_is_git_repo_false(tmp_path: Path):
    sub = tmp_path / "not_git"
    sub.mkdir()
    assert is_git_repo(sub) is False


def test_parse_unified_diff():
    diff_text = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -10,0 +11,3 @@
+def new_func():
+    pass
+
@@ -25,2 +28,1 @@
-old_code()
+new_code()
"""
    result = _parse_unified_diff(diff_text)
    assert "src/app.py" in result
    assert {11, 12, 13, 28}.issubset(result["src/app.py"])


def test_discover_all_source_files_filter(tmp_path: Path):
    # Regular source
    (tmp_path / "app.py").write_text("x = 1")
    (tmp_path / "web.ts").write_text("const y = 2;")
    # Test file
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_app.py").write_text("def test_x(): pass")
    # Ignored directory
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "lib.py").write_text("z = 3")

    with_tests = discover_all_source_files(tmp_path, include_tests=True)
    file_names = [f.name for f in with_tests]
    assert "app.py" in file_names
    assert "web.ts" in file_names
    assert "test_app.py" in file_names
    assert "lib.py" not in file_names

    no_tests = discover_all_source_files(tmp_path, include_tests=False)
    no_tests_names = [f.name for f in no_tests]
    assert "test_app.py" not in no_tests_names
    assert "app.py" in no_tests_names


def test_identify_modified_symbols():
    sym1 = Symbol("active", "function", "service.py", 10, 20)
    sym2 = Symbol("inactive", "function", "service.py", 30, 40)
    parsed = ParsedFile("service.py", symbols=[sym1, sym2])

    diff_lines = {"service.py": {15}}
    modified = identify_modified_symbols(diff_lines, {"service.py": parsed})
    assert len(modified) == 1
    assert modified[0].name == "active"

    # Entirely untracked file (empty diff set)
    untracked_diff = {"service.py": set()}
    modified_all = identify_modified_symbols(untracked_diff, {"service.py": parsed})
    assert len(modified_all) == 2


def test_get_git_diff_lines_in_real_repo(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp_path), check=True)

    file_a = tmp_path / "hello.py"
    file_a.write_text("def foo():\n    return 1\n")
    subprocess.run(["git", "add", "hello.py"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), check=True)

    # Edit file without staging
    file_a.write_text("def foo(x):\n    return x\n")
    diffs = get_git_diff_lines(tmp_path)
    assert "hello.py" in diffs
    assert 1 in diffs["hello.py"]
