from pathlib import Path

from prism.core.hook import init_github_actions_workflow, install_git_pre_commit_hook


def test_install_git_pre_commit_hook(tmp_path: Path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    hook_file = install_git_pre_commit_hook(tmp_path)

    assert hook_file.exists()
    assert hook_file == tmp_path / ".git" / "hooks" / "pre-commit"
    content = hook_file.read_text(encoding="utf-8")
    assert "prism scan --staged --strict" in content
    assert "PRISM Pre-Commit Blast Radius & Contract Guard" in content


def test_init_github_actions_workflow(tmp_path: Path):
    workflow_file = init_github_actions_workflow(tmp_path)

    assert workflow_file.exists()
    assert workflow_file == tmp_path / ".github" / "workflows" / "prism-radar.yml"
    content = workflow_file.read_text(encoding="utf-8")
    assert "name: PRISM Blast Radius Radar" in content
    assert "prism scan --base origin/main" in content
    assert "upload-sarif" in content
