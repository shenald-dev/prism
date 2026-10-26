"""
Terminal UI components and visual topological tree rendering powered by Rich.
"""

import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        sys.stdout.flush()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from prism.core.blast import BlastRadiusReport
from prism.core.graph import CallerNode

console = Console()

LOGO = r"""[bold cyan]   ____  ____  ___ ____  __  __ [/]
[bold cyan]  |  _ \|  _ \|_ _/ ___||  \/  |[/]
[bold cyan]  | |_) | |_) || |\___ \| |\/| |[/]
[bold cyan]  |  __/|  _ < | | ___) | |  | |[/]
[bold cyan]  |_|   |_| \_\___|____/|_|  |_|[/]
  [dim]💎 Topological Blast Radius & Invariant Radar • Zero Bloat[/]"""


def print_banner():
    """Render the official PRISM header."""
    console.print()
    console.print(Panel(LOGO, border_style="cyan", padding=(0, 2)))
    console.print()


def _populate_tree_nodes(parent_tree: Tree, nodes: list[CallerNode], violations_map: dict):
    for node in nodes:
        key = f"{node.file_path}:{node.line_number}"
        has_violation = key in violations_map

        if has_violation:
            badge = "[bold white on red] ⚠️ BROKEN CONTRACT [/]"
            style = "bold red"
            label = f"{badge} [bold red]{node.caller_symbol}[/] [dim]({node.file_path}:{node.line_number})[/]\n  [red]> {violations_map[key]}[/]"
        elif node.depth == 1:
            badge = "[bold cyan][L1 Direct][/]"
            label = f"{badge} [cyan]{node.caller_symbol}[/] [dim]({node.file_path}:{node.line_number})[/]"
            style = "cyan"
        else:
            badge = f"[dim green][L{node.depth} Transitive][/]"
            label = f"{badge} [green]{node.caller_symbol}[/] [dim]({node.file_path}:{node.line_number})[/]"
            style = "dim"

        child_branch = parent_tree.add(label, style=style)
        if node.children:
            _populate_tree_nodes(child_branch, node.children, violations_map)


def render_report(report: BlastRadiusReport):
    """Render the full topological blast radius report."""
    if not report.symbol_blasts:
        console.print(
            Panel(
                f"[bold green]✨ ZERO BLAST RADIUS IMPACT[/]\n\n"
                f"[dim]Scanned {report.total_files_scanned} files in {report.duration_seconds:.2f}s.[/]\n"
                f"No uncommitted modified symbols or broken contracts found.",
                title="[bold green]STATUS: 💎 ISOLATED & PRISTINE[/]",
                border_style="green",
            )
        )
        return

    # 1. Render Blast Trees for each modified symbol
    console.print("[bold cyan]📡 Topological Ripple Shockwave:[/]\n")
    for sb in report.symbol_blasts:
        violations_map = {
            f"{v.caller_file}:{v.caller_line}": v.reason for v in sb.violations
        }

        root_label = f"[bold white]💎 MODIFIED:[/] [bold yellow]{sb.symbol.name}[/] [dim]({sb.symbol.file_path}:{sb.symbol.line_number})[/]\n  [dim cyan]> {sb.symbol.signature}[/]"
        tree = Tree(root_label, guide_style="cyan")

        if not sb.blast_tree:
            tree.add("[dim green]✔ No active callers (isolated local change)[/]")
        else:
            _populate_tree_nodes(tree, sb.blast_tree, violations_map)

        console.print(tree)
        console.print()

    # 2. Render Contract Violations Table (if any)
    if report.all_violations:
        table = Table(
            title="[bold red]🚨 Contract Violations & Signature Mismatches[/]",
            border_style="red",
            header_style="bold red",
            show_lines=True,
        )
        table.add_column("Sev", justify="center", width=10)
        table.add_column("Caller Location", style="cyan", width=28)
        table.add_column("Contract Violation Reason", style="white")
        table.add_column("Suggested Fix", style="dim green", width=30)

        for v in report.all_violations:
            sev_badge = "[bold white on red] CRITICAL [/]" if v.severity == "CRITICAL" else "[bold yellow]HIGH[/]"
            loc = f"{v.caller_file}:{v.caller_line}"
            desc = f"[bold]{v.reason}[/]"
            if v.snippet:
                desc += f"\n[dim red]> {v.snippet[:60]}[/]"
            table.add_row(sev_badge, loc, desc, v.suggested_fix)

        console.print(table)
        console.print()

    # 3. Telemetry Radar Card
    critical_label = "🚨 CRITICAL (Broken Contracts Detected)" if report.all_violations else "🚨 CRITICAL (Extensive Blast Radius)"
    risk_labels = {
        "LOW": "🟢 LOW RISK (Isolated Local Changes)",
        "MODERATE": "🟡 MODERATE (Check Affected Callers)",
        "ELEVATED": "🟠 ELEVATED (Broad Downstream Ripple)",
        "CRITICAL": critical_label,
    }

    panel_text = Text()
    panel_text.append("Blast Impact Score: ", style="bold")
    panel_text.append(f"{report.impact_score}/100 ", style=f"bold {report.color}")
    panel_text.append(f"[{report.risk_level}]\n", style=f"bold {report.color}")
    panel_text.append(f"Assessment: {risk_labels.get(report.risk_level, report.risk_level)}\n\n", style=f"bold {report.color}")
    panel_text.append(f"• Modified Symbols: {report.modified_symbols_count}    ", style="bold")
    panel_text.append(f"• Direct Callers (L1): {report.direct_callers_count}    ", style="cyan" if report.direct_callers_count else "dim")
    panel_text.append(f"• Transitive Callers: {report.transitive_callers_count}    ", style="dim")
    panel_text.append(f"• Affected Files: {len(report.all_affected_files)}\n", style="dim")
    panel_text.append(f"• Broken Contracts: {len(report.all_violations)}\n\n", style="bold red" if report.all_violations else "dim green")
    panel_text.append(f"Analyzed {report.total_files_scanned} files in {report.duration_seconds:.2f}s.", style="dim")

    console.print(
        Panel(
            panel_text,
            title="[bold cyan]📊 TOPOLOGICAL BLAST RADAR TELEMETRY[/]",
            border_style=report.color,
            padding=(1, 2),
        )
    )
    console.print()
