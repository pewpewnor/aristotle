from typing import Dict, Tuple


class Node:
    def __init__(self, uuid: str, kind: str, attributes: Dict[str, str]):
        self.uuid = uuid
        self.kind = kind
        self.attributes = attributes

        assert self.attributes.get("name")

    def to_tuple(self) -> Tuple[str, str, Dict[str, str]]:
        return (self.uuid, self.kind, self.attributes)

    def __str__(self) -> str:
        return f"Node(uuid={self.uuid!r}, kind={self.kind!r}, attributes={self.attributes!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return False
        return (
            self.uuid == other.uuid
            and self.kind == other.kind
            and self.attributes == other.attributes
        )
