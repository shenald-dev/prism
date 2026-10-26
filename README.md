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

[![PyPI Version](https://img.shields.io/pypi/v/prism-radar.svg?color=blue&style=flat-square)](https://pypi.org/project/prism-radar/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg?style=flat-square)](LICENSE)
[![CI Passing](https://img.shields.io/badge/CI-Passing-brightgreen.svg?style=flat-square)](https://github.com/shenald-dev/prism/actions)
[![Speed](https://img.shields.io/badge/speed-%3C50ms-cyan.svg?style=flat-square)](#architecture)
[![Zero Config](https://img.shields.io/badge/config-zero-success.svg?style=flat-square)](#quick-start)

---

[The Problem](#-the-problem) •
[How It Works](#-how-it-works) •
[Quick Start](#-quick-start) •
[Terminal UI](#-terminal-ui) •
[CI / CD Enforcement](#-ci--pre-commit-enforcement) •
[Agent Integration](#-agent--llm-loop-mode) •
[Architecture](#-architecture)

---

</div>

## 💥 The Problem

In the era of vibe coding and autonomous AI agents (**Cursor, Claude Code, Copilot, Cline, Aider, Jules**), AI writes code at 1,000 WPM.

**However, LLMs suffer from severe tunnel vision:**
- An AI refactors `authenticate_user(user_id, token, tenant_id=None)` to require `org_id` as a second parameter.
- The AI runs its isolated unit test in `test_auth.py`, reports *"Refactoring complete!"*, and stops.
- Downstream in `billing/webhook.py`, `api/v1/sessions.py`, and `workers/sync.ts`, 12 callers are now silently broken with:
  ```text
  TypeError: authenticate_user() missing 1 required positional argument: 'org_id'
  ```

Traditional typecheckers (mypy, tsc) require strict types everywhere or take seconds to recompile your whole project. Unit tests only catch downstream breakage if you already wrote tests for every transitive caller.

**`prism` is a zero-latency topological radar.** It scans your uncommitted git diff (`git diff HEAD`), builds an in-memory dependency graph, traces the ripple shockwave up to N hops deep, and runs contract invariant checks on callers—all in **<50ms**.

---

## ⚡ Key Highlights

- 🌊 **Topological Ripple Shockwave:** Computes the multi-hop transitive caller tree of every symbol touched in your git working tree.
- 🛡️ **Contract Invariant Checking:** Flags missing required arguments, excess positional parameters, and unexpected keyword arguments across Python & TypeScript/JavaScript.
- 🚦 **Topological Threat Score (0–100):** Categorizes risk into `LOW`, `MODERATE`, `ELEVATED`, or `CRITICAL` based on graph depth, blast radius width, and contract violations.
- ⚡ **Sub-50ms Zero-Config Engine:** Pure AST visitor with zero heavy daemon overhead. Runs instantaneously on commit hooks.
- 🤖 **Machine-Readable JSON Mode:** Designed for AI coding loops. Pipe structured JSON diagnostics back to your AI agent so it can self-heal callers before you ever review the code.

---

## 💻 Terminal UI

When you run `prism scan` after an AI edits your code:

```text
💎 PRISM: TOPOLOGICAL BLAST RADIUS REPORT
Scan target: . | Engine: AST Invariant Graph | Latency: 0.034s

─── TOPOLOGICAL IMPACT ────────────────────────────────────────────────────────
Impact Score: 85/100  [CRITICAL RISK - CONTRACTS BROKEN]
Modified Symbols: 1   Affected Downstream Callers: 3   Max Depth: 2

─── TOPOLOGICAL RIPPLE SHOCKWAVE ──────────────────────────────────────────────
📦 calculate_tax (tax.py:12)
├── ⚠️ order_service.py:45 -> process_checkout (depth 1)
│   └── ⚠️ checkout_worker.py:18 -> run_job (depth 2)
└── ⚠️ api/v2/orders.py:89 -> handle_post (depth 1)

─── CONTRACT VIOLATIONS (3) ───────────────────────────────────────────────────
FILE                 LINE   CALLER            DIAGNOSIS
───────────────────  ─────  ────────────────  ──────────────────────────────────
order_service.py     45     process_checkout  Missing required parameter: 'jurisdiction'
checkout_worker.py   18     run_job           Unexpected keyword argument: 'tax_exempt'
api/v2/orders.py     89     handle_post       Missing required parameter: 'jurisdiction'

💥 Result: 3 callers will crash at runtime. Fix callers before committing.
```

---

## 🚀 Quick Start

### Installation

Install via pip:

```bash
pip install prism-radar
```

Or install with `uv` / `pipx`:

```bash
uv tool install prism-radar
# or
pipx install prism-radar
```

### Usage

#### 1. Scan Uncommitted Changes (Default)
Inspect what your current git working tree (unstaged + staged changes) impacts:

```bash
prism scan
```

#### 2. Scan Entire Codebase
Analyze all symbols across the entire repository:

```bash
prism scan --all
```

#### 3. Strict Mode for Pre-Commit & CI
Exit with non-zero code (`1`) if any contract violation or high risk is detected:

```bash
prism scan --strict
```

#### 4. JSON Output for AI Pipelines
Generate clean JSON diagnostics for autonomous agents:

```bash
prism scan --json
```

---

## 🛡️ CI & Pre-Commit Enforcement

### Git Pre-Commit Hook

Never let an AI commit broken downstream contracts. Add `prism` to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/shenald-dev/prism
    rev: v0.1.0
    hooks:
      - id: prism
        entry: prism scan --strict
        language: python
        always_run: true
```

Or as a raw Git hook in `.git/hooks/pre-commit`:

```bash
#!/bin/sh
prism scan --strict
```

### GitHub Actions Workflow

Add this to `.github/workflows/prism.yml` to block pull requests with broken contracts:

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
        run: pip install prism-radar

      - name: Verify Blast Radius & Invariants
        run: prism scan --strict
```

---

## 🤖 Agent / LLM Loop Mode

If you run autonomous coding loops (e.g. Claude Code, Aider, Devin, OpenDevin, Cursor Agent), use `prism` as the ground-truth verifier:

```bash
prism scan --json | your-agent-fixer
```

Sample JSON response:

```json
{
  "impact_score": 85,
  "risk_level": "CRITICAL",
  "total_modified_symbols": 1,
  "total_affected_callers": 3,
  "max_depth": 2,
  "violations": [
    {
      "caller_file": "order_service.py",
      "caller_line": 45,
      "caller_name": "process_checkout",
      "target_name": "calculate_tax",
      "kind": "missing_required_arg",
      "message": "Missing required argument 'jurisdiction'"
    }
  ]
}
```

---

## ⚙️ Architecture

```
                       ┌──────────────────────┐
                       │  Git Diff Workspace  │
                       └──────────┬───────────┘
                                  │ (modified line ranges)
                                  ▼
┌──────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  Python AST      │───▶│  Symbol Extraction  │◀───│  JS / TS Lexer   │
│  Visitor Engine  │    │  & Parameter Schema │    │  Parser Engine   │
└──────────────────┘    └──────────┬──────────┘    └──────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │  Topological Graph  │
                        │  Transitive Callers │
                        └──────────┬──────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │  Contract Invariant │
                        │  Signature Auditor  │
                        └──────────┬──────────┘
                                   │
                 ┌─────────────────┴─────────────────┐
                 ▼                                   ▼
        [Rich Terminal Radar]              [JSON Machine Report]
```

1. **Diff Intersector:** `git diff` calculates precise changed line spans.
2. **AST Symbol Extractor:** Parses symbols and records their parameters (positional, keyword-only, variadic `*args`, `**kwargs`, defaults).
3. **Graph Traversal:** Computes the directed acyclic graph (DAG) of callers, safely detecting and pruning recursion cycles.
4. **Contract Validator:** Evaluates call sites against target signatures for argument count and keyword alignment.

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
