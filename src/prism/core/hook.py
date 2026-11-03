"""
Pre-commit hook and CI integration generator for PRISM.
Installs native Git pre-commit hooks and generates GitHub Actions workflows.
"""

from pathlib import Path

PRE_COMMIT_SCRIPT = """#!/usr/bin/env sh
# PRISM Pre-Commit Blast Radius & Contract Guard
# Installed by `prism hook install`

echo "💎 PRISM: Checking topological blast radius & contract invariants..."
prism scan --staged --strict

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ PRISM: Commit aborted due to broken contracts or high blast radius."
    echo "Run 'prism explain' for remediation prompt or 'prism fix --apply' to auto-patch."
    exit $EXIT_CODE
fi

exit 0
"""

GITHUB_ACTIONS_WORKFLOW = """name: PRISM Blast Radius Radar

on:
  pull_request:
    branches: [main, master]
  push:
    branches: [main, master]

jobs:
  prism-radar:
    name: Blast Radius & Contract Radar
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install PRISM
        run: |
          pip install git+https://github.com/shenald-dev/prism.git

      - name: Run PRISM Blast Radius Radar
        run: |
          prism scan --base origin/main --format sarif --output prism.sarif --format markdown > prism-summary.md
          cat prism-summary.md >> $GITHUB_STEP_SUMMARY
        continue-on-error: true

      - name: Upload SARIF to GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: prism.sarif
          category: prism-radar
"""


def install_git_pre_commit_hook(repo_root: Path) -> Path:
    """Install native pre-commit hook into .git/hooks/pre-commit."""
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-commit"
    hook_file.write_text(PRE_COMMIT_SCRIPT, encoding="utf-8")
    try:
        hook_file.chmod(0o755)
    except Exception:
        pass
    return hook_file


def init_github_actions_workflow(repo_root: Path) -> Path:
    """Create .github/workflows/prism-radar.yml."""
    workflows_dir = repo_root / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    workflow_file = workflows_dir / "prism-radar.yml"
    workflow_file.write_text(GITHUB_ACTIONS_WORKFLOW, encoding="utf-8")
    return workflow_file
