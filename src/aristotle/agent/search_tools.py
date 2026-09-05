import json

from langchain_core.tools import BaseTool
from langgraph.pregel.main import asyncio

from aristotle import project_config
from aristotle.kbs import (combine_filter_search_information,
                                        filter_docs_search,
                                        filter_graph_search)
from aristotle.kbs import validate_relationship

from .args_schemas import EntityRelationshipSearchArgs, SearchToolArgs
from .databases import docs_db, graph_db


class CombinedSearchTool(BaseTool):
    name: str = "search"
    description: str = (
        "Search for entities, relationships, and code documentations in the codebase."
        "Provide a 'query' describing what to find in detail along with the codebase name."
    )

    def __init__(self) -> None:
        super().__init__()
        self.args_schema = SearchToolArgs

    async def _run(self, query: str) -> str:
        print(f"[WARN] Agent combined searched (sync run): '{query}'")
        try:
            loop = asyncio.get_running_loop()
            return loop.create_task(self._arun(query)).result()
        except Exception as e:
            print("[ERROR]:", e)
            return f"Error: {str(e)}"

    async def _arun(self, query: str) -> str:
        print(f"[INFO] Agent combined searched (async run): '{query}'")
        try:
            graph_information = await graph_db.search(query)
            docs_information = docs_db.search(query)
            combined_result = json.dumps(
                combine_filter_search_information(graph_information, docs_information)
            )
            if project_config.enable_evaluation:
                with open(project_config.evaluation_temp_file, "w") as f:
                    f.write(combined_result)
            else:
                print("[INFO] Combined search result:", combined_result)
            return combined_result
        except Exception as e:
            print("[ERROR] While combined search:", e)
            return f"Error: {str(e)}"


class GraphSearchTool(BaseTool):
    name: str = "search_code"
    description: str = (
        "Search for entities and relationships of source code in the codebase."
        "Provide a 'query' describing what to find in detail along with the codebase name."
    )

    def __init__(self) -> None:
        super().__init__()
        self.args_schema = SearchToolArgs

    async def _run(self, query: str) -> str:
        print(f"[WARN] Agent graph only searched (sync run): '{query}'")
        try:
            loop = asyncio.get_running_loop()
            return loop.create_task(self._arun(query)).result()
        except Exception as e:
            print("[ERROR]:", e)
            return f"Error: {str(e)}"

    async def _arun(self, query: str) -> str:
        print(f"[INFO] Agent graph only searched (async run): '{query}'")
        try:
            graph_information = await graph_db.search(query)
            print("[INFO] Graph search result:", graph_information)
            return json.dumps(filter_graph_search(graph_information))
        except Exception as e:
            print("[ERROR]:", e)
            return f"Error: {str(e)}"


class DocumentationsSearchTool(BaseTool):
    name: str = "search_docs"
    description: str = (
        "Search for code documentation chunks in the codebase."
        "Provide a 'query' describing what to find in detail along with the codebase name."
    )

    def __init__(self) -> None:
        super().__init__()
        self.args_schema = SearchToolArgs

    def _run(self, query: str) -> str:
        print(f"[INFO] Agent docs only searched: '{query}'")
        try:
            docs_information = docs_db.search(query)
            print("[INFO] Docs search result:", docs_information)
            return json.dumps(filter_docs_search(docs_information))
        except Exception as e:
            print("[ERROR]:", e)
            return f"Error: {str(e)}"


class EntityRelationshipSearchTool(BaseTool):
    name: str = "search_entity_relationship"
    description: str = (
        "Search for specific entities and their relationships in the codebase knowledge graph. "
        "Use this tool when you need to find how entities are connected, such as which methods "
        "a class has, which parameters a function takes, or what a module contains."
    )

    def __init__(self) -> None:
        super().__init__()
        self.args_schema = EntityRelationshipSearchArgs

    async def _run(
        self,
        codebase_name: str,
        entity_name: str,
        entity_kind: str,
        relationship_name: str,
        relationship_type: str,
    ) -> str:
        print(
            f"[WARN] Agent entity relationship searched (sync run): entity='{entity_name}', kind='{entity_kind}', relationship='{relationship_type}'"
        )
        try:
            loop = asyncio.get_running_loop()
            return loop.create_task(
                self._arun(
                    codebase_name,
                    entity_name,
                    entity_kind,
                    relationship_name,
                    relationship_type,
                )
            ).result()
        except Exception as e:
            print("[ERROR]:", e)
            return f"Error: {str(e)}"

    async def _arun(
        self,
        codebase_name: str,
        entity_name: str,
        entity_kind: str,
        relationship_name: str,
        relationship_type: str,
    ) -> str:
        print(
            f"[INFO] Agent entity relationship searched (async run): entity='{entity_name}', kind='{entity_kind}', relationship='{relationship_type}'"
        )

        try:
            is_valid, validation_message = validate_relationship(
                entity_kind, relationship_type
            )

            if not is_valid:
                error_result = {
                    "error": "Invalid relationship",
                    "message": validation_message,
                    "codebase": codebase_name,
                    "entity_name": entity_name,
                    "entity_kind": entity_kind,
                    "relationship_name": relationship_name,
                    "relationship_type": relationship_type,
                }
                print(f"[ERROR] Validation failed: {validation_message}")
                return json.dumps(error_result)

            search_query = (
                f"In codebase '{codebase_name}' find {entity_kind} named '{entity_name}'"
                f"which {relationship_type} a '{relationship_name}'"
            )

            graph_result = await graph_db.search(search_query)

            result = {
                "codebase": codebase_name,
                "entity_name": entity_name,
                "entity_kind": entity_kind,
                "relationship_name": relationship_name,
                "relationship_type": relationship_type,
                "validation": validation_message,
                "results": graph_result,
            }

            print("[INFO] Entity relationship search result:", result)
            return json.dumps(result)

        except Exception as e:
            print("[ERROR] While searching entity relationship:", e)
            return f"Error: {str(e)}"
