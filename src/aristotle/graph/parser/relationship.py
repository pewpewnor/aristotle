from typing import Dict, Tuple


class Relationship:
    def __init__(
        self, source: str, relationship: str, target: str, attributes: Dict[str, str]
    ):
        self.source = source
        self.relationship = relationship
        self.target = target
        self.attributes = attributes

        assert self.attributes.get("source_kind")
        assert self.attributes.get("target_kind")

    def to_tuple(self) -> Tuple[str, str, str, Dict[str, str]]:
        return (self.source, self.relationship, self.target, self.attributes)

    def __str__(self) -> str:
        return f"{self.source} ({self.attributes['source_kind']}) --[{self.relationship}]--> {self.target} ({self.attributes['target_kind']})"

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, Relationship)
        return (
            self.source == other.source
            and self.relationship == other.relationship
            and self.target == other.target
            and self.attributes == other.attributes
        )
