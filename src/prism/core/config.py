"""
Configuration engine for PRISM.
Loads project settings from prism.toml or pyproject.toml with environment variable overrides.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


@dataclass
class PrismConfig:
    max_depth: int = 5
    strict: bool = False
    fail_on: str = "CRITICAL"  # "CRITICAL", "ELEVATED", "MODERATE", "ANY"
    max_impact_score: int = 70
    ignore_symbols: List[str] = field(default_factory=lambda: ["__repr__", "__str__", "__init__"])
    ignore_paths: List[str] = field(default_factory=list)
    include_tests: bool = True
    default_format: str = "terminal"  # "terminal", "json", "sarif", "markdown"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrismConfig":
        config = cls()
        if "max_depth" in data:
            config.max_depth = int(data["max_depth"])
        if "strict" in data:
            config.strict = bool(data["strict"])
        if "fail_on" in data:
            config.fail_on = str(data["fail_on"]).upper()
        if "max_impact_score" in data:
            config.max_impact_score = int(data["max_impact_score"])
        if "ignore_symbols" in data and isinstance(data["ignore_symbols"], list):
            config.ignore_symbols = [str(s) for s in data["ignore_symbols"]]
        if "ignore_paths" in data and isinstance(data["ignore_paths"], list):
            config.ignore_paths = [str(p) for p in data["ignore_paths"]]
        if "include_tests" in data:
            config.include_tests = bool(data["include_tests"])
        if "default_format" in data:
            config.default_format = str(data["default_format"]).lower()
        return config


def _simple_toml_fallback(content: str) -> Dict[str, Any]:
    """Lightweight fallback parser for basic key-value toml if tomllib is unavailable."""
    result: Dict[str, Any] = {}
    in_section = False
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            in_section = section in ("prism", "tool.prism")
            continue
        if in_section and "=" in line:
            key, val = [p.strip() for p in line.split("=", 1)]
            if val.lower() == "true":
                result[key] = True
            elif val.lower() == "false":
                result[key] = False
            elif val.isdigit():
                result[key] = int(val)
            elif val.startswith('"') and val.endswith('"'):
                result[key] = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                result[key] = val[1:-1]
            elif val.startswith("[") and val.endswith("]"):
                items = [i.strip().strip("'\"") for i in val[1:-1].split(",") if i.strip()]
                result[key] = items
    return result


def load_config(root_path: Optional[Path] = None) -> PrismConfig:
    """Load PRISM configuration from prism.toml, pyproject.toml, or defaults."""
    root = root_path or Path.cwd()

    # 1. Check prism.toml
    prism_file = root / "prism.toml"
    if prism_file.is_file():
        try:
            content = prism_file.read_text(encoding="utf-8")
            if tomllib is not None:
                parsed = tomllib.loads(content)
                section = parsed.get("prism", parsed)
                return PrismConfig.from_dict(section)
            else:
                return PrismConfig.from_dict(_simple_toml_fallback(content))
        except Exception:
            pass

    # 2. Check pyproject.toml [tool.prism]
    pyproject_file = root / "pyproject.toml"
    if pyproject_file.is_file():
        try:
            content = pyproject_file.read_text(encoding="utf-8")
            if tomllib is not None:
                parsed = tomllib.loads(content)
                tool_section = parsed.get("tool", {}).get("prism", {})
                if tool_section:
                    return PrismConfig.from_dict(tool_section)
            else:
                parsed_fallback = _simple_toml_fallback(content)
                if parsed_fallback:
                    return PrismConfig.from_dict(parsed_fallback)
        except Exception:
            pass

    return PrismConfig()
