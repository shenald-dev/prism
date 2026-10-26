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
from prism.core.git import discover_all_source_files, get_git_diff_lines, identify_modified_symbols
from prism.core.graph import DependencyGraph
from prism.parsers.base import ParsedFile
from prism.parsers.js_ts_parser import parse_js_ts_file
from prism.parsers.python_parser import parse_python_file
from prism.ui.console import console, print_banner, render_report

app = typer.Typer(
    help="💎 Real-time topological blast radius and contract analysis for AI-generated code. Know what will break before you commit.",
    add_completion=False,
)


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
):
    """Compute topological blast radius and check caller contracts for uncommitted changes."""
    start_time = time.time()

    if not json_output:
        print_banner()

    # 1. Discover all source files
    source_files = discover_all_source_files(path)
    if not source_files:
        if json_output:
            print(json.dumps({"error": "No supported source files (.py, .ts, .tsx, .js, .jsx) found."}))
        else:
            console.print("[bold yellow]No supported source files (.py, .ts, .tsx, .js, .jsx) found.[/]")
        raise typer.Exit(0)

    # 2. Parse all files into symbols and callsites
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
            graph.add_symbol(sym)
        for call in parsed.call_sites:
            graph.add_call_site(call)

    # 3. Identify modified symbols
    if all_symbols:
        modified_symbols = []
        for p in parsed_files.values():
            modified_symbols.extend(p.symbols)
    else:
        diff_lines = get_git_diff_lines(path)
        modified_symbols = identify_modified_symbols(diff_lines, parsed_files)
        # If no uncommitted changes found, fallback to informing user or full repo
        if not modified_symbols and not json_output:
            console.print("[dim]No uncommitted git changes detected. Analyzing all repository symbols...[/]\n")
            for p in parsed_files.values():
                modified_symbols.extend(p.symbols)

    duration = time.time() - start_time

    # 4. Compute Blast Radius
    report = compute_blast_radius(
        modified_symbols=modified_symbols,
        graph=graph,
        total_files_scanned=len(source_files),
        duration_seconds=duration,
        max_depth=depth,
    )

    # 5. Render Output
    if json_output:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        render_report(report)

    # 6. Strict Mode Exit Code
    if strict and (report.risk_level == "CRITICAL" or len(report.all_violations) > 0):
        if not json_output:
            console.print(f"\n[bold red]❌ STRICT CHECK FAILED: {len(report.all_violations)} broken contract(s) detected.[/]\n")
        raise typer.Exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
