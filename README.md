# Aristotle Backend

![Aristotle logo](media/aristotle.png)

Aristotle is an AI framework for building a coding assistant that can answer questions about codebases, Git repositories, and Python packages. This repository contains its local-first backend: a FastAPI service used by the VS Code extension, an agent workflow, code-knowledge-graph indexing, and semantic documentation search.

Its central idea is model amplification. A relatively weak or small local model does not need to remember every API, implementation detail, or README in a repository: Aristotle retrieves the relevant evidence from a semantic graph and a vector index, then gives that evidence to the model when it answers. The retrieval layer supplies grounded, code-specific context while Ollama keeps inference local and configurable.

The backend is a retrieval-augmented generation (RAG) system. It does not normally fine-tune a model or place an entire repository in the model's context. Instead, it parses and indexes a codebase, retrieves the most relevant structure and documentation for each question, and gives that evidence to the model at answer time.

## What it does

- Accepts chat questions, conversation history, and optional file context through HTTP.
- Loads codebases from Git URLs or PyPI package names in the background.
- Parses Python source and notebooks into entities and relationships.
- Stores code relationships in a Graphiti/Neo4j knowledge graph.
- Splits Markdown documentation into chunks and indexes the chunks in FAISS.
- Uses an agentic LangGraph workflow to decide when to search, load a codebase, or list loaded codebases.
- Returns a Markdown answer together with references selected from retrieved code and documentation.
- Accepts individual workspace files from the VS Code extension through the `/load` endpoint.

## Use cases and benefits

Aristotle is intended for developers working in unfamiliar or rapidly changing codebases. Typical questions include:

- “Which parameters does this method accept, and what does it return?”
- “Where is this feature implemented?”
- “How are these modules or classes connected?”
- “What does this package's documented configuration option do?”

The graph representation is useful for structural questions—classes, functions, modules, parameters, and relationships—while the documentation index is useful for prose, examples, and README content. Combining both gives the model more specific evidence than a general-purpose chat model would have on its own, and keeps repository content searchable without requiring every file to fit into one prompt.

In this sense, Aristotle is both:

- an AI framework for composing local models, retrieval tools, a knowledge graph, and a vector store into a coding assistant; and
- a coding assistant client/backend that developers can use to explore unfamiliar source code and documentation.

## AI architecture

### Model roles

Aristotle uses several model-facing components, each with a distinct job:

| Component | Role | Configuration |
| --- | --- | --- |
| Tool-calling chat model | Plans the next step, asks for retrieval, lists loaded codebases, or schedules a load operation | `OLLAMA_LLM_MAIN_MODEL`, default `llama3.1:8b` |
| Structured-response chat model | Converts the conversation and retrieved evidence into the final JSON response | The same main model through `ChatOllama`, with JSON output requested |
| Embedding model | Converts documentation, graph facts, and queries into vectors for semantic retrieval | `OLLAMA_EMBEDDING_MODEL`; code default is `nomic-embed-text:latest`, while `.env.example` selects `mxbai-embed-large:latest` |
| Graphiti LLM client | Supports graph construction/search operations and reranking through an OpenAI-compatible Ollama endpoint | `OLLAMA_LLM_MAIN_MODEL`, `OLLAMA_LLM_SMALL_MODEL`, and `GRAPHITI_OLLAMA_BASE_URL` |
| Neo4j + Graphiti | Persists code entities, relationships, facts, and their embeddings | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` |
| FAISS + JSON metadata | Persists the vector index and the documentation/chunk metadata | `FAISS_DATA_DIR`, default `./.index` |

The default design is local-model friendly: Ollama provides the chat and embedding endpoints, Neo4j stores the graph, and FAISS stores the documentation index. The endpoint settings can also point at compatible services running elsewhere.

### Request-time model pipeline

At question time, the main model acts as a tool-using planner, not as the retrieval database itself:

```
User question + history + optional attached files
                         |
                         v
             FastAPI POST /chat
                         |
                         v
        LangGraph AristotleAgent state machine
                         |
              ChatOllama tool-calling model
                         |
       +-----------------+------------------+
       |                                    |
       v                                    v
   search tool                    load/list tools when needed
       |
       +----------------------+----------------------+
       |                                             |
       v                                             v
 Graphiti / Neo4j search                    FAISS documentation search
       |                                             |
       +----------------------+----------------------+
                              |
                              v
             filtered and combined evidence
                              |
                              v
       ChatOllama structured-response model
                  (JSON / ResponseFormat)
                              |
                              v
                Markdown answer + references
