from pathlib import Path

from typer.testing import CliRunner

from prism.cli import app

runner = CliRunner()


def test_cli_scan_mermaid_format(tmp_path: Path):
    f = tmp_path / "app.py"
    f.write_text("def run():\n    pass\n\ndef main():\n    run()\n")

    res = runner.invoke(app, ["scan", str(tmp_path), "--all", "--format", "mermaid"])
    assert res.exit_code == 0
    assert "graph TD" in res.stdout


def test_cli_scan_dot_format(tmp_path: Path):
    f = tmp_path / "app.py"
    f.write_text("def run():\n    pass\n\ndef main():\n    run()\n")

    res = runner.invoke(app, ["scan", str(tmp_path), "--all", "--format", "dot"])
    assert res.exit_code == 0
    assert "digraph PrismBlastRadius" in res.stdout


def test_cli_visual_command_mermaid(tmp_path: Path):
    f = tmp_path / "app.py"
    f.write_text("def greet(): return 'hi'\n\ndef run(): greet()\n")

    res = runner.invoke(app, ["visual", str(tmp_path), "--format", "mermaid"])
    assert res.exit_code == 0
    assert "graph TD" in res.stdout


def test_cli_visual_command_dot_file(tmp_path: Path):
    f = tmp_path / "app.py"
    f.write_text("def greet(): return 'hi'\n\ndef run(): greet()\n")
    out_file = tmp_path / "diagram.dot"

    res = runner.invoke(app, ["visual", str(tmp_path), "--format", "dot", "-o", str(out_file)])
    assert res.exit_code == 0
    assert out_file.exists()
    assert "digraph PrismBlastRadius" in out_file.read_text(encoding="utf-8")


def test_cli_fix_display_and_patch(tmp_path: Path):
    f = tmp_path / "service.py"
    f.write_text("async def fetch(): pass\n\ndef run():\n    fetch()\n")
    patch_file = tmp_path / "fix.patch"

    # Display patch
    res = runner.invoke(app, ["fix", str(tmp_path)])
    assert res.exit_code == 0
    assert "Proposed Call-site Remediation Patch" in res.stdout

    # Write patch file
    res = runner.invoke(app, ["fix", str(tmp_path), "--patch", str(patch_file)])
    assert res.exit_code == 0
    assert patch_file.exists()
    assert "await fetch()" in patch_file.read_text(encoding="utf-8")


def test_cli_fix_apply(tmp_path: Path):
    f = tmp_path / "service.py"
    f.write_text("async def fetch(): pass\n\ndef run():\n    fetch()\n")

    res = runner.invoke(app, ["fix", str(tmp_path), "--apply"])
    assert res.exit_code == 0
    assert "Successfully applied fixes to 1 callsite(s)" in res.stdout
    assert "await fetch()" in f.read_text(encoding="utf-8")


def test_cli_hook_install(tmp_path: Path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    res = runner.invoke(app, ["hook", "install", str(tmp_path)])
    assert res.exit_code == 0
    assert (tmp_path / ".git" / "hooks" / "pre-commit").exists()


def test_cli_ci_init(tmp_path: Path):
    res = runner.invoke(app, ["ci", "init", str(tmp_path)])
    assert res.exit_code == 0
    assert (tmp_path / ".github" / "workflows" / "prism-radar.yml").exists()
