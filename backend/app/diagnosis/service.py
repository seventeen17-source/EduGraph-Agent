from app.diagnosis.schemas import DiagnosisRecommendResponse
from app.graph.neo4j_store import Neo4jGraphStore
from app.graphrag.schemas import StudentProfileInput


class DiagnosisService:
    def __init__(self, graph_store: Neo4jGraphStore) -> None:
        self.graph_store = graph_store

    async def recommend(
        self,
        student_profile: StudentProfileInput,
        top_k: int = 5,
    ) -> DiagnosisRecommendResponse:
        recommended_nodes = student_profile.weak_points[:top_k]
        exercise_ids: list[str] = []
        for uid in recommended_nodes:
            exercises = await self.graph_store.get_exercises_for_node(uid, limit=2)
            exercise_ids.extend(exercise.uid for exercise in exercises)
        return DiagnosisRecommendResponse(
            recommended_nodes=recommended_nodes,
            recommended_exercises=exercise_ids[:top_k],
            reasoning=[
                "MVP 阶段根据学生画像 weak_points 推荐知识点。",
                "优先返回与薄弱知识点存在 ASSESSES 关系的练习题。",
            ],
        )
