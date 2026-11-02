# Changelog

All notable changes to **prism** (`prism-radar`) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-02

### Added
- **Python 3.8–3.12 Contract Invariant Engine**:
  - Full structural AST support for positional-only parameters (`/`) and keyword-only parameters (`*`).
  - Detection of positional-only arguments improperly passed as keyword arguments.
  - Detection of duplicate parameter bindings (receiving both positional and keyword values).
  - Accurate constructor signature extraction for standard Python classes and `@dataclass` definitions.
- **Import-Aware Scoped Dependency Graph**:
  - Full AST `Import` and `ImportFrom` visitor with alias tracking and relative import resolution.
  - ES6 module import parsing for TypeScript/JavaScript (`import { foo } from './bar'`).
  - Qualified call-site callee resolution preventing cross-module name collisions.
- **Intelligent Test Impact Radar (`prism test-impact`)**:
  - Traces modified symbols directly and transitively to impacted test suites and test cases.
  - Automatically identifies test coverage gaps (modified symbols with 0 automated tests).
  - Recommends the exact test execution command and offers instantaneous test execution (`--run-tests` / `prism test-impact --run`).
- **Autonomous Agent Remediation Generator (`prism explain` / `prism prompt`)**:
  - High-density, zero-hallucination prompt generator tailored for AI coding agents (Claude Code, Cursor, Copilot, Cline, Aider, Devin).
  - Outputs exact file paths, line numbers, caller source snippets, diagnoses, and actionable code fixes.
- **Enterprise Multi-Format Reporting**:
  - Full SARIF 2.1.0 exporter (`--format sarif`) for direct integration with GitHub Code Scanning inline PR annotations.
  - GitHub Flavored Markdown summary generator (`--format markdown`) for `$GITHUB_STEP_SUMMARY` and PR comment automation.
  - Structured file export option (`--output / -o`).
- **Advanced Git Revision & CI Diffing**:
  - Support for `--base`, `--head`, `--staged`, and `--commit <sha>` diff targets.
  - Auto-detection of GitHub Actions PR base branches (`GITHUB_BASE_REF`) for clean checkouts in CI workflows.
- **Project Configuration & Policy Engine (`prism.toml`)**:
  - Added `prism init` command to bootstrap starter configuration.
  - Reads configuration from `prism.toml` or `pyproject.toml` (`[tool.prism]`).
  - Configurable depth, failure thresholds (`fail_on = "CRITICAL" | "ELEVATED" | "MODERATE" | "ANY"`), ignored symbols, and ignored paths.
- **Comprehensive Test Suite**:
  - 32 new unit and integration tests covering CLI v1, SARIF generation, remediation prompts, test impact, advanced git diffs, and complex contract invariants (53 tests total, 88% overall test coverage).

### Changed
- Promoted package version to `1.0.0` with `Production/Stable` classification.
- Upgraded terminal UI telemetry card to display test impact metrics and test caller branch badges.
- Default file discovery now includes test directories for comprehensive shockwave impact tracing.

### Fixed
- Fixed scoring logic in `compute_blast_radius` where transitive and direct callers were improperly calculated.
- Fixed regex parsing for multi-line JavaScript/TypeScript function declarations and callsites.
- Fixed argument counting for callsites containing nested object/array literals.

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
