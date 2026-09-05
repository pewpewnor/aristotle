import os

from .ast_traverser import ASTTraverser
from .node import Node
from .parser_settings import ParserSettings
from .relationship import Relationship


class CodebaseParser:
    def __init__(self, codebase_name: str, settings: ParserSettings):
        self.codebase_name = codebase_name
        self.relationships: list[Relationship] = []
        self.settings = settings
        self.nodes: list[Node] = []

    def parse_file(self, file_path: str, virtual_path: str, reference: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        nodes, relationships = ASTTraverser(
            self.codebase_name, file_path, virtual_path, reference, self.settings
        ).traverse()
        self.nodes.extend(nodes)
        self.relationships.extend(relationships)

    def parse_dir(
        self,
        codebase_path: str,
        reference_prefix: str = "",
        print_progress: bool = False,
    ):
        for root_path, dir_names, file_names in os.walk(codebase_path):
            dir_names[:] = [
                dir_name
                for dir_name in dir_names
                if not dir_name.startswith(".")
                and (
                    not self.settings.include_private_dirs
                    and not dir_name.startswith("_")
                )
            ]

            for file_name in file_names:
                if (file_name.endswith(".py") or file_name.endswith(".ipynb")) and (
                    not self.settings.include_test_files
                    and not file_name.startswith("test_")
                ):
                    file_path = os.path.join(root_path, file_name)
                    virtual_path = os.path.join(
                        ".", root_path[len(codebase_path) + 1 :], file_name
                    )
                    reference = f"{reference_prefix}{root_path[len(codebase_path) + 1 :]}/{file_name}"

                    try:
                        self.parse_file(file_path, virtual_path, reference)
                        if print_progress:
                            print(f"[INFO] Parsed '{file_path}' as '{reference}'")
                    except Exception as e:
                        if print_progress:
                            print(f"[WARN] Failed to parse '{file_path}': {e}")

    def get_nodes(self) -> list[Node]:
        return self.nodes

    def get_relationships(self) -> list[Relationship]:
        return self.relationships
