import json

from typer.testing import CliRunner

from prism.cli import app

runner = CliRunner()


def test_cli_scan_sarif_format(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def run(a, b):\n    return a + b\n\ndef main():\n    run(1)\n")

    res = runner.invoke(app, ["scan", str(tmp_path), "--all", "--format", "sarif"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["version"] == "2.1.0"
    assert len(data["runs"][0]["results"]) == 1
    assert data["runs"][0]["results"][0]["ruleId"] == "prism/missing-required-argument"


def test_cli_scan_markdown_format(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def run(a, b):\n    return a + b\n\ndef main():\n    run(1)\n")

    res = runner.invoke(app, ["scan", str(tmp_path), "--all", "--format", "markdown"])
    assert res.exit_code == 0
    assert "## 🚨 PRISM: Topological Blast Radius Report" in res.stdout
    assert "Contract Invariant Violations" in res.stdout


def test_cli_scan_output_file(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def hello():\n    return 'hi'\n")
    out_file = tmp_path / "report.json"

    res = runner.invoke(app, ["scan", str(tmp_path), "--all", "--format", "json", "-o", str(out_file)])
    assert res.exit_code == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert "impact_score" in data


def test_cli_test_impact_command(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def add(x, y):\n    return x + y\n")
    t = tmp_path / "test_app.py"
    t.write_text("from app import add\ndef test_add():\n    assert add(1, 2) == 3\n")

    res = runner.invoke(app, ["test-impact", str(tmp_path)])
    assert res.exit_code == 0
    assert "IMPACTED TEST SUITE" in res.stdout or "No active test callers" in res.stdout


def test_cli_explain_command(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("def calc(a, b):\n    pass\ndef caller():\n    calc(1)\n")

    res = runner.invoke(app, ["explain", str(tmp_path)])
    assert res.exit_code == 0
    assert "PRISM INVARIANT RADAR" in res.stdout
    assert "Missing 1 required argument" in res.stdout


def test_cli_init_command(tmp_path):
    res = runner.invoke(app, ["init", str(tmp_path)])
    assert res.exit_code == 0
    config_file = tmp_path / "prism.toml"
    assert config_file.exists()
    assert "[prism]" in config_file.read_text()

    # Second run should report already exists
    res2 = runner.invoke(app, ["init", str(tmp_path)])
    assert res2.exit_code == 0
    assert "already exists" in res2.stdout
