from typing import Optional

from pydantic import BaseModel, Field


class SearchToolArgs(BaseModel):
    query: str = Field(description="The query to search for in the codebase")


class CodebaseLoaderToolArgs(BaseModel):
    repository: str = Field(
        description="URL of the git repository OR the PyPi package name"
    )


class EntityRelationshipSearchArgs(BaseModel):
    codebase_name: str = Field(description="Name of the codebase to search in")
    entity_name: str = Field(description="Name of the entity to search for")
    entity_kind: str = Field(
        description="Type of entity: MODULE, CLASS, FUNCTION, FIELD, or GLOBAL_VARIABLE"
    )
    relationship_name: str = Field(description="Name of the related entity")
    relationship_type: str = Field(
        description="Type of relationship: CONTAINS, HAS_METHOD, HAS_PARAMETER, HAS_FIELD, or INHERITS"
    )
