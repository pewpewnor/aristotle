from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from .parser.relationship import Relationship


def print_relationships_summary(relationships: List[Relationship]):
    """relationships: list of Relationship objects"""
    print("=" * 100)
    print("SUMMARY VIEW")
    print("=" * 100)
    print("Knowledge Graph Relationships Summary:\n" + "=" * 80)
    relations = {}
    for rel in relationships:
        relations.setdefault(rel.relationship, []).append(
            (rel.source, rel.target, rel.attributes)
        )

    for relation, items in relations.items():
        print(f"\n{relation} relationships ({len(items)}):")
        print("-" * 40)
        for source, target, attrs in items:
            print(f"  {source} --[{relation}]--> {target} | {attrs}")


def print_relationships_summary_compact(relationships: List[Relationship]):
    print("=" * 100)
    print("SUMMARY VIEW")
    print("=" * 100)
    print("Knowledge Graph Triplets Summary:\n" + "=" * 80)
    relations = {}
    for rel in relationships:
        relations.setdefault(rel.relationship, []).append(rel)

    for relation, items in relations.items():
        print(f"\n{relation} relationships ({len(items)}):")
        print("-" * 40)
        for rel in items:
            print(f"  {rel}")


def print_relationships_all(relationships: List[Relationship]):
    print("=" * 100)
    print("DETAILED VIEW")
    print("=" * 100)
    print("Complete Knowledge Graph Relationships Details:\n" + "=" * 100)

    for i, rel in enumerate(relationships, 1):
        source, relation, target, attrs = (
            rel.source,
            rel.relationship,
            rel.target,
            rel.attributes,
        )
        print(f"\n[{i:3d}] {source} --[{relation}]--> {target}")

        print("      Additional Attributes:")
        if attrs:
            for key, value in sorted(attrs.items()):
                if isinstance(value, str):
                    display_value = value if len(value) <= 60 else f"{value[:57]}..."
                    print(f"        {key}: '{display_value}'")
                elif isinstance(value, (list, tuple)):
                    print(
                        f"        {key}: {type(value).__name__} with {len(value)} items"
                    )
                elif isinstance(value, dict):
                    print(f"        {key}: Dict with {len(value)} keys")
                else:
                    print(f"        {key}: {value}")

        if i < len(relationships):
            print("      " + "-" * 80)

    print(f"\nTotal relationships displayed: {len(relationships)}")


def plot_knowledge_graph_from_relationships(
    relationships: List[Relationship],
    title: str = "Python Code Knowledge Graph",
    figsize: Tuple[int, int] = (15, 10),
    save_path: Optional[str] = None,
):
    graph = nx.DiGraph()

    node_colors = {
        "MODULE": "#FF6B6B",  # Red
        "CLASS": "#4ECDC4",  # Teal
        "FUNCTION": "#45B7D1",  # Blue
        "METHOD": "#96CEB4",  # Green
        "FIELD": "#FFEAA7",  # Yellow
        "GLOBAL_VARIABLE": "#DDA0DD",  # Plum
    }

    edge_colors = {
        "CONTAINS": "#2D3436",
        "HAS_METHOD": "#00B894",
        "HAS_FIELD": "#FDCB6E",
        "INHERITS": "#E17055",
        "HAS_PARAMETER": "#6C5CE7",
        "MODULE_NODE": "#74B9FF",
    }

    node_types = {}
    edge_labels = {}

    for rel in relationships:
        source, relation, target, attrs = (
            rel.source,
            rel.relationship,
            rel.target,
            rel.attributes,
        )
        source_type = attrs.get("source_kind", "UNKNOWN")
        target_type = attrs.get("target_kind", "UNKNOWN")

        graph.add_node(source)
        graph.add_node(target)

        node_types[source] = source_type
        node_types[target] = target_type

        graph.add_edge(source, target)
        edge_labels[(source, target)] = relation

    plt.figure(figsize=figsize)

    pos = nx.spring_layout(graph, k=3, iterations=50, seed=42)

    for node_type, color in node_colors.items():
        nodes = [node for node, ntype in node_types.items() if ntype == node_type]
        if nodes:
            nx.draw_networkx_nodes(
                graph,
                pos,
                nodelist=nodes,
                node_color=color,
                node_size=1000,
                alpha=0.8,
                label=node_type,
            )

    for edge_type, color in edge_colors.items():
        edges = [
            (u, v) for (u, v), relation in edge_labels.items() if relation == edge_type
        ]
        if edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=edges,
                edge_color=color,
                alpha=0.7,
                arrows=True,
                arrowsize=20,
                arrowstyle="->",
                width=2,
            )

    truncated_labels = {
        node: node.split(".")[-1] if len(node) > 20 else node for node in graph.nodes()
    }
    nx.draw_networkx_labels(
        graph, pos, truncated_labels, font_size=8, font_weight="bold"
    )
    nx.draw_networkx_edge_labels(
        graph, pos, edge_labels, font_size=6, font_color="black"
    )

    node_legend = [
        Rectangle((0, 0), 1, 1, facecolor=color, alpha=0.8)
        for color in node_colors.values()
    ]
    plt.legend(
        node_legend,
        node_colors.keys(),
        loc="upper left",
        bbox_to_anchor=(0, 1),
        title="Node Types",
    )
    edge_legend = [
        Line2D([0], [0], color=color, linewidth=3, alpha=0.7)
        for color in edge_colors.values()
    ]
    plt.legend(
        edge_legend,
        edge_colors.keys(),
        loc="upper right",
        bbox_to_anchor=(1, 1),
        title="Relations",
    )

    plt.title(title, fontsize=16, fontweight="bold", pad=20)
    plt.axis("off")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Graph saved to: {save_path}")

    plt.show()


