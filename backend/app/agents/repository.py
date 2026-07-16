import json
from typing import Any

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import GeneratedResourceRecord
from app.agents.schemas import ResourceGenerateResponse
from app.exercises.models import ExerciseAttempt, ExerciseSession


def _normalize_search_text(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )


class ResourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_generation(
        self,
        *,
        student_id: str,
        resource_types: list[str],
        response: ResourceGenerateResponse,
    ) -> GeneratedResourceRecord:
        center_props = response.center_node.properties if response.center_node else {}
        record = GeneratedResourceRecord(
            student_id=student_id,
            query=response.query,
            resolved_uid=response.resolved_uid or "",
            center_node_name=center_props.get("name") or center_props.get("title") or response.resolved_uid or "",
            resource_types_json=resource_types,
            resources_json=response.resources.model_dump(mode="json"),
            evidence_json=response.evidence.model_dump(mode="json"),
            quality_report_json=response.quality_report.model_dump(mode="json"),
            agent_trace_json=[item.model_dump(mode="json") for item in response.agent_trace],
            quality_score=response.quality_report.score,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def list_generations(
        self,
        *,
        student_id: str | None = None,
        limit: int = 30,
        query: str = "",
    ) -> list[tuple[GeneratedResourceRecord, dict]]:
        """列出资源记录，并附带使用状态统计。

        返回元素为 (record, stats) 元组，stats 包含：
        - related_nodes: list[str]   关联知识点 uid（resolved_uid + 各资源内嵌的 related_node_id / source_uids）
        - is_practiced: bool         该资源是否被练习过
        - practice_accuracy: float | None  练习正确率（已练习时为 0-1 浮点数）
        """
        fetch_limit = max(limit, 200) if query.strip() else limit
        stmt = select(GeneratedResourceRecord).order_by(desc(GeneratedResourceRecord.created_at)).limit(fetch_limit)
        if student_id:
            stmt = stmt.where(GeneratedResourceRecord.student_id == student_id)
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        q = _normalize_search_text(query)
        if q:
            matches: list[GeneratedResourceRecord] = []
            for record in records:
                haystack = _normalize_search_text(" ".join([
                    record.query or "",
                    record.resolved_uid or "",
                    record.center_node_name or "",
                    " ".join(record.resource_types_json or []),
                    json.dumps(record.resources_json or {}, ensure_ascii=False),
                ]))
                if q in haystack:
                    matches.append(record)
                if len(matches) >= limit:
                    break
            records = matches

        stats_map = self._extract_related_nodes(records)
        practice_stats = await self._compute_practice_stats(list(stats_map.keys()))
        for rid, pstats in practice_stats.items():
            stats_map.setdefault(rid, {"related_nodes": [], "is_practiced": False, "practice_accuracy": None})
            stats_map[rid].update(pstats)
        return [(record, stats_map.get(record.id, {"related_nodes": [], "is_practiced": False, "practice_accuracy": None})) for record in records]

    @staticmethod
    def _extract_related_nodes(records: list[GeneratedResourceRecord]) -> dict[str, dict]:
        """从 resources_json 中提取每个资源关联的知识点 uid 列表。"""
        stats_map: dict[str, dict] = {}
        for record in records:
            related: list[str] = []
            if record.resolved_uid:
                related.append(record.resolved_uid)
            resources = dict(record.resources_json or {})
            for ex in (resources.get("exercises") or []):
                if isinstance(ex, dict):
                    node_id = ex.get("related_node_id")
                    if node_id and node_id not in related:
                        related.append(node_id)
            code_case = resources.get("code_case")
            if isinstance(code_case, dict):
                node_id = code_case.get("related_node_id")
                if node_id and node_id not in related:
                    related.append(node_id)
            for key in ("document", "mindmap", "video_script", "image"):
                item = resources.get(key)
                if isinstance(item, dict):
                    for uid in (item.get("source_uids") or []):
                        if uid and uid not in related:
                            related.append(uid)
            stats_map[record.id] = {
                "related_nodes": related,
                "is_practiced": False,
                "practice_accuracy": None,
            }
        return stats_map

    async def _compute_practice_stats(self, resource_ids: list[str]) -> dict[str, dict]:
        """批量查询每个 resource_id 下的练习作答情况。

        通过 ExerciseSession.source_id = resource_id 关联（前端从知识中心
        或助手启动练习时，会将 source_id 设为资源记录 id）。
        """
        if not resource_ids:
            return {}
        stmt = (
            select(
                ExerciseSession.source_id.label("resource_id"),
                func.count(ExerciseAttempt.id).label("total"),
                func.sum(case((ExerciseAttempt.is_correct.is_(True), 1), else_=0)).label("correct"),
            )
            .join(ExerciseAttempt, ExerciseAttempt.session_id == ExerciseSession.id)
            .where(ExerciseSession.source_id.in_(resource_ids))
            .group_by(ExerciseSession.source_id)
        )
        rows = await self.session.execute(stmt)
        stats_map: dict[str, dict] = {}
        for row in rows:
            rid = row.resource_id
            total = int(row.total or 0)
            correct = int(row.correct or 0)
            stats_map[rid] = {
                "is_practiced": total > 0,
                "practice_accuracy": round(correct / total, 4) if total > 0 else None,
            }
        return stats_map

    async def get_generation(self, resource_id: str) -> GeneratedResourceRecord | None:
        return await self.session.get(GeneratedResourceRecord, resource_id)

    async def update_mindmap(
        self,
        resource_id: str,
        *,
        title: str | None,
        content: str,
    ) -> GeneratedResourceRecord | None:
        record = await self.get_generation(resource_id)
        if record is None:
            return None
        resources = dict(record.resources_json or {})
        mindmap = dict(resources.get("mindmap") or {})
        mindmap["content"] = content
        if title is not None:
            mindmap["title"] = title
        if not mindmap.get("format"):
            mindmap["format"] = "mermaid"
        resources["mindmap"] = mindmap
        record.resources_json = resources
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def update_single_resource(
        self,
        resource_id: str,
        *,
        field: str,
        value: Any,
    ) -> GeneratedResourceRecord | None:
        """更新单类资源字段（document/mindmap/exercises/video_script/code_case）。"""
        record = await self.get_generation(resource_id)
        if record is None:
            return None
        resources = dict(record.resources_json or {})
        resources[field] = value
        record.resources_json = resources
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def update_generation_after_retry(
        self,
        resource_id: str,
        *,
        field: str,
        value: Any,
        quality_report: dict,
        agent_trace: list[dict],
        quality_score: float,
    ) -> GeneratedResourceRecord | None:
        """Update one regenerated resource and keep trace/quality in sync."""
        record = await self.get_generation(resource_id)
        if record is None:
            return None
        resources = dict(record.resources_json or {})
        resources[field] = value
        record.resources_json = resources
        record.quality_report_json = quality_report
        record.agent_trace_json = agent_trace
        record.quality_score = quality_score
        await self.session.commit()
        await self.session.refresh(record)
        return record
