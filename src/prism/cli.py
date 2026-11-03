"""
CLI entrypoint for PRISM - The Topological Blast Radius & Invariant Radar.
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional

import typer

from prism import __version__
from prism.core.blast import compute_blast_radius
from prism.core.config import load_config
from prism.core.git import discover_all_source_files, get_git_diff_lines, identify_modified_symbols
from prism.core.graph import DependencyGraph
from prism.core.hook import init_github_actions_workflow, install_git_pre_commit_hook
from prism.core.patch import PatchGenerator
from prism.core.remediation import generate_agent_remediation_prompt
from prism.core.tests import run_impacted_tests
from prism.core.visual import export_dot, export_mermaid
from prism.core.watch import LiveRadarWatcher
from prism.parsers.base import ParsedFile
from prism.parsers.js_ts_parser import parse_js_ts_file
from prism.parsers.python_parser import parse_python_file
from prism.ui.console import console, print_banner, render_report

app = typer.Typer(
    help="💎 Real-time topological blast radius and contract analysis for AI-generated code. Know what will break before you commit.",
    add_completion=False,
)

hook_app = typer.Typer(
    name="hook",
    help="🪝 Manage Git pre-commit hooks for PRISM.",
    no_args_is_help=True,
)
app.add_typer(hook_app, name="hook")

ci_app = typer.Typer(
    name="ci",
    help="🤖 Manage CI/CD automation workflows (GitHub Actions, SARIF).",
    no_args_is_help=True,
)
app.add_typer(ci_app, name="ci")


def version_callback(value: bool):
    if value:
        console.print(f"[bold cyan]prism[/] version [bold green]{__version__}[/]")
        raise typer.Exit()


@app.callback()
def common(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show version and exit.", callback=version_callback, is_eager=True
    ),
):
    pass


def _collect_and_parse(
    path: Path, include_tests: bool = True
) -> tuple[Dict[str, ParsedFile], DependencyGraph, list[Path]]:
    """Helper to discover and parse all supported files into parsed_files and graph."""
    source_files = discover_all_source_files(path, include_tests=include_tests)
    parsed_files: Dict[str, ParsedFile] = {}
    graph = DependencyGraph()

    for file_path in source_files:
        rel_path = str(file_path.relative_to(path)).replace("\\", "/")
        try:
            code = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        ext = file_path.suffix.lower()
        if ext == ".py":
            parsed = parse_python_file(rel_path, code)
        elif ext in {".js", ".jsx", ".ts", ".tsx"}:
            parsed = parse_js_ts_file(rel_path, code)
        else:
            continue

        parsed_files[rel_path] = parsed
        for sym in parsed.symbols:
            graph.register_symbol(sym)
        for call in parsed.call_sites:
            graph.add_call_site(call)

    return parsed_files, graph, source_files


@app.command(name="scan")
def scan(
    path: Path = typer.Argument(
        Path("."),
        help="Target repository or directory to analyze.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    all_symbols: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Analyze all symbols across the repository instead of only uncommitted / modified git changes.",
    ),
    base: Optional[str] = typer.Option(
        None,
        "--base",
        help="Git base revision or branch to diff against (e.g. 'main', 'origin/main', or 'HEAD~1').",
    ),
    head: Optional[str] = typer.Option(
        None,
        "--head",
        help="Git head revision when diffing a range against --base.",
    ),
    staged: bool = typer.Option(
        False,
        "--staged",
        help="Only inspect staged git changes.",
    ),
    commit: Optional[str] = typer.Option(
        None,
        "--commit",
        help="Inspect changes introduced by a specific git commit hash.",
    ),
    depth: int = typer.Option(
        5,
        "--depth",
        "-d",
        help="Maximum depth for transitive caller graph traversal.",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        "-s",
        help="Fail with exit code 1 if any broken contracts or critical blast risks are detected (ideal for CI / pre-commit).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output raw JSON results for CI/CD integrations or agent feedback loops.",
    ),
    output_format: str = typer.Option(
        "terminal",
        "--format",
        "-f",
        help="Output format: 'terminal', 'json', 'sarif', 'markdown', 'mermaid', or 'dot'.",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional destination file path to save output.",
    ),
    include_tests: bool = typer.Option(
        True,
        "--tests/--no-tests",
        help="Include test impact analysis in scan.",
    ),
    run_tests: bool = typer.Option(
        False,
        "--run-tests",
        help="Automatically execute the impacted tests via their runner.",
    ),
):
    """Compute topological blast radius, trace caller shockwaves, and check contract invariants."""
    start_time = time.time()
    config = load_config(path)

    # Determine effective format
    effective_format = "json" if json_output else output_format.lower()
    if effective_format == "terminal" and config.default_format != "terminal" and not json_output:
        effective_format = config.default_format

    if effective_format == "terminal":
        print_banner()

    # 1. Discover and parse all source files
    parsed_files, graph, source_files = _collect_and_parse(path, include_tests=include_tests)
    if not source_files:
        msg = "No supported source files (.py, .ts, .tsx, .js, .jsx) found."
        if effective_format == "json":
            print(json.dumps({"error": msg}))
        elif effective_format == "terminal":
            console.print(f"[bold yellow]{msg}[/]")
        raise typer.Exit(0)

    # 2. Identify modified symbols
    if all_symbols:
        modified_symbols = []
        for p in parsed_files.values():
            modified_symbols.extend(p.symbols)
    else:
        diff_lines = get_git_diff_lines(path, base=base, head=head, staged=staged, commit=commit)
        modified_symbols = identify_modified_symbols(diff_lines, parsed_files)
        # If no uncommitted changes found, fallback to informing user or full repo
        if not modified_symbols:
            if effective_format == "terminal":
                console.print("[dim]No git changes detected for target. Analyzing all repository symbols...[/]\n")
            for p in parsed_files.values():
                modified_symbols.extend(p.symbols)

    duration = time.time() - start_time

    # 3. Compute Blast Radius
    report = compute_blast_radius(
        modified_symbols=modified_symbols,
        graph=graph,
        total_files_scanned=len(source_files),
        duration_seconds=duration,
        max_depth=depth,
        include_tests=include_tests,
        config=config,
    )

    # 4. Optional: Run Impacted Tests
    if run_tests and report.test_impact:
        if effective_format == "terminal":
            console.print("[bold cyan]🧪 Executing impacted test suite...[/]")
        report.test_impact = run_impacted_tests(report.test_impact, path)

    # 5. Render Output
    output_content = ""
    if effective_format == "json":
        output_content = json.dumps(report.to_dict(), indent=2)
        if not output_file:
            print(output_content)
    elif effective_format == "sarif":
        sarif_doc = report.to_sarif()
        output_content = json.dumps(sarif_doc, indent=2)
        if not output_file:
            print(output_content)
    elif effective_format == "markdown":
        output_content = report.to_markdown()
        if not output_file:
            print(output_content)
    elif effective_format == "mermaid":
        output_content = report.to_mermaid()
        if not output_file:
            print(output_content)
    elif effective_format == "dot":
        output_content = report.to_dot()
        if not output_file:
            print(output_content)
    else:
        render_report(report)

    if output_file:
        output_file.write_text(output_content, encoding="utf-8")
        if effective_format == "terminal":
            console.print(f"[bold green]✔ Saved report to {output_file}[/]")

    # 6. Strict Mode Exit Code
    is_strict = strict or config.strict
    fail_on = config.fail_on

    should_fail = False
    if is_strict:
        if fail_on == "ANY" and (report.impact_score > 0 or report.all_violations):
            should_fail = True
        elif fail_on == "MODERATE" and (report.risk_level in ("MODERATE", "ELEVATED", "CRITICAL") or report.all_violations):
            should_fail = True
        elif fail_on == "ELEVATED" and (report.risk_level in ("ELEVATED", "CRITICAL") or report.all_violations):
            should_fail = True
        else:  # CRITICAL
            should_fail = report.risk_level == "CRITICAL" or len(report.all_violations) > 0

    if should_fail:
        if effective_format == "terminal":
            console.print(
                f"\n[bold red]❌ STRICT CHECK FAILED: {len(report.all_violations)} broken contract(s) detected "
                f"or risk level is {report.risk_level}.[/]\n"
            )
        raise typer.Exit(1)


@app.command(name="visual")
@app.command(name="graph")
def visual_command(
    path: Path = typer.Argument(
        Path("."),
        help="Target repository or directory to visualize.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    format_type: str = typer.Option("mermaid", "--format", "-f", help="Diagram format: 'mermaid' or 'dot'."),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Destination file to save diagram."),
):
    """Generate visual DAG diagrams of the blast radius in Mermaid.js or Graphviz DOT."""
    parsed_files, graph, source_files = _collect_and_parse(path, include_tests=True)
    diff_lines = get_git_diff_lines(path)
    modified = identify_modified_symbols(diff_lines, parsed_files)
    if not modified:
        for p in parsed_files.values():
            modified.extend(p.symbols)

    report = compute_blast_radius(
        modified_symbols=modified,
        graph=graph,
        total_files_scanned=len(source_files),
        duration_seconds=0.0,
        include_tests=True,
    )

    if format_type.lower() == "dot":
        diagram = export_dot(report)
    else:
        diagram = export_mermaid(report)

    if output_file:
        output_file.write_text(diagram, encoding="utf-8")
        console.print(f"[bold green]✔ Saved {format_type.upper()} diagram to {output_file}[/]")
    else:
        print(diagram)


@app.command(name="fix")
def fix_command(
    path: Path = typer.Argument(
        Path("."),
        help="Target repository or directory to remediate.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    apply_fixes: bool = typer.Option(False, "--apply", help="Apply remediations directly to caller files."),
    patch_file: Optional[Path] = typer.Option(None, "--patch", help="Save unified diff patch to file."),
):
    """Auto-generate or apply callsite fixes for contract violations (unawaited coroutines, etc.)."""
    parsed_files, graph, source_files = _collect_and_parse(path, include_tests=True)
    diff_lines = get_git_diff_lines(path)
    modified = identify_modified_symbols(diff_lines, parsed_files)
    if not modified:
        for p in parsed_files.values():
            modified.extend(p.symbols)

    report = compute_blast_radius(
        modified_symbols=modified,
        graph=graph,
        total_files_scanned=len(source_files),
        duration_seconds=0.0,
        include_tests=True,
    )

    if not report.all_violations:
        console.print("[bold green]✨ No broken contracts found. Codebase is clean.[/]")
        return

    patch_str = PatchGenerator.generate_patch(report.all_violations, path)

    if patch_file:
        patch_file.write_text(patch_str, encoding="utf-8")
        console.print(f"[bold green]✔ Saved unified patch to {patch_file}[/]")
    elif not apply_fixes:
        if patch_str:
            console.print("[bold cyan]📋 Proposed Call-site Remediation Patch:[/]\n")
            console.print(patch_str)
            console.print("\n[dim]Run 'prism fix --apply' to automatically modify caller files.[/]\n")
        else:
            console.print("[yellow]No automated patches available for current violations. Run 'prism explain'.[/]")

    if apply_fixes:
        count = PatchGenerator.apply_fixes(report.all_violations, path)
        if count > 0:
            console.print(f"[bold green]✔ Successfully applied fixes to {count} callsite(s)![/]")
        else:
            console.print("[yellow]No automated fixes could be safely applied.[/]")


@app.command(name="watch")
def watch_command(
    path: Path = typer.Argument(
        Path("."),
        help="Target repository to monitor in real-time.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    interval: float = typer.Option(0.5, "--interval", "-i", help="Polling interval in seconds."),
):
    """Live continuous radar watcher daemon for real-time AI vibe-coding feedback."""
    print_banner()
    console.print(f"[bold cyan]👀 PRISM Live Radar active on {path.resolve()}[/] [dim](Ctrl+C to exit)[/]\n")

    def _on_change():
        console.clear()
        print_banner()
        console.print("[bold yellow]⚡ Change detected! Recomputing blast radius...[/]\n")
        scan(path=path)

    watcher = LiveRadarWatcher(path, poll_interval=interval)
    try:
        watcher.watch(_on_change)
    except KeyboardInterrupt:
        console.print("\n[bold cyan]PRISM Live Radar stopped.[/]")


# --- Hook and CI commands ---


@hook_app.command(name="install")
def hook_install(
    path: Path = typer.Argument(Path("."), help="Target git repository path."),
):
    """Install native pre-commit hook preventing commits with broken contracts."""
    hook_path = install_git_pre_commit_hook(path)
    console.print(f"[bold green]✔ Installed PRISM pre-commit hook at {hook_path}[/]")


@ci_app.command(name="init")
def ci_init(
    path: Path = typer.Argument(Path("."), help="Target repository path."),
):
    """Initialize GitHub Actions PRISM blast radius CI workflow."""
    wf_path = init_github_actions_workflow(path)
    console.print(f"[bold green]✔ Generated GitHub Actions workflow at {wf_path}[/]")


@app.command(name="test-impact")
def test_impact_command(
    path: Path = typer.Argument(
        Path("."),
        help="Target repository or directory to analyze.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    run: bool = typer.Option(
        False,
        "--run",
        "-r",
        help="Execute the impacted tests immediately.",
    ),
):
    """Pinpoint impacted tests for modified symbols and detect coverage gaps."""
    parsed_files, graph, source_files = _collect_and_parse(path, include_tests=True)
    diff_lines = get_git_diff_lines(path)
    modified = identify_modified_symbols(diff_lines, parsed_files)
    if not modified:
        for p in parsed_files.values():
            modified.extend(p.symbols)

    report = compute_blast_radius(
        modified_symbols=modified,
        graph=graph,
        total_files_scanned=len(source_files),
        duration_seconds=0.0,
        include_tests=True,
    )

    if not report.test_impact or not report.test_impact.impacted_test_cases:
        console.print("[bold green]✔ No active test callers found for modified symbols.[/]")
        return

    console.print(f"[bold cyan]🧪 IMPACTED TEST SUITE ({len(report.test_impact.impacted_test_cases)} tests):[/]\n")
    for tc in report.test_impact.impacted_test_cases:
        console.print(f"  • [purple]{tc}[/]")

    if report.test_impact.recommended_command:
        console.print(f"\n[bold green]Command to execute:[/] [white]{report.test_impact.recommended_command}[/]\n")

    if run:
        console.print("[bold yellow]Running impacted tests...[/]\n")
        updated = run_impacted_tests(report.test_impact, path)
        status_color = "bold green" if updated.execution_success else "bold red"
        console.print(f"[{status_color}]Result: {updated.execution_result}[/]")
        if not updated.execution_success:
            raise typer.Exit(1)


@app.command(name="explain")
def explain(
    path: Path = typer.Argument(
        Path("."),
        help="Target repository or directory to analyze.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
):
    """Generate high-density AI Agent remediation prompt context for self-healing callers."""
    parsed_files, graph, source_files = _collect_and_parse(path, include_tests=True)
    diff_lines = get_git_diff_lines(path)
    modified = identify_modified_symbols(diff_lines, parsed_files)
    if not modified:
        for p in parsed_files.values():
            modified.extend(p.symbols)

    report = compute_blast_radius(
        modified_symbols=modified,
        graph=graph,
        total_files_scanned=len(source_files),
        duration_seconds=0.0,
        include_tests=True,
    )

    prompt = generate_agent_remediation_prompt(
        modified_symbols=modified,
        violations=report.all_violations,
        risk_level=report.risk_level,
        impact_score=report.impact_score,
    )
    print(prompt)


@app.command(name="init")
def init(
    path: Path = typer.Argument(
        Path("."),
        help="Target directory to create prism.toml config.",
    ),
):
    """Initialize a starter prism.toml configuration in the target directory."""
    target_file = path / "prism.toml"
    if target_file.exists():
        console.print(f"[bold yellow]Config file {target_file} already exists.[/]")
        raise typer.Exit(0)

    starter_config = """# PRISM Configuration File (v2.0)
# Documentation: https://github.com/shenald-dev/prism

[prism]
max_depth = 5
strict = false
fail_on = "CRITICAL"
max_impact_score = 70
ignore_symbols = ["__repr__", "__str__", "__init__"]
include_tests = true
default_format = "terminal"
"""
    target_file.write_text(starter_config, encoding="utf-8")
    console.print(f"[bold green]✔ Initialized starter configuration at {target_file}[/]")
    console.print("\n[dim]Add PRISM to your .pre-commit-config.yaml or CI workflow for zero-latency invariant radar.[/]")


def main():
    app()


if __name__ == "__main__":
    main()
