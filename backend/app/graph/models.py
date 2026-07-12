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


class DependencyPath(BaseModel):
    """一条完整的多跳前置依赖路径。

    例如：ml_partial_derivative → ml_chain_rule → ml_backpropagation
    表示：偏导数 → 链式法则 → 反向传播
    """
    path_nodes: list[str] = Field(default_factory=list)          # ["ml_partial_derivative", "ml_chain_rule", "ml_backpropagation"]
    path_labels: list[str] = Field(default_factory=list)         # ["偏导数", "链式法则", "反向传播"]
    depth: int = 1                                                # 跳数（边数）
    reasoning: str = ""                                           # 自然语言推理说明
    intermediate_evidence: dict[str, dict] = Field(default_factory=dict)  # {node_id: {has_doc, has_code, has_exercise, ...}}


class MultiHopSummary(BaseModel):
    """多跳依赖分析摘要。"""
    center_node_id: str = ""
    total_dependencies: int = 0
    max_depth_found: int = 0
    dependency_paths: list[DependencyPath] = Field(default_factory=list)
    # 按深度分组
    direct_prerequisites: list[str] = Field(default_factory=list)     # 1-hop
    transitive_prerequisites: list[str] = Field(default_factory=list)  # 2+-hop
    # 推理链（供 prompt 使用）
    reasoning_chain: list[str] = Field(default_factory=list)
