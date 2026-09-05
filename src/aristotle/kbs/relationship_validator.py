from typing import Tuple


def validate_relationship(entity_kind: str, relationship_kind: str) -> Tuple[bool, str]:
    valid_relationships = {
        "MODULE": {"CONTAINS"},
        "CLASS": {"HAS_METHOD", "HAS_FIELD", "INHERITS"},
        "FUNCTION": {"HAS_PARAMETER"},
        "FIELD": set(),
        "GLOBAL_VARIABLE": set(),
    }

    entity_kind = entity_kind.upper()
    relationship_kind = relationship_kind.upper()

    if entity_kind not in valid_relationships:
        return (
            False,
            f"Unknown entity kind: '{entity_kind}'. Valid types are: MODULE, CLASS, FUNCTION, FIELD, GLOBAL_VARIABLE",
        )

    all_relationship_kinds = {
        "CONTAINS",
        "HAS_METHOD",
        "HAS_PARAMETER",
        "HAS_FIELD",
        "INHERITS",
    }
    if relationship_kind not in all_relationship_kinds:
        return (
            False,
            f"Unknown relationship kind: '{relationship_kind}'. Valid types are: CONTAINS, HAS_METHOD, HAS_PARAMETER, HAS_FIELD, INHERITS",
        )

    if relationship_kind in valid_relationships[entity_kind]:
        return (True, f"Valid: {entity_kind} can have {relationship_kind} relationship")
    else:
        allowed = valid_relationships[entity_kind]
        if allowed:
            allowed_str = ", ".join(sorted(allowed))
            return (
                False,
                f"Invalid: {entity_kind} cannot have {relationship_kind} relationship. {entity_kind} can only have: {allowed_str}",
            )
        else:
            return (
                False,
                f"Invalid: {entity_kind} cannot have {relationship_kind} relationship. {entity_kind} cannot have any outgoing relationships",
            )
