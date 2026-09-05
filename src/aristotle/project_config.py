import os

import dotenv

dotenv.load_dotenv()

neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
neo4j_password = os.environ.get("NEO4J_PASSWORD", "neo4j")

ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
graphiti_ollama_base_url = os.environ.get(
    "GRAPHITI_OLLAMA_BASE_URL", f"{ollama_base_url}/v1"
)
ollama_llm_main_model = os.environ.get("OLLAMA_LLM_MAIN_MODEL", "llama3.1:8b")
ollama_llm_small_model = os.environ.get("OLLAMA_LLM_SMALL_MODEL", ollama_llm_main_model)
ollama_embedding_model = os.environ.get(
    "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest"
)
llm_temperature = float(os.environ.get("LLM_TEMPERATURE", 0.3))

git_clone_dir = os.environ.get("GIT_CLONE_DIR", "./.cloned")
faiss_data_dir = os.environ.get("FAISS_DATA_DIR", "./.index")

system_prompt_file = os.environ.get("SYSTEM_PROMPT_FILE", "system_prompt.txt")
top_k_graph_search = int(os.environ.get("TOP_K_GRAPH_SEARCH", 7))
top_k_vector_search = int(os.environ.get("TOP_K_VECTOR_SEARCH", 3))

pool_max_workers = int(os.environ.get("POOL_MAX_WORKERS", 1))
loaded_codebases_file = os.environ.get("LOADED_CODEBASES_FILE", "loaded_codebases.json")

ollama_llm_eval_model = os.environ.get("OLLAMA_LLM_EVAL_MODEL", "qwen3:8b")
enable_evaluation = bool(os.environ.get("ENABLE_EVALUATION") == "true")
evaluation_temp_file = os.environ.get(
    "EVALUATION_TEMP_FILE", "./eval/combined_results.json"
)
evaluation_metric_file = os.environ.get(
    "EVALUATION_METRIC_FILE", "./eval/eval_results.csv"
)
evaluation_progress_file = os.environ.get(
    "EVALUATION_PROGRESS_FILE", "./eval/eval_progress.csv"
)
