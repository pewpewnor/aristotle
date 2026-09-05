import asyncio
import time

from graphiti_core import Graphiti
from graphiti_core.cross_encoder.bge_reranker_client import BGERerankerClient
from graphiti_core.cross_encoder.openai_reranker_client import \
    OpenAIRerankerClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient

from . import project_config


async def run_search(question: str, top_n: int = 5):
    """Run a semantic search on Graphiti with BGE reranking."""
    llm_config = LLMConfig(
        api_key="ollama",
        model=project_config.ollama_llm_main_model,
        small_model=project_config.ollama_llm_small_model,
        base_url=project_config.ollama_base_url,
    )
    llm_client = OpenAIGenericClient(config=llm_config)

    graphiti = Graphiti(
        project_config.neo4j_uri,
        project_config.neo4j_user,
        project_config.neo4j_password,
        llm_client=llm_client,
        embedder=OpenAIEmbedder(
            config=OpenAIEmbedderConfig(
                api_key="ollama",
                embedding_model=project_config.ollama_embedding_model,
                embedding_dim=768,
                base_url=project_config.ollama_base_url,
            )
        ),
        # cross_encoder=BGERerankerClient(),
        cross_encoder=OpenAIRerankerClient(client=llm_client, config=llm_config),  # type: ignore
    )

    try:
        print(f"\n🔍 Searching for: '{question}' (top {top_n} results)...")
        start = time.time()

        results = await graphiti.search(question, num_results=top_n)

        end = time.time()
        print(f"⏱️  Elapsed time: {end - start:.2f}s\n")

        # Limit results
        for i, result in enumerate(results[:top_n], start=1):
            print(f"Result {i}:")
            print(result.fact)
            print("-" * 80)

    finally:
        await graphiti.close()
        print("\n🔒 Connection closed.")


def main():
    # Default question
    default_question = "what are the params for the bind method for Widget?"

    # Ask user
    question = input(f"Enter your question [{default_question}]: ").strip()
    if not question:
        question = default_question

    top_n_input = input("How many top results to show? [5]: ").strip()
    top_n = int(top_n_input) if top_n_input.isdigit() else 5

    # Run async search
    asyncio.run(run_search(question, top_n))


if __name__ == "__main__":
    main()
