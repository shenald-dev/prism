<div align="center">

```
  ██████╗ ██████╗ ██╗███████╗███╗   ███╗
  ██╔══██╗██╔══██╗██║██╔════╝████╗ ████║
  ██████╔╝██████╔╝██║███████╗██╔████╔██║
  ██╔═══╝ ██╔══██╗██║╚════██║██║╚██╔╝██║
  ██║     ██║  ██║██║███████║██║ ╚═╝ ██║
  ╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝╚═╝     ╚═╝
```

### 💎 Topological Blast Radius & Invariant Radar for AI-Generated Code

*Know what the AI just broke across your entire repository before you commit.*

[![GitHub Release](https://img.shields.io/github/v/release/shenald-dev/prism?color=00d4ff&style=flat-square&logo=github)](https://github.com/shenald-dev/prism/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg?style=flat-square)](LICENSE)
[![CI Passing](https://img.shields.io/badge/CI-Passing-brightgreen.svg?style=flat-square)](https://github.com/shenald-dev/prism/actions)
[![Speed](https://img.shields.io/badge/speed-%3C50ms-cyan.svg?style=flat-square)](#architecture)
[![Zero Config](https://img.shields.io/badge/config-zero-success.svg?style=flat-square)](#quick-start)

---

[The Problem](#-the-problem) •
[Key Highlights](#-key-highlights) •
[Quick Start](#-quick-start) •
[Terminal UI](#-terminal-ui) •
[CLI Commands](#-cli-commands) •
[Agent Loop Mode](#-agent--llm-loop-mode) •
[CI / CD Enforcement](#-ci--github-actions-enforcement) •
[Architecture](#-architecture)

---

</div>

## 💥 The Problem

In the era of vibe coding and autonomous AI agents (**Cursor, Claude Code, Copilot, Cline, Aider**), AI writes code at 1,000 WPM.

**However, LLMs suffer from severe tunnel vision:**
- An AI refactors `authenticate_user(user_id, token, tenant_id=None)` to require `org_id` as a second parameter.
- The AI runs its isolated unit test in `test_auth.py`, reports *"Refactoring complete!"*, and stops.
- Downstream in `billing/webhook.py`, `api/v1/sessions.py`, and `workers/sync.ts`, 12 callers are now silently broken with:
  ```text
  TypeError: authenticate_user() missing 1 required positional argument: 'org_id'
  ```

Traditional typecheckers (mypy, tsc) require strict types everywhere or take seconds to recompile your whole project. Unit tests only catch downstream breakage if you already wrote tests for every transitive caller.

**`prism` is a zero-latency topological radar.** It scans your uncommitted git diff (`git diff HEAD`) or branch diff, builds an in-memory dependency graph, traces the ripple shockwave up to N hops deep, identifies impacted tests, and runs contract invariant checks on callers—all in **<50ms**.

---

## ⚡ Key Highlights

- 🌊 **Topological Ripple Shockwave:** Computes the multi-hop transitive caller tree of every symbol touched in your git working tree.
- 🛡️ **Advanced Contract Invariant Checking:** Flags missing required arguments, excess positional parameters, unexpected keyword arguments, positional-only violations (`/`), duplicate bindings, and dataclass signatures across Python 3.8–3.12 and TypeScript/JavaScript.
- 🧪 **Intelligent Test Impact Radar:** Pinpoints exact test files and test functions that directly or transitively cover modified code, flags untested modified symbols, and runs only affected tests with one command.
- 🤖 **Agent Remediation Prompt Generator (`prism explain`):** Synthesizes high-density, zero-hallucination prompt context and exact code fixes for autonomous coding agents (Claude Code, Cursor, Copilot, Aider, Devin).
- 📊 **Multi-Format Enterprise Reporting:** Emits Rich terminal UI, machine-readable JSON, GitHub Flavored Markdown (`$GITHUB_STEP_SUMMARY`), or SARIF 2.1.0 for GitHub Code Scanning inline PR annotations.
- 🔀 **Revision & CI Diffing:** Analyze uncommitted changes, staged changes (`--staged`), commits (`--commit`), or base branches (`--base origin/main`).
- ⚡ **Sub-50ms Zero-Config Engine:** Pure AST visitor with zero heavy daemon overhead. Runs instantaneously on commit hooks.

---

## 💻 Terminal UI

When you run `prism scan` after an AI edits your code:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│     ____  ____  ___ ____  __  __                                            │
│    |  _ \|  _ \|_ _/ ___||  \/  |                                           │
│    | |_) | |_) || |\___ \| |\/| |                                           │
│    |  __/|  _ < | | ___) | |  | |                                           │
│    |_|   |_| \_\___|____/|_|  |_|                                           │
│    💎 Topological Blast Radius & Invariant Radar • Zero Bloat               │
└─────────────────────────────────────────────────────────────────────────────┘

📡 Topological Ripple Shockwave:

💎 MODIFIED: calculate_tax (tax.py:12)
  > def calculate_tax(amount, rate, jurisdiction)
├──  ⚠️ BROKEN CONTRACT  order_service.py::process_checkout (order_service.py:45)
│     > Missing 1 required argument(s): 'jurisdiction'.
│   └── [L2 Transitive] checkout_worker.py::run_job (checkout_worker.py:18)
├── [🧪 Test Caller] tests/test_orders.py::test_tax_calculation (tests/test_orders.py:22)
└──  ⚠️ BROKEN CONTRACT  api/v2/orders.py::handle_post (api/v2/orders.py:89)
      > Missing 1 required argument(s): 'jurisdiction'.

🚨 Contract Violations & Signature Mismatches (2)
┌────────────┬──────────────────────────────┬──────────────────────────────┬────────────────────────────────┐
│    Sev     │ Caller Location              │ Contract Violation Reason    │ Suggested Fix                  │
├────────────┼──────────────────────────────┼──────────────────────────────┼────────────────────────────────┤
│  CRITICAL  │ order_service.py:45          │ Missing 1 required arg...    │ Pass 'jurisdiction' parameter  │
│  CRITICAL  │ api/v2/orders.py:89          │ Missing 1 required arg...    │ Pass 'jurisdiction' parameter  │
└────────────┴──────────────────────────────┴──────────────────────────────┴────────────────────────────────┘

┌─────────────────────────── 🧪 TEST IMPACT RADAR ────────────────────────────┐
│  • Impacted Test Files: 1                                                   │
│  • Impacted Test Cases: 1                                                   │
│  • Recommended Run: pytest tests/test_orders.py                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────── 📊 TOPOLOGICAL BLAST RADAR TELEMETRY ────────────────────┐
│  Blast Impact Score: 85/100 [CRITICAL]                                      │
│  Assessment: 🚨 CRITICAL (Broken Contracts Detected)                        │
│  • Modified Symbols: 1    • Direct Callers: 2    • Transitive: 1            │
│  • Broken Contracts: 2    • Impacted Tests: 1                               │
│  Analyzed 24 files in 0.038s.                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Installation

Install directly via pip from GitHub:

```bash
pip install "git+https://github.com/shenald-dev/prism.git"
```

Or install the pre-built wheel directly from the [latest GitHub Release](https://github.com/shenald-dev/prism/releases/latest):

```bash
pip install https://github.com/shenald-dev/prism/releases/download/v1.0.0/prism_radar-1.0.0-py3-none-any.whl
```

Or run via `pipx` / `uv`:

```bash
pipx install "git+https://github.com/shenald-dev/prism.git"
# or
uv tool install "git+https://github.com/shenald-dev/prism.git"
```

---

## 🛠️ CLI Commands

### 1. `prism scan` (Core Blast & Contract Radar)

Scan your current git working tree (unstaged + staged changes):

```bash
prism scan
```

Scan against a base branch (e.g. in PRs or feature branches):

```bash
prism scan --base origin/main
```

Scan staged changes only:

```bash
prism scan --staged
```

Run in strict mode (fails with exit code `1` if broken contracts or high risk are found):

```bash
prism scan --strict
```

Export results as SARIF 2.1.0 for GitHub Code Scanning:

```bash
prism scan --format sarif -o results.sarif
```

Export results as GitHub Flavored Markdown for PR comments:

```bash
prism scan --format markdown
```

### 2. `prism test-impact` (Smart Test Selection)

Identify exactly which tests are impacted by your current changes and find coverage gaps:

```bash
prism test-impact
```

Automatically execute only the impacted tests:

```bash
prism test-impact --run
```

### 3. `prism explain` (AI Agent Self-Healing Context)

Generate high-density diagnostic context and remediation instructions ready to pipe into an AI coding agent:

```bash
prism explain
```

### 4. `prism init` (Project Configuration)

Initialize a `prism.toml` file with sensible defaults:

```bash
prism init
```

---

## 🤖 Agent / LLM Loop Mode

If you run autonomous coding loops (**Claude Code, Cursor Agent, Copilot Workspace, Aider, Devin**), use `prism` as your invariant guardrail:

```bash
# Provide structured context to agent when contracts break
prism explain | your-agent-fixer
```

Or pipe structured JSON:

```bash
prism scan --json | your-agent-fixer
```

Sample JSON output:

```json
{
  "impact_score": 85,
  "risk_level": "CRITICAL",
  "metrics": {
    "modified_symbols": 1,
    "direct_callers": 2,
    "transitive_callers": 1,
    "total_affected_files": 4,
    "contract_violations": 2
  },
  "violations": [
    {
      "callee_name": "calculate_tax",
      "caller_file": "order_service.py",
      "caller_line": 45,
      "severity": "CRITICAL",
      "reason": "Missing 1 required argument(s): 'jurisdiction'",
      "snippet": "calculate_tax(order.total, rate)",
      "suggested_fix": "Update callsite to pass all required parameters ('jurisdiction')."
    }
  ],
  "test_impact": {
    "impacted_test_files": ["tests/test_orders.py"],
    "impacted_test_cases": ["tests/test_orders.py::test_tax_calculation"],
    "recommended_command": "pytest tests/test_orders.py"
  }
}
```

---

## 🛡️ CI & GitHub Actions Enforcement

### GitHub Actions Workflow with Inline PR Annotations (SARIF)

Add `.github/workflows/prism.yml` to block PRs with broken contracts and display inline line-by-line annotations directly on your GitHub PR diff:

```yaml
name: Prism Radar

on: [pull_request]

jobs:
  blast-radius:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Prism
        run: pip install "git+https://github.com/shenald-dev/prism.git"

      - name: Run Prism SARIF Scan
        run: prism scan --base origin/${{ github.base_ref }} --format sarif -o prism.sarif
        continue-on-error: true

      - name: Upload SARIF to GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: prism.sarif

      - name: Strict Verification Gate
        run: prism scan --base origin/${{ github.base_ref }} --strict
```

### Git Pre-Commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/shenald-dev/prism
    rev: v1.0.0
    hooks:
      - id: prism
        entry: prism scan --strict
        language: python
        always_run: true
```

---

## ⚙️ Configuration (`prism.toml`)

Customize PRISM's analysis behavior with an optional `prism.toml` or `pyproject.toml`:

```toml
[prism]
max_depth = 6
strict = false
fail_on = "CRITICAL"            # "CRITICAL", "ELEVATED", "MODERATE", or "ANY"
max_impact_score = 70
ignore_symbols = ["__repr__", "__str__", "__init__"]
ignore_paths = ["legacy/*"]
include_tests = true
default_format = "terminal"     # "terminal", "json", "sarif", "markdown"
```

---

## ⚙️ Architecture

```
                       ┌──────────────────────┐
                       │  Git Diff Workspace  │
                       └──────────┬───────────┘
                                  │ (modified line spans)
                                  ▼
┌──────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  Python AST      │───▶│  Symbol Extraction  │◀───│  JS / TS Lexer   │
│  Visitor Engine  │    │  & Parameter Schema │    │  Parser Engine   │
└────────┬─────────┘    └──────────┬──────────┘    └────────┬─────────┘
         │                         │                        │
         ▼                         ▼                        ▼
┌──────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  Import Visitor  │───▶│  Topological Graph  │◀───│ Test Impact Radar│
│  Alias Resolver  │    │  Transitive Callers │    │ Coverage Gaps    │
└──────────────────┘    └──────────┬──────────┘    └──────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │  Contract Invariant │
                        │  Signature Auditor  │
                        └──────────┬──────────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
[Rich Terminal Radar]     [JSON / SARIF 2.1.0]        [Agent Remediation Context]
```

1. **Diff Intersector:** `git diff` computes precise line ranges for uncommitted, staged, commit, or branch diffs.
2. **AST Symbol Extractor:** Full lexical and AST visitors parse functions, methods, classes, and dataclasses, capturing positional-only, keyword-only, variadic, and default parameters.
3. **Import Resolver:** Resolves imported modules and aliases to eliminate cross-module name collisions.
4. **Topological Graph:** Computes the directed acyclic graph (DAG) of callers, safely detecting recursion cycles.
5. **Contract Invariant Auditor:** Verifies call sites for parameter counts, keyword alignment, positional-only violations, and duplicate bindings.
6. **Test Impact Radar:** Maps touched code to relevant test suites and exposes untested modified symbols.

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or PR on [GitHub](https://github.com/shenald-dev/prism).

```bash
git clone https://github.com/shenald-dev/prism.git
cd prism
pip install -e ".[dev]"
pytest
ruff check .
```

---

## 📜 License

MIT License. Designed and built with ❤️ by [shenald-dev](https://github.com/shenald-dev).