def plot_knowledge_graph(
    relationships: List[Relationship],
    title: str = "Python Code Knowledge Graph",
    figsize: Tuple[int, int] = (15, 10),
    save_path: Optional[str] = None,
):
    """
    Plot the knowledge graph from relationships using networkx and matplotlib.

    Args:
        relationships: List of Relationship objects
        title: Title for the graph
        figsize: Figure size (width, height)
        save_path: Optional path to save the plot
    """
    graph = nx.DiGraph()

    node_colors = {
        "MODULE": "#FF6B6B",  # Red
        "CLASS": "#4ECDC4",  # Teal
        "FUNCTION": "#45B7D1",  # Blue
        "METHOD": "#96CEB4",  # Green
        "FIELD": "#FFEAA7",  # Yellow
        "GLOBAL_VARIABLE": "#DDA0DD",  # Plum
    }

    edge_colors = {
        "CONTAINS": "#2D3436",
        "HAS_METHOD": "#00B894",
        "HAS_FIELD": "#FDCB6E",
        "INHERITS": "#E17055",
        "HAS_PARAMETER": "#6C5CE7",
        "MODULE_NODE": "#74B9FF",
    }

    node_types = {}
    edge_labels = {}

    for rel in relationships:
        source_type = rel.attributes.get("source_kind", "UNKNOWN")
        target_type = rel.attributes.get("target_kind", "UNKNOWN")

        graph.add_node(rel.source)
        graph.add_node(rel.target)

        node_types[rel.source] = source_type
        node_types[rel.target] = target_type

        graph.add_edge(rel.source, rel.target)
        edge_labels[(rel.source, rel.target)] = rel.relationship

    plt.figure(figsize=figsize)

    pos = nx.spring_layout(graph, k=3, iterations=50, seed=42)

    for node_type, color in node_colors.items():
        nodes = [node for node, ntype in node_types.items() if ntype == node_type]
        if nodes:
            nx.draw_networkx_nodes(
                graph,
                pos,
                nodelist=nodes,
                node_color=color,
                node_size=1000,
                alpha=0.8,
                label=node_type,
            )

    for edge_type, color in edge_colors.items():
        edges = [
            (u, v) for (u, v), relation in edge_labels.items() if relation == edge_type
        ]
        if edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=edges,
                edge_color=color,
                alpha=0.7,
                arrows=True,
                arrowsize=20,
                arrowstyle="->",
                width=2,
            )

    truncated_labels = {
        node: node.split(".")[-1] if len(node) > 20 else node for node in graph.nodes()
    }
    nx.draw_networkx_labels(
        graph, pos, truncated_labels, font_size=8, font_weight="bold"
    )
    nx.draw_networkx_edge_labels(
        graph, pos, edge_labels, font_size=6, font_color="black"
    )

    node_legend = [
        Rectangle((0, 0), 1, 1, facecolor=color, alpha=0.8)
        for color in node_colors.values()
    ]
    plt.legend(
        node_legend,
        node_colors.keys(),
        loc="upper left",
        bbox_to_anchor=(0, 1),
        title="Node Types",
    )
    edge_legend = [
        Line2D([0], [0], color=color, linewidth=3, alpha=0.7)
        for color in edge_colors.values()
    ]
    plt.legend(
        edge_legend,
        edge_colors.keys(),
        loc="upper right",
        bbox_to_anchor=(1, 1),
        title="Relations",
    )

    plt.title(title, fontsize=16, fontweight="bold", pad=20)
    plt.axis("off")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Graph saved to: {save_path}")

    plt.show()
