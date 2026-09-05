import pytest

from aristotle.graph.parser.codebase_parser import CodebaseParser
from aristotle.graph.parser.node import Node
from aristotle.graph.parser.parser_settings import ParserSettings
from aristotle.graph.parser.relationship import Relationship

file_name = "1.py"
source_file_path = f"./test_files/{file_name}"
codebase_name = "CodebaseName"


@pytest.fixture
def codebase_parser():
    return CodebaseParser(codebase_name, ParserSettings())


@pytest.fixture
def expected_nodes_and_relationships():
    expected_file_path = f"./{file_name}"

    nodes = [
        Node("CodebaseName.1", "MODULE", {"name": "1"}),
        Node(
            "CodebaseName.1.x",
            "GLOBAL_VARIABLE",
            {"name": "x", "reference": expected_file_path, "target_type": "int"},
        ),
        Node(
            "CodebaseName.1.Animal",
            "CLASS",
            {
                "name": "Animal",
                "reference": expected_file_path,
                "docstring": "Base class for animals.\n\nAnimal stores a name and can speak (prints its name).",
            },
        ),
        Node(
            "CodebaseName.1.Animal.__init__",
            "METHOD",
            {
                "name": "__init__",
                "reference": expected_file_path,
                "docstring": "Initialize an Animal with a name.\n\nArgs:\n    name: human-readable name for the animal",
            },
        ),
        Node(
            "CodebaseName.1.name",
            "FIELD",
            {"name": "name", "reference": expected_file_path},
        ),
        Node(
            "CodebaseName.1.Mammal",
            "CLASS",
            {
                "name": "Mammal",
                "reference": expected_file_path,
                "docstring": "Marker class that represents mammal-type animals.",
            },
        ),
        Node(
            "CodebaseName.1.Dog",
            "CLASS",
            {
                "name": "Dog",
                "reference": expected_file_path,
                "docstring": "A friendly dog that can bark.",
            },
        ),
        Node(
            "CodebaseName.1.Dog.bark",
            "METHOD",
            {
                "name": "bark",
                "reference": expected_file_path,
                "docstring": "Bark the provided words (print them).",
            },
        ),
        Node(
            "CodebaseName.1.words",
            "FIELD",
            {"name": "words", "reference": expected_file_path},
        ),
        Node(
            "CodebaseName.1.greet",
            "FUNCTION",
            {
                "name": "greet",
                "reference": expected_file_path,
                "docstring": "Greet an animal and report its age.\n\nReturns an integer example value.",
            },
        ),
        Node(
            "CodebaseName.1.greet.animal",
            "FIELD",
            {"name": "animal"},
        ),
        Node(
            "CodebaseName.1.greet.age",
            "FIELD",
            {"name": "age"},
        ),
    ]

    relationships = [
        Relationship(
            "CodebaseName.1",
            "CONTAINS",
            "CodebaseName.1.x",
            {
                "source_kind": "MODULE",
                "target_kind": "GLOBAL_VARIABLE",
                "reference": expected_file_path,
                "target_name": "x",
                "target_type": "int",
            },
        ),
        Relationship(
            "CodebaseName.1",
            "CONTAINS",
            "CodebaseName.1.Animal",
            {
                "source_kind": "MODULE",
                "target_kind": "CLASS",
                "reference": expected_file_path,
                "target_name": "Animal",
                "target_signature": "class Animal",
            },
        ),
        Relationship(
            "CodebaseName.1.Animal",
            "HAS_METHOD",
            "CodebaseName.1.Animal.__init__",
            {
                "source_kind": "CLASS",
                "target_kind": "METHOD",
                "reference": expected_file_path,
                "target_name": "__init__",
                "target_return_type": "None",
                "target_signature": "__init__(self, name: str) -> None",
            },
        ),
        Relationship(
            "CodebaseName.1.Animal",
            "HAS_FIELD",
            "CodebaseName.1.name",
            {
                "source_kind": "CLASS",
                "target_kind": "FIELD",
                "reference": expected_file_path,
                "target_name": "name",
                "target_type": "str",
            },
        ),
        Relationship(
            "CodebaseName.1.Animal",
            "HAS_FIELD",
            "CodebaseName.1.Animal.name",
            {
                "source_kind": "CLASS",
                "target_kind": "FIELD",
                "reference": expected_file_path,
                "target_name": "name",
                "target_type": "str",
            },
        ),
        Relationship(
            "CodebaseName.1.Animal.__init__",
            "HAS_PARAMETER",
            "CodebaseName.1.Animal.__init__.name",
            {
                "source_kind": "METHOD",
                "target_kind": "FIELD",
                "target_name": "name",
                "target_type": "str",
            },
        ),
        Relationship(
            "CodebaseName.1.Animal",
            "HAS_METHOD",
            "CodebaseName.1.Animal.speak",
            {
                "source_kind": "CLASS",
                "target_kind": "METHOD",
                "reference": expected_file_path,
                "target_name": "speak",
                "target_return_type": "None",
                "target_signature": "speak(self, ) -> None",
            },
        ),
        Relationship(
            "CodebaseName.1",
            "CONTAINS",
            "CodebaseName.1.Mammal",
            {
                "source_kind": "MODULE",
                "target_kind": "CLASS",
                "reference": expected_file_path,
                "target_name": "Mammal",
                "target_signature": "class Mammal",
            },
        ),
        Relationship(
            "CodebaseName.1",
            "CONTAINS",
            "CodebaseName.1.Dog",
            {
                "source_kind": "MODULE",
                "target_kind": "CLASS",
                "reference": expected_file_path,
                "target_name": "Dog",
                "target_signature": "class Dog(Animal, Mammal)",
            },
        ),
        Relationship(
            "CodebaseName.1.Dog",
            "INHERITS",
            "CodebaseName.1.Animal",
            {
                "source_kind": "CLASS",
                "target_kind": "CLASS",
            },
        ),
        Relationship(
            "CodebaseName.1.Dog",
            "INHERITS",
            "CodebaseName.1.Mammal",
            {
                "source_kind": "CLASS",
                "target_kind": "CLASS",
            },
        ),
        Relationship(
            "CodebaseName.1.Dog",
            "HAS_METHOD",
            "CodebaseName.1.Dog.bark",
            {
                "source_kind": "CLASS",
                "target_kind": "METHOD",
                "reference": expected_file_path,
                "target_name": "bark",
                "target_return_type": "None",
                "target_signature": "bark(self, words: str) -> None",
            },
        ),
        Relationship(
            "CodebaseName.1.Dog",
            "HAS_FIELD",
            "CodebaseName.1.words",
            {
                "source_kind": "CLASS",
                "target_kind": "FIELD",
                "reference": expected_file_path,
                "target_name": "words",
                "target_type": "str",
            },
        ),
        Relationship(
            "CodebaseName.1.Dog.bark",
            "HAS_PARAMETER",
            "CodebaseName.1.Dog.bark.words",
            {
                "source_kind": "METHOD",
                "target_kind": "FIELD",
                "target_name": "words",
                "target_type": "str",
            },
        ),
        Relationship(
            "CodebaseName.1",
            "CONTAINS",
            "CodebaseName.1.greet",
            {
                "source_kind": "MODULE",
                "target_kind": "FUNCTION",
                "reference": expected_file_path,
                "target_name": "greet",
                "target_return_type": "int",
                "target_signature": "greet(self, animal: Animal, age: int) -> int",
            },
        ),
        Relationship(
            "CodebaseName.1.greet",
            "HAS_PARAMETER",
            "CodebaseName.1.greet.animal",
            {
                "source_kind": "FUNCTION",
                "target_kind": "FIELD",
                "target_name": "animal",
                "target_type": "Animal",
            },
        ),
        Relationship(
            "CodebaseName.1.greet",
            "HAS_PARAMETER",
            "CodebaseName.1.greet.age",
            {
                "source_kind": "FUNCTION",
                "target_kind": "FIELD",
                "target_name": "age",
                "target_type": "int",
            },
        ),
    ]

    # Normalize expected relationships to include source_name when missing
    for rel in relationships:
        if "source_name" not in rel.attributes:
            rel.attributes["source_name"] = rel.source.split(".")[-1]

    return nodes, relationships


