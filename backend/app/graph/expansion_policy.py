from pydantic import BaseModel, Field


COGNITIVE_RELATIONS = ["PREREQUISITE", "RELATED", "EXTENDS", "CONTRASTS"]
RESOURCE_RELATIONS = ["ASSESSES", "SUPPORTS", "PRACTICES"]
SOURCE_RELATIONS = ["CITES_SOURCE"]
STRUCTURE_RELATIONS = ["CONTAINS"]
BLOCKED_EXPANSION_RELATIONS = [
    "HAS_CHAPTER",
    "HAS_KNOWLEDGE_POINT",
    "HAS_DOCUMENT",
    "HAS_CHUNK",
    "HAS_EXERCISE",
    "TRACKS_CHAPTER",
]


class GraphExpansionPolicy(BaseModel):
    """Controls GraphRAG subgraph expansion and evidence limits."""

    depth: int = 2  # 默认 2-hop（支持多跳推理）
    max_prerequisites: int = 12  # 多跳场景需要更多前置节点
    max_related_nodes: int = 8
    max_exercises: int = 8
    max_document_chunks: int = 8  # 多跳收集更多文档
    max_code_cases: int = 5       # 多跳收集更多代码案例
    max_sources: int = 10
    max_subgraph_items: int = 120
    multi_hop_enabled: bool = True
    max_hop_depth: int = 3  # 最多 3 跳
    collect_intermediate_evidence: bool = True  # 是否收集中间节点的证据
    cognitive_relations: list[str] = Field(default_factory=lambda: COGNITIVE_RELATIONS.copy())
    resource_relations: list[str] = Field(default_factory=lambda: RESOURCE_RELATIONS.copy())
    source_relations: list[str] = Field(default_factory=lambda: SOURCE_RELATIONS.copy())

    @property
    def graphrag_relations(self) -> list[str]:
        return self.cognitive_relations + self.resource_relations

    def clamp_depth(self, max_depth: int = 2) -> int:
        return max(1, min(self.depth, max_depth))
