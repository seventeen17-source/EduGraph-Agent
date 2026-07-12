import asyncio

from app.agents.resource_agents import LangChainResourceAgents
from app.agents.schemas import (
    AgentTraceItem,
    GeneratedResources,
    QualityReport,
    ResourceCenterDetail,
    ResourceCenterItem,
    ResourceCenterListResponse,
    ResourceMindmapUpdateRequest,
    ResourceGenerateRequest,
    ResourceGenerateResponse,
)
from app.core.config import Settings
from app.core.errors import ServiceUnavailableError
from app.graphrag.schemas import EvidencePackage, StudentProfileInput
from app.graphrag.service import GraphRAGService
from app.agents.repository import ResourceRepository


class ResourceGenerationService:
    """Coordinates GraphRAG evidence retrieval and LangChain resource agents."""

    def __init__(
        self,
        graphrag_service: GraphRAGService,
        settings: Settings,
        repository: ResourceRepository | None = None,
    ) -> None:
        self.graphrag_service = graphrag_service
        self.settings = settings
        self.repository = repository
        self.resource_agents = LangChainResourceAgents(settings)

    async def generate(self, payload: ResourceGenerateRequest) -> ResourceGenerateResponse:
        if not self.settings.llm_api_key:
            raise ServiceUnavailableError(
                "LLM_API_KEY is required for LangChain resource generation."
            )

        profile = payload.student_profile
        if profile is None or not isinstance(profile, StudentProfileInput):
            profile = StudentProfileInput()
        trace: list[AgentTraceItem] = []

        if payload.node_id:
            evidence = await self.graphrag_service.build_evidence_by_uid(payload.node_id, profile)
            trace.append(
                AgentTraceItem(
                    agent="RetrievalAgent",
                    status="done",
                    summary=f"uid={payload.node_id} 直接检索，无需解析",
                )
            )
        else:
            evidence = await self.graphrag_service.query(payload.query or "梯度下降", profile)
            trace.append(
                AgentTraceItem(
                    agent="RetrievalAgent",
                    status="done" if evidence.center_node is not None else "failed",
                    summary=(
                        f"resolved_uid={evidence.resolved_uid}"
                        if evidence.center_node is not None
                        else "未能定位中心知识点"
                    ),
                )
            )

        resources = GeneratedResources()
        if evidence.center_node is None:
            # 无匹配 → 返回空资源 + 建议
            alternatives = await self._collect_alternatives(payload.query or "")
            return self._response(payload, evidence, resources, trace,
                                  resolution_quality="none",
                                  suggested_alternatives=alternatives,
                                  resolution_notice=self._build_notice("none", evidence, alternatives))

        resource_types = list(dict.fromkeys(payload.resource_types))

        async def safe_run(agent_name: str, coro):
            try:
                result = await coro
                trace.append(AgentTraceItem(agent=agent_name, status="done", summary=f"生成{agent_name}"))
                return result
            except Exception as exc:
                import traceback
                traceback.print_exc()
                trace.append(
                    AgentTraceItem(
                        agent=agent_name,
                        status="failed",
                        summary=f"生成{agent_name}失败: {type(exc).__name__}: {exc}",
                    )
                )
                return None

        tasks: dict[str, Any] = {}
        if "document" in resource_types:
            tasks["document"] = safe_run("DocumentAgent", self.resource_agents.generate_document(evidence, profile))
        if "mindmap" in resource_types:
            tasks["mindmap"] = safe_run("MindmapAgent", self.resource_agents.generate_mindmap(evidence, profile))
        if "exercise" in resource_types:
            tasks["exercise"] = safe_run(
                "ExerciseAgent",
                self.resource_agents.generate_exercises(
                    evidence,
                    profile,
                    count=payload.exercise_count or 3,
                    exercise_type=payload.exercise_type,
                ),
            )
        if "video_script" in resource_types:
            tasks["video_script"] = safe_run("VideoScriptAgent", self.resource_agents.generate_video_script(evidence, profile))
        if "code_case" in resource_types:
            tasks["code_case"] = safe_run("CodeAgent", self.resource_agents.generate_code_case(evidence, profile))

        _FIELD_MAP = {
            "document": "document",
            "mindmap": "mindmap",
            "exercise": "exercises",
            "video_script": "video_script",
            "code_case": "code_case",
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=False)
        for key, result in zip(tasks.keys(), results):
            field = _FIELD_MAP.get(key, key)
            # ExerciseAgent 返回 GeneratedExercises，需提取 .items
            if key == "exercise" and hasattr(result, "items"):
                result = result.items or []
            setattr(resources, field, result)

        resolution_quality = evidence.resolution_quality or "exact"
        response = self._response(
            payload, evidence, resources, trace,
            resolution_quality=resolution_quality,
            suggested_alternatives=evidence.suggested_alternatives or [],
        )
        if self.repository is not None and response.center_node is not None:
            record = await self.repository.save_generation(
                student_id=payload.student_id or "",
                resource_types=resource_types,
                response=response,
            )
            response.resource_record_id = record.id
        return response

    async def list_center_items(self, student_id: str | None = None, limit: int = 30) -> ResourceCenterListResponse:
        if self.repository is None:
            return ResourceCenterListResponse()
        records = await self.repository.list_generations(student_id=student_id, limit=limit)
        return ResourceCenterListResponse(
            items=[
                ResourceCenterItem(
                    id=record.id,
                    student_id=record.student_id,
                    query=record.query,
                    resolved_uid=record.resolved_uid,
                    center_node_name=record.center_node_name,
                    resource_types=record.resource_types_json or [],
                    quality_score=record.quality_score,
                    created_at=record.created_at.isoformat(),
                )
                for record in records
            ]
        )

    async def get_center_detail(self, resource_id: str) -> ResourceCenterDetail | None:
        if self.repository is None:
            return None
        record = await self.repository.get_generation(resource_id)
        if record is None:
            return None
        return ResourceCenterDetail(
            id=record.id,
            student_id=record.student_id,
            query=record.query,
            resolved_uid=record.resolved_uid,
            center_node_name=record.center_node_name,
            resource_types=record.resource_types_json or [],
            resources=GeneratedResources.model_validate(record.resources_json or {}),
            evidence=EvidencePackage.model_validate(record.evidence_json or {}),
            quality_report=QualityReport.model_validate(record.quality_report_json or {}),
            agent_trace=[AgentTraceItem.model_validate(item) for item in record.agent_trace_json or []],
            quality_score=record.quality_score,
            created_at=record.created_at.isoformat(),
        )

    async def update_center_mindmap(
        self,
        resource_id: str,
        payload: ResourceMindmapUpdateRequest,
    ) -> ResourceCenterDetail | None:
        if self.repository is None:
            return None
        record = await self.repository.update_mindmap(
            resource_id,
            title=payload.title,
            content=payload.content,
        )
        if record is None:
            return None
        return await self.get_center_detail(resource_id)

    def _response(
        self,
        payload: ResourceGenerateRequest,
        evidence: EvidencePackage,
        resources: GeneratedResources,
        trace: list[AgentTraceItem],
        resolution_quality: str = "exact",
        suggested_alternatives: list[dict] | None = None,
        resolution_notice: str = "",
    ) -> ResourceGenerateResponse:
        quality_report = self._quality_report(evidence, resources)
        trace.append(
            AgentTraceItem(
                agent="QualityAgent",
                status="done",
                summary=f"grounded={quality_report.grounded}, score={quality_report.score:.2f}",
            )
        )
        # 从 evidence 中继承解析质量（如果调用方未显式传入）
        if resolution_quality == "exact" and evidence.resolution_quality != "exact":
            resolution_quality = evidence.resolution_quality
        if not suggested_alternatives:
            suggested_alternatives = evidence.suggested_alternatives or []
        if not resolution_notice:
            resolution_notice = self._build_notice(
                resolution_quality, evidence, suggested_alternatives or [],
            )
        return ResourceGenerateResponse(
            resource_record_id=None,
            query=payload.query,
            resolved_uid=evidence.resolved_uid,
            center_node=evidence.center_node,
            evidence=evidence,
            resources=resources,
            quality_report=quality_report,
            agent_trace=trace,
            uncertainty=evidence.uncertainty,
            missing_evidence=evidence.missing_evidence,
            resolution_quality=resolution_quality,
            suggested_alternatives=suggested_alternatives or [],
            resolution_notice=resolution_notice,
        )

    async def _collect_alternatives(self, query: str, limit: int = 5) -> list[dict]:
        """收集建议的备选知识点。"""
        keywords = query.replace("的", " ").replace("是", " ").split()
        candidates: list[dict] = []
        seen: set[str] = set()
        for kw in keywords:
            if len(kw) < 2:
                continue
            nodes = await self.graphrag_service.graph_store.search_knowledge_points(kw, limit=3)
            for node in nodes:
                if node.uid not in seen:
                    seen.add(node.uid)
                    name = node.properties.get("name") or node.uid
                    candidates.append({
                        "uid": node.uid,
                        "name": str(name),
                        "reason": f"与'{kw}'相关的知识点",
                    })
        return candidates[:limit]

    @staticmethod
    def _build_notice(
        resolution_quality: str,
        evidence: EvidencePackage,
        alternatives: list[dict],
    ) -> str:
        """生成给用户看的解析说明。"""
        if resolution_quality == "none":
            msg = "未能找到与你的查询精确匹配的知识点。"
            if alternatives:
                names = "、".join(a["name"] for a in alternatives[:5])
                msg += f" 你可以尝试以下知识点：{names}。也可以换个更具体的关键词重试。"
            else:
                msg += " 请尝试输入更具体的知识点名称（如'梯度下降''反向传播'等）。"
            return msg
        if resolution_quality == "fallback":
            center_name = ""
            if evidence.center_node:
                center_name = str(evidence.center_node.properties.get("name") or evidence.resolved_uid or "")
            msg = f"你的查询未精确匹配到知识点，已为你匹配最接近的「{center_name}」。"
            if alternatives:
                names = "、".join(a["name"] for a in alternatives[:3])
                msg += f" 其他可能相关的知识点：{names}。"
            msg += " 如果这不是你想要的，请尝试更精确的关键词。"
            return msg
        return ""

    def _quality_report(
        self,
        evidence: EvidencePackage,
        resources: GeneratedResources,
    ) -> QualityReport:
        warnings: list[str] = []
        source_uids = [source.uid for source in evidence.sources]
        if evidence.center_node is None:
            warnings.append("未定位到中心知识点，资源生成已跳过。")
        if not evidence.document_chunks:
            warnings.append("证据包缺少讲义 chunk，生成内容主要依赖图谱属性、题目和来源。")
        if not source_uids:
            warnings.append("证据包缺少来源节点。")
        generated_count = 0

        # per-resource quality checks
        if resources.document is not None:
            if len(resources.document.content or "") < 50:
                warnings.append("DocumentAgent: 讲解文档内容过短（< 50 字），可能为低质量或空生成。")
            if not resources.document.source_uids:
                warnings.append("DocumentAgent: 讲解文档未标注引用来源。")
            generated_count += 1

        if resources.mindmap is not None:
            if not (resources.mindmap.content or "").strip().startswith(("mindmap", "graph", "flowchart")):
                warnings.append("MindmapAgent: 思维导图内容可能不是有效 Mermaid 格式。")
            generated_count += 1

        if resources.exercises:
            for ex in resources.exercises:
                if not ex.answer or not ex.question:
                    warnings.append(f"ExerciseAgent: 题目 {ex.title} 缺少问题或答案。")
            generated_count += 1

        if resources.video_script is not None:
            if len(resources.video_script.scenes) < 2:
                warnings.append("VideoScriptAgent: 视频脚本分镜数不足 2 个。")
            generated_count += 1

        if resources.code_case is not None:
            code = resources.code_case.code or ""
            if len(code) < 20:
                warnings.append("CodeAgent: 代码案例过短（< 20 字符），可能无效。")
            elif not any(kw in code for kw in ("def", "import", "class", "print", "=")):
                warnings.append("CodeAgent: 代码案例可能不含可执行语句，请人工复查。")
            generated_count += 1

        if generated_count == 0:
            warnings.append("未生成任何学习资源。")

        score = 0.2
        score += 0.2 if evidence.center_node is not None else 0.0
        score += 0.2 if evidence.document_chunks else 0.0
        score += 0.1 if source_uids else 0.0
        score += min(generated_count, 5) * 0.1
        score = min(score, 1.0)
        return QualityReport(
            grounded=evidence.center_node is not None and bool(source_uids),
            score=score,
            warnings=warnings,
            source_uids=source_uids,
        )
