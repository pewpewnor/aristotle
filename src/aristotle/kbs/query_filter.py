import json
from typing import Any, Dict, List

from graphiti_core.edges import EntityEdge

allowed_attributes = {
    "source_kind",
    "target_kind",
    "reference",
    "target_name",
    "target_type",
    "target_signature",
    "target_return_type",
}


def filter_graph_search(results: List[EntityEdge]) -> List[Dict[str, Any]]:
    filtered = []
    for result in results:
        attributes = {
            k: v for k, v in result.attributes.items() if k in allowed_attributes
        }
        filtered.append({"information": result.fact, **attributes})
    return filtered


def filter_docs_search(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "information": result.get("text", ""),
            "codebase": result.get("codebase", ""),
            "reference": result.get("reference", ""),
        }
        for result in results
    ]


def combine_filter_search_information(
    graph_results: List[EntityEdge], docs_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    return filter_graph_search(graph_results) + filter_docs_search(docs_results)
