from pathlib import Path

from prism.core.config import PrismConfig, _simple_toml_fallback, load_config


def test_prism_config_defaults():
    cfg = PrismConfig()
    assert cfg.max_depth == 5
    assert cfg.strict is False
    assert cfg.fail_on == "CRITICAL"
    assert cfg.max_impact_score == 70
    assert "__repr__" in cfg.ignore_symbols
    assert cfg.include_tests is True
    assert cfg.default_format == "terminal"


def test_prism_config_from_dict():
    data = {
        "max_depth": 8,
        "strict": True,
        "fail_on": "elevated",
        "max_impact_score": 50,
        "ignore_symbols": ["helper"],
        "include_tests": False,
        "default_format": "sarif",
    }
    cfg = PrismConfig.from_dict(data)
    assert cfg.max_depth == 8
    assert cfg.strict is True
    assert cfg.fail_on == "ELEVATED"
    assert cfg.max_impact_score == 50
    assert cfg.ignore_symbols == ["helper"]
    assert cfg.include_tests is False
    assert cfg.default_format == "sarif"


def test_load_config_from_prism_toml(tmp_path: Path):
    toml_file = tmp_path / "prism.toml"
    toml_file.write_text(
        """[prism]
max_depth = 10
strict = true
fail_on = "ANY"
""",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.max_depth == 10
    assert cfg.strict is True
    assert cfg.fail_on == "ANY"


def test_load_config_from_pyproject_toml(tmp_path: Path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[tool.prism]
max_depth = 7
fail_on = "MODERATE"
""",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.max_depth == 7
    assert cfg.fail_on == "MODERATE"


def test_simple_toml_fallback_parser():
    content = """
    # Comment
    [prism]
    max_depth = 12
    strict = true
    format = 'sarif'
    ignore = ["foo", "bar"]
    """
    res = _simple_toml_fallback(content)
    assert res.get("max_depth") == 12
    assert res.get("strict") is True
    assert res.get("format") == "sarif"
    assert res.get("ignore") == ["foo", "bar"]
