import json
from typer.testing import CliRunner
from prism.cli import app

runner = CliRunner()

def test_cli_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "prism version" in res.stdout

def test_cli_scan_clean_dir(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def hello():\n    return 'world'\n")
    
    res = runner.invoke(app, ["scan", str(tmp_path), "--all"])
    assert res.exit_code == 0
    assert "Topological Ripple Shockwave" in res.stdout
    assert "LOW RISK" in res.stdout

def test_cli_scan_json_output(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def calc(x):\n    return x * 2\ndef main():\n    calc(5)\n")
    
    res = runner.invoke(app, ["scan", str(tmp_path), "--all", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert "impact_score" in data
    assert "metrics" in data
    assert data["metrics"]["modified_symbols"] >= 1

def test_cli_strict_fails_on_broken_contract(tmp_path):
    f = tmp_path / "service.py"
    f.write_text("""
def save_user(username, email, role):
    pass

def handler():
    save_user('alice')  # Missing 2 required args
""")
    res = runner.invoke(app, ["scan", str(tmp_path), "--all", "--strict"])
    assert res.exit_code == 1
