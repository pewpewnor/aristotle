import asyncio
from pathlib import Path

from aristotle.agent.loaded_codebases import update_loaded_codebase_status
from aristotle.graph.parser.codebase_parser import CodebaseParser
from aristotle.graph.parser.parser_settings import ParserSettings
from src.aristotle.graph import GraphDatabase
from src.aristotle.repository_loader import clone_git_repository
from src.aristotle.vector import DocumentationsDatabase

repos = [
    ("https://github.com/dmlc/xgboost.git", "9c0efcee38450e786d349a1ec558ca453c6df927"),
    # (
    #     "https://github.com/fastai/fastai.git",
    #     "1ac4ee147baf86d2f66f13da9d755a4970f1160b",
    # ),
    (
        "https://github.com/getzep/graphiti.git",
        "3200afa363cc71db8533c09040d1d7091c6ad8fe",
    ),
    (
        "https://github.com/keras-team/keras.git",
        "89d953e1631b72c5b44397388d85f2a46c3f6e42",
    ),
    (
        "https://github.com/microsoft/qlib.git",
        "78b77e302b9cab90100d05c6c534e2ed13980860",
    ),
    ("https://github.com/topoteretes/cognee", None),
    # (
    #     "https://github.com/huggingface/diffusers.git",
    #     "3c8b67b3711b668a6e7867e08b54280e51454eb5",
    # ),
]


async def main():
    graph_db = GraphDatabase()
    docs_db = DocumentationsDatabase()

    for repo, commit in repos:
        codebase_name = Path(repo).stem

        print(f"[STEP] Loading repository: {repo} at commit {commit}")
        codebase_path, reference_prefix = clone_git_repository(
            repo, commit_id=commit, codebase_name=codebase_name
        )

        # update_loaded_codebase_status(codebase_name, "LOADING_IN_PROGRESS")

        print(f"[STEP] Loading documents into vector database...")
        docs_db.load_dir(
            codebase_path,
            codebase_name,
            reference_prefix=reference_prefix,
            print_progress=False,
        )

        # print(f"[STEP] Parsing codebase '{codebase_name}'...")
        # parser = CodebaseParser(codebase_name, ParserSettings())
        # parser.parse_dir(
        #     codebase_path, reference_prefix=reference_prefix, print_progress=False
        # )
        #
        # print(
        #     f"[STEP] Inserting {len(parser.get_nodes())} nodes and {len(parser.get_relationships())} into graph database..."
        # )
        # await graph_db.insert_parser_results(parser)
        #
        # update_loaded_codebase_status(codebase_name, "LOADED")
        print(f"[SUCCESS] Repository loaded successfully: {codebase_name}")


if __name__ == "__main__":
    asyncio.run(main())
