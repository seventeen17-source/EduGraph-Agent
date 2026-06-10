from app.core.config import get_settings
from app.graph.expansion_policy import GraphExpansionPolicy
from app.graph.llm_resolver import build_llm_resolver_client
from app.graph.neo4j_store import Neo4jGraphStore
from app.graph.node_resolver import NodeResolver
from app.graphrag.evidence_retriever import EvidenceRetriever
from app.graphrag.schemas import EvidencePackage, StudentProfileInput


class GraphRAGService:
    def __init__(self, graph_store: Neo4jGraphStore) -> None:
        self.graph_store = graph_store
        self.policy = GraphExpansionPolicy()
        self.node_resolver = NodeResolver(
            graph_store,
            llm_client=build_llm_resolver_client(get_settings()),
        )
        self.evidence_retriever = EvidenceRetriever(graph_store, self.policy)

    async def build_evidence_by_uid(
        self,
        uid: str,
        student_profile: StudentProfileInput | None = None,
    ) -> EvidencePackage:
        return await self.evidence_retriever.retrieve(
            query=uid,
            center_uid=uid,
            student_profile=student_profile,
        )

    async def query(
        self,
        query_text: str,
        student_profile: StudentProfileInput | None = None,
    ) -> EvidencePackage:
        profile = student_profile or StudentProfileInput()
        resolution = await self.node_resolver.resolve(query_text, profile.weak_points)
        if resolution.resolved_uid is None:
            return EvidencePackage(
                query=query_text,
                uncertainty=resolution.uncertainty,
                missing_evidence=["resolved_center_node"],
            )

        evidence = await self.evidence_retriever.retrieve(
            query=query_text,
            center_uid=resolution.resolved_uid,
            student_profile=profile,
        )
        evidence.uncertainty.extend(resolution.uncertainty)
        evidence.student_profile_adaptation["node_resolution"] = {
            "normalized_query": resolution.normalized_query,
            "intent": resolution.intent,
            "candidate_uids": [node.uid for node in resolution.candidates],
            "llm_understanding": (
                resolution.llm_understanding.model_dump()
                if resolution.llm_understanding is not None
                else None
            ),
        }
        return evidence