```

The LangGraph workflow starts with the agent node. If the model asks for a tool, the workflow visits the tool node and then returns to the agent. It stops after a response is ready or the configured tool-call limit is reached. A second model invocation requests a JSON object containing `response` and `references`; invalid JSON is retried up to the configured retry limit before a fallback response is returned.

### Codebase indexing pipeline

When a Git repository or PyPI package is loaded, the backend follows this path:

1. `CodebaseLoaderTool` normalizes the repository/package name and clones the source under `GIT_CLONE_DIR` (default `./.cloned`).
2. `CodebaseParser` walks Python files and notebooks, ignoring hidden directories and test/private content by default.
3. The AST traverser produces code nodes and relationships such as module, class, function, parameter, and containment/call-like links.
4. `GraphDatabase` writes those entities and relationships to Graphiti backed by Neo4j. Graph embeddings and generated relationship facts make semantic graph search possible.
5. `DocumentationsDatabase` scans Markdown files, splits them into chunks, adds codebase/file context, embeds them with Ollama, and stores the vectors in a FAISS inner-product index with JSON metadata.
6. The status in `loaded_codebases.json` is updated so the agent can avoid scheduling a duplicate load.

The workspace upload route follows the same intended indexing boundary for individual `.py` and `.md` files. The VS Code extension uses that route when loading the current workspace.

### Retrieval details

The enabled `search` tool performs two searches for a query:

1. Graphiti searches the Neo4j-backed code knowledge graph and returns relevant relationship facts.
2. FAISS embeds the query with the configured Ollama embedding model and returns the nearest documentation chunks.

The backend filters each result into a compact evidence object, combines graph and documentation evidence, and gives that result back to the agent. References are preserved so the final response can point back to source files or repository URLs where available.

## How the service works

The main HTTP entry point is `src/server/app.py`:

- `GET /` returns a small health-style index page.
- `POST /chat` accepts a `message`, optional `history`, and optional attached `files`; it returns a generated `response` and `references`.
- `POST /load` accepts `codebase_name`, `file_path`, and `file_content` for workspace-file ingestion.

The application initializes the agent and shared graph/documentation databases at import time, prepares Graphiti indexes during startup, and closes the graph connection during shutdown. The VS Code extension normally talks to this service at `http://localhost:8000`.

## Evaluation and benchmark

