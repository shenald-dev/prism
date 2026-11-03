"""
Visual Dependency & Blast Radius Diagram Exporter.
Exports topological cascades to Mermaid.js and DOT/Graphviz formats.
"""

from typing import List, Set

from prism.core.blast import BlastRadiusReport
from prism.core.graph import CallerNode


def _sanitize_id(name: str) -> str:
    """Sanitize identifier for Mermaid / DOT node names."""
    return (
        name.replace("/", "_")
        .replace("\\", "_")
        .replace(".", "_")
        .replace(":", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


def export_mermaid(report: BlastRadiusReport) -> str:
    """Generate a Mermaid.js flowchart (graph TD) of the blast radius."""
    lines = [
        "```mermaid",
        "graph TD",
        "    %% PRISM Blast Radius Graph",
        "    classDef target fill:#9b59b6,stroke:#8e44ad,stroke-width:3px,color:#fff;",
        "    classDef direct fill:#e74c3c,stroke:#c0392b,stroke-width:2px,color:#fff;",
        "    classDef transitive fill:#3498db,stroke:#2980b9,stroke-width:1px,color:#fff;",
        "    classDef test fill:#2ecc71,stroke:#27ae60,stroke-width:1px,color:#fff;",
        "    classDef broken fill:#c0392b,stroke:#e74c3c,stroke-width:3px,stroke-dasharray: 5 5,color:#fff;",
    ]

    target_nodes: Set[str] = set()
    direct_nodes: Set[str] = set()
    transitive_nodes: Set[str] = set()
    test_nodes: Set[str] = set()
    broken_nodes: Set[str] = set()

    broken_callers = {v.caller_identifier for v in report.all_violations}

    for sb in report.symbol_blasts:
        target_id = _sanitize_id(sb.symbol.identifier)
        target_nodes.add(target_id)
        lines.append(f'    {target_id}["💎 {sb.symbol.name}"]:::target')

        def _add_nodes_and_edges(nodes: List[CallerNode], parent_id: str):
            for node in nodes:
                node_id = _sanitize_id(node.caller_symbol)
                label = node.caller_symbol.split("::")[-1]
                edge_label = f"L{node.depth}"

                if node.caller_symbol in broken_callers:
                    broken_nodes.add(node_id)
                    lines.append(f'    {node_id}["🚨 {label}\\n(Broken Contract)"]:::broken')
                elif node.is_test:
                    test_nodes.add(node_id)
                    lines.append(f'    {node_id}["🧪 {label}"]:::test')
                elif node.depth == 1:
                    direct_nodes.add(node_id)
                    lines.append(f'    {node_id}["⚡ {label}"]:::direct')
                else:
                    transitive_nodes.add(node_id)
                    lines.append(f'    {node_id}["🌊 {label}"]:::transitive')

                lines.append(f"    {node_id} -->|{edge_label}| {parent_id}")

                if node.children:
                    _add_nodes_and_edges(node.children, node_id)

        _add_nodes_and_edges(sb.blast_tree, target_id)

    lines.append("```")
    return "\n".join(lines)


def export_dot(report: BlastRadiusReport) -> str:
    """Generate a DOT / Graphviz representation of the blast radius."""
    lines = [
        "digraph PrismBlastRadius {",
        '    rankdir="RL";',
        '    node [fontname="Helvetica", shape="box", style="rounded,filled"];',
        '    edge [fontname="Helvetica", fontsize="10"];',
    ]

    broken_callers = {v.caller_identifier for v in report.all_violations}

    for sb in report.symbol_blasts:
        target_id = _sanitize_id(sb.symbol.identifier)
        lines.append(
            f'    "{target_id}" [label="💎 {sb.symbol.name}", fillcolor="#9b59b6", fontcolor="white"];'
        )

        def _walk(nodes: List[CallerNode], parent_id: str):
            for node in nodes:
                node_id = _sanitize_id(node.caller_symbol)
                label = node.caller_symbol.split("::")[-1]

                if node.caller_symbol in broken_callers:
                    color = "#c0392b"
                    lbl = f"🚨 {label}\\n(Broken)"
                elif node.is_test:
                    color = "#2ecc71"
                    lbl = f"🧪 {label}"
                elif node.depth == 1:
                    color = "#e74c3c"
                    lbl = f"⚡ {label}"
                else:
                    color = "#3498db"
                    lbl = f"🌊 {label}"

                lines.append(
                    f'    "{node_id}" [label="{lbl}", fillcolor="{color}", fontcolor="white"];'
                )
                lines.append(f'    "{node_id}" -> "{parent_id}" [label="L{node.depth}"];')

                if node.children:
                    _walk(node.children, node_id)

        _walk(sb.blast_tree, target_id)

    lines.append("}")
    return "\n".join(lines)
