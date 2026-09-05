from typing import Dict, Optional


def build_fact(
    source: str, relation: str, target: str, attrs: Dict[str, Optional[str]]
) -> str:
    source_kind = attrs.get("source_kind", "")
    target_kind = attrs.get("target_kind", "")

    # relationship-specific templates
    if relation == "CONTAINS":
        fact = f"{source_kind} {source} contains {target_kind} {target}"
    elif relation == "HAS_METHOD":
        fact = f"{source_kind} {source} has method {target}"
    elif relation == "HAS_FIELD":
        fact = f"{source_kind} {source} has field or attribute or property {target}"
    elif relation == "INHERITS":
        fact = f"{source_kind} {source} inherits from or is a subclass of {target}"
    elif relation == "HAS_PARAMETER":
        fact = f"{source_kind} {source} has parameter or accepts argument {target}"
    else:
        fact = f"{source_kind} {source} {relation} {target_kind} {target}"

    if docstring := attrs.get("docstring"):
        fact += "\n" + docstring.replace("\n", " ").strip()
    if target_docstring := attrs.get("target_docstring"):
        fact += "\n" + target_docstring.replace("\n", " ").strip()
    if source_docstring := attrs.get("source_docstring"):
        fact += "\n" + source_docstring.replace("\n", " ").strip()

    return fact