The evaluation harness uses the [`Qodo/deep_code_bench`](https://huggingface.co/datasets/Qodo/deep_code_bench) dataset. It combines the dataset's train and test splits, uses repository/commit metadata to load the matching code snapshot, asks questions about that codebase, and records the generated answer, expected answer, retrieved contexts, and response time.

The saved evaluation artifacts show Aristotle being evaluated against these open-source Python projects:

- [Graphiti](https://github.com/getzep/graphiti)
- [Keras](https://github.com/keras-team/keras)
- [Qlib](https://github.com/microsoft/qlib)

The repository's manual loading/evaluation configuration also includes [XGBoost](https://github.com/dmlc/xgboost) and [Cognee](https://github.com/topoteretes/cognee) as additional codebase targets, with other candidates retained in comments. The current saved target list does not contain a completed Hugging Face Transformers run, so the project-specific claims here are limited to the repositories represented by the local artifacts.

The benchmark includes both retrieval and baseline experiments:

1. `eval/evaluate_rag.py` loads the repositories, asks `AristotleAgent` questions, and captures the graph/vector evidence returned by the combined search tool.
2. `eval/evaluate_llm.py` queries the configured Ollama chat model directly on hard questions, without Aristotle retrieval, to provide a weak/local-model baseline.
3. `eval/evaluate_csv.py` evaluates recorded answers with Ragas using `AnswerRelevancy`, `Faithfulness`, `ContextPrecision`, and `ContextRecall`; the stored `ragas_score` is the mean of those four metrics.
4. The checked-in progress/result files compare variants such as normal direct-model answers, Aristotle retrieval without supplied facts, and retrieval with supplied facts.

These are reproducible experiment artifacts rather than a universal performance guarantee: results depend on the pinned repository commits, dataset slice, parser/index state, selected local models, and retrieval settings. The important benchmark question is whether semantic graph search plus vector search lets a smaller local model answer source-code questions more accurately and with better supporting context than the same model without retrieval.

## Quick start

### Prerequisites

- Python 3.13 or newer
- [`uv`](https://docs.astral.sh/uv/)
- A reachable Neo4j instance
- [Ollama](https://ollama.com/) with a chat model and an embedding model
- The VS Code extension in [`../aristotle-vscode`](../aristotle-vscode) if you want the editor integration

### Install and configure

From this repository:

```
cp .env.example .env
uv sync
```

Review `.env` and make sure Neo4j and Ollama are reachable. The example configuration uses:

```
NEO4J_URI=bolt://localhost:7687
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MAIN_MODEL=llama3.1:8b
OLLAMA_EMBEDDING_MODEL=mxbai-embed-large:latest
```

Pull the selected models into Ollama if they are not already available:

```
ollama pull llama3.1:8b
ollama pull mxbai-embed-large:latest
```

### Start the API

Run the server from the repository root:

```
uv run uvicorn src.server.app:app --host 127.0.0.1 --port 8000
```

The VS Code extension can now use its default backend URL. To use another host or port, set `aristotle.api_base_url` in VS Code settings.

The included `Dockerfile` exposes the same port and uses `uv sync` inside the image; Neo4j and Ollama still need to be supplied as reachable services.

## Configuration

The most important environment variables are:

| Variable | Purpose |
| --- | --- |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Graph database connection |
| `OLLAMA_BASE_URL` | Chat and embedding endpoint |
| `GRAPHITI_OLLAMA_BASE_URL` | Optional Graphiti-specific OpenAI-compatible endpoint; defaults to `$OLLAMA_BASE_URL/v1` |
| `OLLAMA_LLM_MAIN_MODEL` | Main chat/Graphiti model |
| `OLLAMA_LLM_SMALL_MODEL` | Smaller Graphiti model; defaults to the main model |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model for docs and graph data |
| `GIT_CLONE_DIR` | Temporary/persistent clone location |
| `FAISS_DATA_DIR` | FAISS index and metadata location |
| `TOP_K_GRAPH_SEARCH`, `TOP_K_VECTOR_SEARCH` | Retrieval limits |
| `SYSTEM_PROMPT_FILE` | Optional replacement system prompt |
| `POOL_MAX_WORKERS` | Background indexing worker count |

## Repository layout

```
src/server/                 FastAPI application and request models
src/aristotle/agent/        LangGraph agent and load/search tools
src/aristotle/graph/        Graphiti/Neo4j integration and AST parser
src/aristotle/vector/       Markdown chunking, embeddings, and FAISS index
src/aristotle/repository_loader/
                             Git and PyPI loading helpers
eval/                        Evaluation utilities and model files
main_*.py                   Manual indexing/search entry points
Dockerfile                  Container entry point for the API
```

## Development notes

The runtime is still evolving: graph search requires Neo4j and model access, documentation search requires a compatible FAISS index, and indexing quality depends on the parser settings and the selected embedding/chat models.
