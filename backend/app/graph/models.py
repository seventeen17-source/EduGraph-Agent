from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    uid: str
    labels: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphRelationship(BaseModel):
    type: str
    source_uid: str
    target_uid: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphPath(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    relationships: list[GraphRelationship] = Field(default_factory=list)


class SubgraphResult(BaseModel):
    center_uid: str
    nodes: list[GraphNode] = Field(default_factory=list)
    relationships: list[GraphRelationship] = Field(default_factory=list)
    paths: list[GraphPath] = Field(default_factory=list)
