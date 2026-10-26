# Changelog

All notable changes to **prism** (`prism-radar`) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-26

### Added
- **Initial Open Source Launch**: Real-time topological blast radius and contract analysis engine for AI-generated code.
- **Git Working Tree Scanner**: Sub-millisecond extraction of staged and unstaged diff line ranges.
- **Python AST Visitor**: Full structural analysis of functions, async functions, classes, methods, parameters (positional, keyword-only, variadic, defaults), and call sites.
- **JavaScript / TypeScript Parser**: Lexical parser for function declarations, arrow functions, and call sites.
- **Topological Dependency Graph**: Multi-hop transitive caller traversal engine with built-in recursion cycle safety.
- **Contract Invariant Engine**: High-fidelity detection of missing required arguments, excess positional parameters, and unexpected keyword arguments.
- **Topological Threat Scoring**: 0–100 impact score and risk classification (`LOW`, `MODERATE`, `ELEVATED`, `CRITICAL`).
- **Rich Terminal UI**: Cyberpunk-inspired terminal radar with shockwave tree hierarchy and contract violation tables.
- **Typer CLI**: Support for `--all`, `--depth`, `--strict`, `--json`, and `--version` flags.
- **Continuous Integration**: GitHub Actions CI test matrix across Python 3.10, 3.11, and 3.12.
- **Zero-Dependency Core**: Lightweight installation with sub-50ms execution overhead.
