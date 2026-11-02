"""
SARIF 2.1.0 (Static Analysis Results Interchange Format) exporter for GitHub Code Scanning.
Allows PRISM contract violations to render as inline annotations in GitHub Pull Requests.
"""

from typing import Any, Dict, List

from prism import __version__
from prism.core.contracts import ContractViolation


def _map_rule_id(reason: str) -> str:
    """Map contract violation reason to a distinct SARIF rule ID."""
    r = reason.lower()
    if "missing" in r and "required" in r:
        return "prism/missing-required-argument"
    elif "excess positional" in r:
        return "prism/excess-positional-argument"
    elif "unexpected keyword" in r:
        return "prism/unexpected-keyword-argument"
    elif "positional-only" in r:
        return "prism/positional-only-violation"
    elif "duplicate parameter" in r:
        return "prism/duplicate-parameter-binding"
    return "prism/contract-violation"


def export_sarif(violations: List[ContractViolation]) -> Dict[str, Any]:
    """Generate a valid SARIF 2.1.0 document from detected contract violations."""
    rules_map = {
        "prism/missing-required-argument": {
            "id": "prism/missing-required-argument",
            "name": "MissingRequiredArgument",
            "shortDescription": {"text": "Caller is missing required positional or keyword arguments."},
            "defaultConfiguration": {"level": "error"},
        },
        "prism/excess-positional-argument": {
            "id": "prism/excess-positional-argument",
            "name": "ExcessPositionalArgument",
            "shortDescription": {"text": "Caller passed more positional arguments than allowed."},
            "defaultConfiguration": {"level": "error"},
        },
        "prism/unexpected-keyword-argument": {
            "id": "prism/unexpected-keyword-argument",
            "name": "UnexpectedKeywordArgument",
            "shortDescription": {"text": "Caller passed unexpected keyword arguments not in signature."},
            "defaultConfiguration": {"level": "warning"},
        },
        "prism/positional-only-violation": {
            "id": "prism/positional-only-violation",
            "name": "PositionalOnlyViolation",
            "shortDescription": {"text": "Positional-only parameter passed as keyword argument."},
            "defaultConfiguration": {"level": "error"},
        },
        "prism/duplicate-parameter-binding": {
            "id": "prism/duplicate-parameter-binding",
            "name": "DuplicateParameterBinding",
            "shortDescription": {"text": "Argument provided both positionally and as keyword."},
            "defaultConfiguration": {"level": "error"},
        },
        "prism/contract-violation": {
            "id": "prism/contract-violation",
            "name": "ContractViolation",
            "shortDescription": {"text": "Caller violates the function or method contract signature."},
            "defaultConfiguration": {"level": "error"},
        },
    }

    results: List[Dict[str, Any]] = []

    for v in violations:
        rule_id = _map_rule_id(v.reason)
        level = "error" if v.severity == "CRITICAL" else ("warning" if v.severity == "HIGH" else "note")

        results.append(
            {
                "ruleId": rule_id,
                "level": level,
                "message": {"text": f"{v.reason} (Fix: {v.suggested_fix})"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": v.caller_file.replace("\\", "/"),
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": {
                                "startLine": max(1, v.caller_line),
                                "startColumn": 1,
                            },
                        }
                    }
                ],
            }
        )

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "PRISM",
                        "informationUri": "https://github.com/shenald-dev/prism",
                        "semanticVersion": __version__,
                        "rules": list(rules_map.values()),
                    }
                },
                "results": results,
            }
        ],
    }
