"""Deterministic visualization of the canonical case data."""

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

from case_generation import MysteryCase, case_to_graph_data


def draw_case_graph(
    case: MysteryCase,
    output_path: str | Path,
    language: str = "English",
) -> Path:
    spanish = language.strip().casefold() in {"spanish", "español", "es", "castellano"}
    relation_labels = (
        {
            "murdered": "asesinó",
            "motive": "motivo",
            "knows_secret": "conoce el secreto de",
            "corroborated_by": "testigo de",
            "implicates": "implica a",
        }
        if spanish
        else {}
    )
    graph_data = case_to_graph_data(case)
    graph = nx.DiGraph()
    for node in graph_data["nodes"]:
        node_id = node["id"]
        label = node_id
        if spanish and node["type"] == "clue":
            label = "Pista: " + node_id.removeprefix("Clue: ")
        graph.add_node(node_id, kind=node["type"], label=label)
    for relation in graph_data["rels"]:
        source = relation["source"]
        target = relation["target"]
        label = relation_labels.get(relation["type"], relation["type"])
        if graph.has_edge(source, target):
            graph[source][target]["label"] += f", {label}"
        else:
            graph.add_edge(source, target, label=label)

    positions = nx.spring_layout(graph, seed=42)
    figure, axis = plt.subplots(figsize=(12, 9))
    node_colors = []
    for node in graph.nodes:
        kind = graph.nodes[node]["kind"]
        if kind == "victim":
            node_colors.append("#d96c5f")
        elif kind == "clue":
            node_colors.append("#e2b34f")
        else:
            node_colors.append("#6a9c89")
    nx.draw_networkx(
        graph,
        positions,
        ax=axis,
        with_labels=True,
        labels=nx.get_node_attributes(graph, "label"),
        node_color=node_colors,
        node_size=1500,
        font_size=8,
        edge_color="#777777",
        arrows=True,
    )
    edge_labels = nx.get_edge_attributes(graph, "label")
    nx.draw_networkx_edge_labels(
        graph,
        positions,
        edge_labels=edge_labels,
        ax=axis,
        font_size=7,
        label_pos=0.35,
    )
    axis.set_axis_off()
    figure.tight_layout()

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return destination
