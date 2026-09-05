import asyncio
import time

from src.aristotle.graph import GraphDatabase
from src.aristotle.graph.parser import CodebaseParser, ParserSettings
from src.aristotle.repository_loader import clone_pypi_package


async def graph(parser):
    graph = GraphDatabase()
    await graph.setup()
    await graph.insert_parser_results(parser)
    await graph.stop()


class Timer:
    def __init__(self, label):
        self.label = label

    def __enter__(self):
        self.start = time.time()
        print(f"⏳ {self.label}...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.time()
        self.elapsed = self.end - self.start
        print(f"✅ {self.label} done in {self.elapsed:.2f}s\n")


def main():
    codebase_name = "cognee"
    settings = ParserSettings()
    codebase_parser = CodebaseParser(codebase_name, settings)

    summary = {}

    try:
        with Timer(f"Cloning PyPI package '{codebase_name}'"):
            path, reference_prefix = clone_pypi_package(codebase_name)
            summary["clone_path"] = path

        with Timer("Parsing codebase"):
            codebase_parser.parse_dir(
                path, reference_prefix=reference_prefix, print_progress=True
            )
            nodes = codebase_parser.get_nodes()
            relationships = codebase_parser.get_relationships()
            summary["nodes"] = len(nodes)
            summary["relationships"] = len(relationships)

        with Timer("Inserting into Graphiti"):
            asyncio.run(graph(codebase_parser))

        print("\n" + "=" * 60)
        print(f"📊 Summary for '{codebase_name}'")
        print("=" * 60)
        print(f"📁 Cloned path: {summary.get('clone_path', 'N/A')}")
        print(f"🧩 Total nodes: {summary.get('nodes', 0)}")
        print(f"🔗 Total relationships: {summary.get('relationships', 0)}")
        total_time = (
            sum(v for k, v in globals().get("_timings", {}).items())
            if "_timings" in globals()
            else None
        )
        print(f"⏱️  Finished all operations successfully.\n")

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print(
            "Please update 'file_path' to point to a valid Python file you want to analyze."
        )

    except Exception as e:
        print(f"💥 Unexpected error: {e}")


if __name__ == "__main__":
    main()
