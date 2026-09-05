import sys
import time

from src.aristotle.repository_loader import clone_pypi_package
from src.aristotle.vector import DocumentationsDatabase

libraries = [
    "numpy",
    "pandas",
    "requests",
    "fastapi",
    "pydantic",
    "typer",
    "sqlmodel",
    "httpx",
    "rich",
    "textual",
    "ruff",
    "black",
    "poetry",
    "pdm",
    "hatch",
    "mkdocs",
    "mkdocs-material",
    "mkdocstrings",
    "langchain",
    "llama-index",
    "haystack-ai",
    "transformers",
    "datasets",
    "diffusers",
    "accelerate",
    "peft",
    "optimum",
    "evaluate",
    "gradio",
    "streamlit",
    "polars",
    "ibis-framework",
    "piccolo",
    "prisma",
    "timm",
    "ultralytics",
    "mmsegmentation",
    "mmcv",
    "hydra-core",
    "ragas",
]


def main():
    db = DocumentationsDatabase()
    print(sys.argv[1])
    print(db.search(sys.argv[1]))
    # for repo in ["mkdocs-material"]:
    #     codebase_path, reference_prefix = clone_pypi_package(repo)
    #     db.load_dir(codebase_path, repo, reference_prefix, print_progress=True)


if __name__ == "__main__":
    main()