def test_nodes_and_relationships_match_expected(
    codebase_parser, expected_nodes_and_relationships
):
    expected_nodes, expected_relationships = expected_nodes_and_relationships
    codebase_parser.parse_file(source_file_path, f"./{file_name}", f"./{file_name}")
    nodes = codebase_parser.get_nodes()
    relationships = codebase_parser.get_relationships()

    # simple equality checks (order-insensitive)
    assert set(n.uuid for n in nodes) >= set(n.uuid for n in expected_nodes)
    # verify expected node attributes are present and match values
    nodes_by_uuid = {n.uuid: n for n in nodes}
    for exp in expected_nodes:
        assert exp.uuid in nodes_by_uuid, f"Expected node {exp.uuid} not found"
        parsed_attrs = nodes_by_uuid[exp.uuid].attributes
        for k, v in exp.attributes.items():
            assert (
                parsed_attrs.get(k) == v
            ), f"Node attribute mismatch for {exp.uuid}: key '{k}' expected {v!r}, got {parsed_attrs.get(k)!r}"
    # relationships are Relationship objects; extract (source, relationship, target)
    rel_keys = set((r.source, r.relationship, r.target) for r in relationships)
    expected_rel_keys = set(
        (r.source, r.relationship, r.target) for r in expected_relationships
    )
    assert expected_rel_keys.issubset(
        rel_keys
    ), "Generated relationships missing expected ones"

    # verify attributes for each expected relationship match exactly
    actual_attr_map = {
        (r.source, r.relationship, r.target): r.attributes for r in relationships
    }
    for exp in expected_relationships:
        key = (exp.source, exp.relationship, exp.target)
        assert (
            key in actual_attr_map
        ), f"Expected relationship {key} not found in parsed relationships"
        actual_attrs = actual_attr_map[key]
        expected_attrs = exp.attributes
        assert (
            actual_attrs == expected_attrs
        ), f"Attributes mismatch for relationship {key}: expected {expected_attrs!r}, got {actual_attrs!r}"
