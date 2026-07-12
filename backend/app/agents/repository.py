from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import GeneratedResourceRecord
from app.agents.schemas import ResourceGenerateResponse


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
    ) -> list[GeneratedResourceRecord]:
        stmt = select(GeneratedResourceRecord).order_by(desc(GeneratedResourceRecord.created_at)).limit(limit)
        if student_id:
            stmt = stmt.where(GeneratedResourceRecord.student_id == student_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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
