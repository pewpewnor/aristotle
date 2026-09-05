from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from graphiti_core import Graphiti
from graphiti_core.cross_encoder.openai_reranker_client import \
    OpenAIRerankerClient
from graphiti_core.edges import EntityEdge
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.nodes import EntityNode

from aristotle.graph.parser import CodebaseParser
from aristotle.kbs import filter_graph_search

from .. import project_config
from .parser.fact_builder import build_fact


class GraphDatabase:
    def __init__(self):
        self.llm_config = LLMConfig(
            api_key="ollama",
            model=project_config.ollama_llm_main_model,
            small_model=project_config.ollama_llm_small_model,
            base_url=project_config.graphiti_ollama_base_url,
        )
        self.llm_client = OpenAIGenericClient(config=self.llm_config)
        self.graphiti = Graphiti(
            project_config.neo4j_uri,
            project_config.neo4j_user,
            project_config.neo4j_password,
            llm_client=self.llm_client,
            embedder=OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key="ollama",
                    embedding_model=project_config.ollama_embedding_model,
                    embedding_dim=768,
                    base_url=project_config.graphiti_ollama_base_url,
                )
            ),
            cross_encoder=OpenAIRerankerClient(
                client=self.llm_client, config=self.llm_config  # type: ignore
            ),
        )

    async def setup(self):
        await self.graphiti.build_indices_and_constraints()

    async def stop(self):
        try:
            await self.graphiti.close()
        except Exception:
            pass

    async def insert_parser_results(self, parser: CodebaseParser, print_progress=False):
        node_map: dict[str, EntityNode] = {}

        nodes = parser.get_nodes()
        num_nodes = len(nodes)
        print(f"[INFO] Inserting {num_nodes} nodes into graph db...")
        for i, node in enumerate(nodes):
            enode = EntityNode(
                uuid=node.uuid,
                name=node.uuid,
                group_id=parser.codebase_name,
                attributes={"kind": node.kind, **(node.attributes or {})},
            )
            enode.name_embedding = await self.graphiti.embedder.create(node.uuid)
            await enode.save(self.graphiti.driver)
            node_map[node.uuid] = enode
            if print_progress:
                print(f"Node inserted [{i+1} / {num_nodes}]: {node}")

        relationships = parser.get_relationships()
        num_relationships = len(relationships)
        print(f"[INFO] Inserting {num_relationships} relationships into graph db...")
        for i, relationship in enumerate(relationships):
            source = relationship.source
            relation = relationship.relationship
            target = relationship.target
            attrs = relationship.attributes
            now = datetime.now()

            target_node = node_map.get(target)
            source_node = node_map.get(source)
            enriched_attrs = cast(Dict[str, Optional[str]], dict(attrs or {}))

            if target_node and isinstance(target_node.attributes, dict):
                docstring = target_node.attributes.get("docstring")
                if isinstance(docstring, str):
                    enriched_attrs["target_docstring"] = docstring

            if source_node and isinstance(source_node.attributes, dict):
                docstring = source_node.attributes.get("docstring")
                if isinstance(docstring, str):
                    enriched_attrs["source_docstring"] = docstring

            fact = build_fact(source, relation, target, enriched_attrs)
            fact_embedding = await self.graphiti.embedder.create(fact)

            entity_edge = EntityEdge(
                group_id=parser.codebase_name,
                source_node_uuid=source,
                target_node_uuid=target,
                created_at=now,
                valid_at=now,
                name=relation,
                fact=fact,
                fact_embedding=fact_embedding,
                attributes=enriched_attrs,
            )

            await entity_edge.save(self.graphiti.driver)
            if print_progress:
                print(
                    f"Relationship inserted [{i+1} / {num_relationships}]: {relationship}"
                )

    async def search(
        self, query: str, top_k: int = project_config.top_k_graph_search
    ) -> List[EntityEdge]:
        results = await self.graphiti.search(query, num_results=top_k)
        return results
