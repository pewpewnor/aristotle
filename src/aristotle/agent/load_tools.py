import asyncio
import json
from pathlib import Path

from langchain_core.tools import BaseTool

from aristotle.agent.loaded_codebases import update_loaded_codebase_status

from ..graph.parser import CodebaseParser, ParserSettings
from ..repository_loader.git_integration import \
    clone_git_repository as load_git_repository
from ..repository_loader.pypi_integration import \
    clone_pypi_package as load_pypi_package
from .args_schemas import CodebaseLoaderToolArgs
from .databases import docs_db, graph_db, worker_pool
from .loaded_codebases import (get_loaded_codebase_status, list_all_codebases,
                               update_loaded_codebase_status)


def is_git_url(repository: str):
    return repository.startswith(("http://", "https://", "git://"))


def automatic_codebase_name(repository: str):
    repository = repository.strip()
    if is_git_url(repository):
        repository = Path(repository).stem
    return repository.lower()


def background_task(
    codebase_name: str,
    codebase_path: str,
    reference_prefix: str,
    loop: asyncio.AbstractEventLoop,
):
    print(
        f"[INFO] Attempting to parse '{codebase_path}' with reference prefix '{reference_prefix}'"
    )

    parser_settings = ParserSettings()
    parser = CodebaseParser(codebase_name, parser_settings)
    parser.parse_dir(codebase_path, reference_prefix=reference_prefix)

    loaded_nodes = len(parser.get_nodes())
    loaded_relationships = len(parser.get_relationships())
    print(
        f"[INFO] Successfully parsed, now inserting {loaded_nodes} nodes"
        f" and {loaded_relationships} relationships into graph db..."
    )

    asyncio.run_coroutine_threadsafe(
        graph_db.insert_parser_results(parser), loop
    ).result()
    print(f"[INFO] Successfully inserted all nodes to Graph DB")

    loaded_docs = docs_db.load_dir(
        codebase_path, codebase_name, reference_prefix=reference_prefix
    )
    print(f"[INFO] Successfully loaded {loaded_docs} code documentation files")

    update_loaded_codebase_status(codebase_name, "LOADED")


class ListLoadedCodebases(BaseTool):
    name: str = "list_loaded_codebases"
    description: str = (
        "Obtain list of all codebases that has been loaded and thus ready to be searched through"
    )

    def __init__(self) -> None:
        super().__init__()

    def _run(self):
        print("[INFO] Agent retrieves list of all loaded codebases status")
        return list_all_codebases()


class CodebaseLoaderTool(BaseTool):
    name: str = "load_codebase"
    description: str = (
        "Load a codebase using a Git repository url or PyPI package name to extract knowledge and relationships."
    )

    def __init__(self) -> None:
        super().__init__()
        self.args_schema = CodebaseLoaderToolArgs

    def _run(self, repository: str):
        codebase_name = automatic_codebase_name(repository)
        try:
            if is_git_url(repository):
                codebase_path, reference_prefix = load_git_repository(repository)
            else:
                codebase_path, reference_prefix = load_pypi_package(repository)
        except Exception as e:
            return f"ERROR: {repository} is either invalid git url or invalid PyPi package or the repository doesn't exist, maybe try again with PyPi package name"

        worker_pool.submit(
            background_task,
            codebase_name,
            codebase_path,
            reference_prefix,
            asyncio.get_event_loop(),
        )
        return json.dumps(
            {
                "status": "codebase loading is scheduled and in progress, the user can periodically check whether it has finished loading and Aristotle would be able to use it once it's done",
                "repository": repository,
                "name": codebase_name,
            }
        )

    async def _arun(self, repository: str) -> str:
        codebase_name = automatic_codebase_name(repository)
        print(
            f"[INFO] Agent attempts to load codebase: '{repository}', inferred codebase name='{codebase_name}'"
        )
        status = get_loaded_codebase_status(codebase_name)
        if status == "LOADED" or status == "LOADING_IN_PROGRESS":
            return f"Codebase '{codebase_name}' loading status is currently {status}, there is no need to try to load it again, you can proceed knowing this information"

        try:
            if is_git_url(repository):
                codebase_path, reference_prefix = load_git_repository(repository)
            else:
                codebase_path, reference_prefix = load_pypi_package(repository)
        except Exception as e:
            return f"ERROR: {repository} is either invalid git url or invalid PyPi package or the repository doesn't exist, maybe try again with PyPi package name"

        loop = asyncio.get_running_loop()
        loop.run_in_executor(
            worker_pool,
            background_task,
            codebase_name,
            codebase_path,
            reference_prefix,
            asyncio.get_event_loop(),
        )
        update_loaded_codebase_status(codebase_name, "LOADING_IN_PROGRESS")
        print(f"[INFO] Agent scheduled to load codebase: '{repository}'")
        return json.dumps(
            {
                "status": "codebase loading is scheduled and in progress, the user can periodically check whether it has finished loading and Aristotle would be able to use it once it's done",
                "repository": repository,
                "name": codebase_name,
            }
        )
