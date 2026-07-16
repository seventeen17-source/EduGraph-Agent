import asyncio
from typing import Any

from app.agents.resource_agents import LangChainResourceAgents
from app.agents.schemas import (
    AgentTraceItem,
    GeneratedDocument,
    GeneratedImage,
    GeneratedResources,
    QualityReport,
    ResourceCenterDetail,
    ResourceCenterItem,
    ResourceCenterListResponse,
    ResourceMindmapUpdateRequest,
    ResourceGenerateRequest,
    ResourceGenerateResponse,
    ResourceType,
)
from app.core.config import Settings
from app.core.errors import ServiceUnavailableError
from app.core.labels import choose_node_label
from app.core.logging import log_business_metric
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
                    summary=f"按指定知识点「{payload.node_id}」直接检索，无需再次解析。",
                )
            )
            if evidence.center_node is None and payload.query:
                evidence = await self.graphrag_service.query(
                    payload.query,
                    profile,
                    student_id=payload.student_id,
                )
                trace.append(
                    AgentTraceItem(
                        agent="RetrievalAgent",
                        status="done" if evidence.center_node is not None else "failed",
                        summary=(
                            f"指定知识点未命中，已改用原始问题定位到「{self._center_node_name(evidence)}」。"
                            if evidence.center_node is not None
                            else "指定知识点未命中，原始问题也未能定位中心知识点。"
                        ),
                    )
                )
        else:
            evidence = await self.graphrag_service.query(payload.query or "梯度下降", profile)
            trace.append(
                AgentTraceItem(
                    agent="RetrievalAgent",
                    status="done" if evidence.center_node is not None else "failed",
                    summary=(
                        f"已定位中心知识点「{self._center_node_name(evidence)}」。"
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
        embed_document_images = self._should_embed_document_images(payload.query, resource_types)

        async def safe_run(agent_name: str, coro):
            try:
                result = await coro
                validation_error = self._resource_validation_error(agent_name, result)
                if validation_error:
                    trace.append(
                        AgentTraceItem(
                            agent=agent_name,
                            status="failed",
                            summary=f"{self._agent_label(agent_name)}未通过校验：{validation_error}",
                        )
                    )
                    return None

                summary = f"{self._agent_label(agent_name)}已生成并通过校验"
                if agent_name == "ExerciseAgent":
                    meta = getattr(self.resource_agents, "last_exercise_generation_trace", {}) or {}
                    mode = meta.get("mode")
                    repairs = meta.get("repair_attempts")
                    fallback = meta.get("fallback_used")
                    if mode:
                        mode_label = {
                            "llm": "大模型直接生成",
                            "llm_repaired": "大模型自修复后生成",
                            "fallback": "最终兜底生成",
                        }.get(str(mode), str(mode))
                        fallback_label = "是" if fallback else "否"
                        summary += f"；生成方式：{mode_label}，修复次数：{repairs or 0}，是否兜底：{fallback_label}"
                    issues = meta.get("issues") or []
                    if issues:
                        summary += f"；质量问题：{'；'.join(str(item) for item in issues[:3])}"
                trace.append(AgentTraceItem(agent=agent_name, status="done", summary=summary))
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
        if "image" in resource_types and not embed_document_images:
            tasks["image"] = safe_run("ImageAgent", self.resource_agents.generate_image(evidence, profile, mode="standalone"))

        _FIELD_MAP = {
            "document": "document",
            "mindmap": "mindmap",
            "exercise": "exercises",
            "video_script": "video_script",
            "code_case": "code_case",
            "image": "image",
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=False)
        for key, result in zip(tasks.keys(), results):
            field = _FIELD_MAP.get(key, key)
            # ExerciseAgent 返回 GeneratedExercises，需提取 .items
            if key == "exercise" and hasattr(result, "items"):
                result = result.items or []
            if key == "exercise" and result is None:
                result = []
            setattr(resources, field, result)

        if embed_document_images and resources.document is not None:
            illustrations: list[GeneratedImage] = []
            illustration_count = self._document_illustration_count(payload.query)
            for index in range(illustration_count):
                focus_hint = self._document_illustration_focus(index, illustration_count, evidence)
                image = await safe_run(
                    "ImageAgent",
                    self.resource_agents.generate_image(
                        evidence,
                        profile,
                        mode="document_illustration",
                        focus_hint=focus_hint,
                    ),
                )
                if image is not None:
                    illustrations.append(image)
            if illustrations:
                resources.document.illustrations = illustrations
                self._insert_document_illustrations(resources.document, illustrations)

        resolution_quality = evidence.resolution_quality or "exact"
        response = self._response(
            payload, evidence, resources, trace,
            resolution_quality=resolution_quality,
            suggested_alternatives=evidence.suggested_alternatives or [],
        )
        has_generated_resource = self._has_generated_resource(response.resources)
        if not has_generated_resource:
            response.generation_status = "failed"
            response.agent_trace.append(
                AgentTraceItem(
                    agent="ResourceGenerationService",
                    status="failed",
                    summary="所有请求的资源都没有生成有效内容，已阻止写入资源中心。",
                )
            )
            response.quality_report.warnings.append("未生成有效资源，本轮结果未写入资源中心。")
        if self.repository is not None and response.center_node is not None and has_generated_resource:
            record = await self.repository.save_generation(
                student_id=payload.student_id or "",
                resource_types=resource_types,
                response=response,
            )
            response.resource_record_id = record.id
        # 业务指标：资源生成成功率
        _resource_agent_names = {"DocumentAgent", "MindmapAgent", "ExerciseAgent", "VideoScriptAgent", "CodeAgent", "ImageAgent"}
        _agent_statuses = {item.agent: item.status for item in trace if item.agent in _resource_agent_names}
        _success_count = sum(1 for s in _agent_statuses.values() if s == "done")
        _total_count = len(_agent_statuses)
        if _total_count > 0:
            log_business_metric(
                "resource_generation_success_rate",
                round(_success_count / _total_count, 4),
                total=_total_count, success=_success_count,
            )
        return response

    async def list_center_items(
        self,
        student_id: str | None = None,
        limit: int = 30,
        query: str = "",
        filter_by_weak_points: bool = False,
        weak_points: list[str] | None = None,
    ) -> ResourceCenterListResponse:
        if self.repository is None:
            return ResourceCenterListResponse()
        tuples = await self.repository.list_generations(student_id=student_id, limit=limit, query=query)
        items: list[ResourceCenterItem] = []
        weak_set = set(weak_points or [])
        for record, stats in tuples:
            resources = self._parse_generated_resources(record.resources_json)
            if not self._has_generated_resource(resources):
                continue
            related_nodes = list(stats.get("related_nodes") or [])
            # 按薄弱点筛选：资源关联的节点必须命中 weak_points
            if filter_by_weak_points and weak_set:
                if not any(uid in weak_set for uid in related_nodes):
                    continue
            items.append(
                ResourceCenterItem(
                    id=record.id,
                    student_id=record.student_id,
                    query=record.query,
                    resolved_uid=record.resolved_uid,
                    center_node_name=record.center_node_name,
                    resource_types=record.resource_types_json or [],
                    quality_score=record.quality_score,
                    created_at=record.created_at.isoformat(),
                    related_nodes=related_nodes,
                    is_practiced=bool(stats.get("is_practiced")),
                    practice_accuracy=stats.get("practice_accuracy"),
                    source="resource_generation",
                )
            )
        return ResourceCenterListResponse(items=items)

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
            resources=self._parse_generated_resources(record.resources_json),
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

    async def retry_single_type(
        self,
        resource_id: str,
        resource_type: str,
        student_id: str,
    ) -> dict:
        """单独重试某类资源。"""
        if not self.settings.llm_api_key:
            raise ServiceUnavailableError(
                "LLM_API_KEY is required for resource retry."
            )
        if self.repository is None:
            return {"success": False, "error": "仓储不可用"}

        # 1. 从数据库获取原资源记录
        record = await self.repository.get_generation(resource_id)
        if record is None:
            return {"success": False, "error": "资源记录不存在"}

        # 2. 加载原 evidence，重新生成指定类型的资源
        evidence = EvidencePackage.model_validate(record.evidence_json or {})
        profile = StudentProfileInput()

        field_map = {
            "document": "document",
            "mindmap": "mindmap",
            "exercise": "exercises",
            "video_script": "video_script",
            "code_case": "code_case",
            "image": "image",
        }
        agent_map = {
            "document": "DocumentAgent",
            "mindmap": "MindmapAgent",
            "exercise": "ExerciseAgent",
            "video_script": "VideoScriptAgent",
            "code_case": "CodeAgent",
            "image": "ImageAgent",
        }
        field = field_map.get(resource_type)
        agent_name = agent_map.get(resource_type)
        if field is None:
            return {"success": False, "error": f"不支持的资源类型: {resource_type}"}

        # 3. 仅重新生成指定类型的资源
        try:
            if resource_type == "document":
                new_resource = await self.resource_agents.generate_document(evidence, profile)
                new_value = new_resource.model_dump(mode="json")
            elif resource_type == "mindmap":
                new_resource = await self.resource_agents.generate_mindmap(evidence, profile)
                new_value = new_resource.model_dump(mode="json")
            elif resource_type == "exercise":
                new_items = await self.resource_agents.generate_exercises(evidence, profile)
                validation_error = self._resource_validation_error(agent_name or "ExerciseAgent", new_items)
                if validation_error:
                    return {"success": False, "error": validation_error}
                items = new_items.items if hasattr(new_items, "items") else new_items
                new_value = [item.model_dump(mode="json") for item in (items or [])]
            elif resource_type == "video_script":
                new_resource = await self.resource_agents.generate_video_script(evidence, profile)
                new_value = new_resource.model_dump(mode="json")
            elif resource_type == "code_case":
                new_resource = await self.resource_agents.generate_code_case(evidence, profile)
                new_value = new_resource.model_dump(mode="json")
            elif resource_type == "image":
                new_resource = await self.resource_agents.generate_image(evidence, profile)
                new_value = new_resource.model_dump(mode="json")
            else:
                return {"success": False, "error": f"不支持的资源类型: {resource_type}"}
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": f"重新生成失败: {type(exc).__name__}: {exc}"}

        if resource_type != "exercise":
            validation_error = self._resource_validation_error(agent_name or "", new_resource)
            if validation_error:
                return {"success": False, "error": validation_error}

        # 4. 同步更新资源、质量报告和该 Agent 的 trace
        resources = self._parse_generated_resources(record.resources_json)
        setattr(resources, field, (items or []) if resource_type == "exercise" else new_resource)
        quality_report = self._quality_report(evidence, resources)
        trace_items = [AgentTraceItem.model_validate(item) for item in record.agent_trace_json or []]
        trace_item = AgentTraceItem(
            agent=agent_name or field,
            status="done",
            summary=f"{self._agent_label(agent_name or field)}重试成功，结果已生成并通过校验",
        )
        replaced = False
        for index, item in enumerate(trace_items):
            if item.agent == trace_item.agent:
                trace_items[index] = trace_item
                replaced = True
                break
        if not replaced:
            trace_items.append(trace_item)

        updated_record = await self.repository.update_generation_after_retry(
            resource_id,
            field=field,
            value=new_value,
            quality_report=quality_report.model_dump(mode="json"),
            agent_trace=[item.model_dump(mode="json") for item in trace_items],
            quality_score=quality_report.score,
        )
        if updated_record is None:
            return {"success": False, "error": "更新数据库失败"}

        # 5. 返回新的资源结果
        return {
            "success": True,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "student_id": student_id,
            "field": field,
            "resource": new_value,
            "agent_trace": [item.model_dump(mode="json") for item in trace_items],
            "quality_report": quality_report.model_dump(mode="json"),
        }

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
                summary=(
                    f"证据扎根：{'是' if quality_report.grounded else '否'}，"
                    f"综合质量分：{quality_report.score:.2f}"
                ),
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
            generation_status=self._generation_status(payload.resource_types, resources),
            success_types=self._generated_resource_types(resources),
            failed_types=self._failed_resource_types(payload.resource_types, resources),
            uncertainty=evidence.uncertainty,
            missing_evidence=evidence.missing_evidence,
            resolution_quality=resolution_quality,
            suggested_alternatives=suggested_alternatives or [],
            resolution_notice=resolution_notice,
        )

    @staticmethod
    def _should_embed_document_images(query: str, resource_types: list[ResourceType]) -> bool:
        if "document" not in resource_types or "image" not in resource_types:
            return False
        text = str(query or "")
        inline_image_terms = (
            "配图", "插图", "图文", "带图", "加图", "加一张图", "加几张图",
            "穿插图片", "穿插图", "文中", "文档里", "讲解文档", "讲义", "多一些图",
            "多点图", "多张图", "几张图", "最好有图", "带一些图",
        )
        if any(term in text for term in inline_image_terms):
            return True
        return set(resource_types) == {"document", "image"}

    @staticmethod
    def _document_illustration_count(query: str) -> int:
        text = str(query or "")
        multi_terms = ("多一些图", "多点图", "多张图", "几张图", "两张图", "2张图", "二张图", "带一些图")
        return 2 if any(term in text for term in multi_terms) else 1

    def _document_illustration_focus(
        self,
        index: int,
        total: int,
        evidence: EvidencePackage,
    ) -> str:
        topic = self._center_node_name(evidence)
        if total <= 1:
            return (
                f"围绕“{topic}”做一张段落级教学插图，重点表现核心机制和关键关系，"
                "画面必须和主题直接相关，不要生成泛泛的科技背景。"
            )
        if index == 0:
            return (
                f"第 1 张图用于文档前半部分，做“{topic}”的整体流程概览，"
                "强调主要对象之间的方向、层级或数据流关系。"
            )
        return (
            f"第 {index + 1} 张图用于文档后半部分，表现“{topic}”中最容易混淆的局部机制，"
            "例如方向变化、参数更新、误差信号传递或前后对比，避免与第 1 张图重复。"
        )

    @staticmethod
    def _insert_document_illustrations(
        document: GeneratedDocument,
        illustrations: list[GeneratedImage],
    ) -> None:
        image_blocks: list[str] = []
        existing_content = document.content or ""
        for image in illustrations:
            image_src = image.image_url or image.local_path
            if not image_src or image_src in existing_content:
                continue
            title = image.title or "教学插图"
            image_blocks.append(f"![{title}]({image_src})\n\n*图：{title}*")
        if not image_blocks:
            return

        lines = existing_content.strip().splitlines()
        if not lines:
            document.content = "\n\n".join(image_blocks)
            return

        insert_at = len(lines)
        passed_title = False
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                if passed_title:
                    insert_at = idx + 1
                    break
                continue
            if stripped.startswith("#"):
                passed_title = True
                continue
            insert_at = idx + 1
            while insert_at < len(lines) and lines[insert_at].strip():
                insert_at += 1
            break

        block_lines = ["", *"\n\n".join(image_blocks).splitlines(), ""]
        lines[insert_at:insert_at] = block_lines
        document.content = "\n".join(lines).strip() + "\n"

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
                    name = choose_node_label(node.properties.get("name"), node.uid)
                    candidates.append({
                        "uid": node.uid,
                        "name": str(name),
                        "reason": f"与'{kw}'相关的知识点",
                    })
        return candidates[:limit]

    @staticmethod
    def _agent_label(agent_name: str) -> str:
        labels = {
            "DocumentAgent": "讲解文档智能体",
            "MindmapAgent": "思维导图智能体",
            "ExerciseAgent": "练习生成智能体",
            "VideoScriptAgent": "视频脚本智能体",
            "CodeAgent": "代码案例智能体",
            "ImageAgent": "图片生成智能体",
            "RetrievalAgent": "证据检索智能体",
            "QualityAgent": "质量校验智能体",
        }
        return labels.get(agent_name, agent_name)

    @staticmethod
    def _center_node_name(evidence: EvidencePackage) -> str:
        if evidence.center_node is None:
            return evidence.resolved_uid or "未知知识点"
        return str(
            evidence.center_node.properties.get("name")
            or evidence.center_node.properties.get("title")
            or evidence.resolved_uid
            or evidence.center_node.uid
        )

    @staticmethod
    def _resource_validation_error(agent_name: str, result: Any) -> str | None:
        """拒绝空壳资源对象，避免前端出现伪完成。"""
        if result is None:
            return "未返回可用结果。"

        if agent_name == "DocumentAgent":
            content = str(getattr(result, "content", "") or "").strip()
            if len(content) < 50:
                return "讲解文档正文为空或过短。"
            return None

        if agent_name == "MindmapAgent":
            content = str(getattr(result, "content", "") or "").strip()
            if not content:
                return "思维导图内容为空。"
            if not content.startswith(("mindmap", "graph", "flowchart")):
                return "思维导图不是有效的 Mermaid 内容。"
            return None

        if agent_name == "ExerciseAgent":
            items = getattr(result, "items", result)
            if not items:
                return "练习题列表为空。"
            for index, item in enumerate(items, start=1):
                question = str(getattr(item, "question", "") or "").strip()
                answer = getattr(item, "answer", None)
                if not question or not answer:
                    return f"第 {index} 道练习缺少题干或答案。"
            return None

        if agent_name == "VideoScriptAgent":
            scenes = getattr(result, "scenes", None) or []
            if len(scenes) < 2:
                return "视频脚本分镜不足 2 个。"
            return None

        if agent_name == "CodeAgent":
            code = str(getattr(result, "code", "") or "").strip()
            explanation = str(getattr(result, "explanation", "") or "").strip()
            if len(code) < 20:
                return "代码内容为空或过短。"
            if not any(keyword in code for keyword in ("def", "import", "class", "print", "=")):
                return "代码缺少明显的可执行语句。"
            if len(explanation) < 20:
                return "代码说明为空或过短。"
            return None

        if agent_name == "ImageAgent":
            image_url = str(getattr(result, "image_url", "") or "").strip()
            prompt = str(getattr(result, "prompt", "") or "").strip()
            if not image_url:
                return "图片生成未返回可访问地址。"
            if len(prompt) < 20:
                return "图片提示词为空或过短。"
            return None

        return None

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
            if resources.document.illustrations:
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

        if resources.image is not None:
            if not resources.image.image_url:
                warnings.append("ImageAgent: 图片资源缺少可访问地址。")
            if len(resources.image.prompt or "") < 20:
                warnings.append("ImageAgent: 图片提示词过短，可能影响生成质量。")
            generated_count += 1

        if generated_count == 0:
            warnings.append("未生成任何学习资源。")

        generated_score = 0.0
        generated_score += 0.25 if evidence.center_node is not None else 0.0
        generated_score += 0.20 if source_uids else 0.0
        generated_score += min(generated_count, 5) * 0.11
        generated_score = min(generated_score, 1.0)

        hybrid_quality = evidence.student_profile_adaptation.get("hybrid_rag_quality") or {}
        coverage_score = float(hybrid_quality.get("coverage_score", 0.0) or 0.0)
        relevance_score = float(hybrid_quality.get("relevance_score", evidence.relevance_score or 0.0) or 0.0)
        grounding_score = float(hybrid_quality.get("grounding_score", 1.0 if source_uids else 0.0) or 0.0)
        personal_fit_score = float(hybrid_quality.get("personal_fit_score", 0.0) or 0.0)
        hybrid_score = float(hybrid_quality.get("overall_score", evidence.evidence_score or 0.0) or 0.0)
        score = round(min(1.0, hybrid_score * 0.65 + generated_score * 0.35), 3)
        weak_reasons = list(hybrid_quality.get("weak_reasons") or [])
        repair_actions = list(hybrid_quality.get("repair_actions") or [])
        if evidence.resolution_quality == "fallback":
            weak_reasons.append("知识点定位为降级匹配，回答中需要提示不确定性。")
        fallback_used = evidence.resolution_quality == "fallback"
        return QualityReport(
            grounded=evidence.center_node is not None and bool(source_uids),
            score=score,
            coverage_score=round(max(0.0, min(1.0, coverage_score)), 3),
            relevance_score=round(max(0.0, min(1.0, relevance_score)), 3),
            grounding_score=round(max(0.0, min(1.0, grounding_score)), 3),
            personal_fit_score=round(max(0.0, min(1.0, personal_fit_score)), 3),
            warnings=warnings,
            weak_reasons=list(dict.fromkeys(weak_reasons)),
            repair_actions=repair_actions,
            source_uids=source_uids,
            fallback_used=fallback_used,
        )

    @staticmethod
    def _parse_generated_resources(value: Any) -> GeneratedResources:
        if isinstance(value, dict):
            normalized = dict(value)
            if normalized.get("exercises") is None:
                normalized["exercises"] = []
            return GeneratedResources.model_validate(normalized)
        return GeneratedResources.model_validate(value or {})

    @staticmethod
    def _has_generated_resource(resources: GeneratedResources) -> bool:
        return any(
            (
                resources.document is not None,
                resources.mindmap is not None,
                bool(resources.exercises),
                resources.video_script is not None,
                resources.code_case is not None,
                resources.image is not None,
            )
        )

    @staticmethod
    def _generated_resource_types(resources: GeneratedResources) -> list[ResourceType]:
        generated: list[ResourceType] = []
        if resources.document is not None:
            generated.append("document")
            if resources.document.illustrations:
                generated.append("image")
        if resources.mindmap is not None:
            generated.append("mindmap")
        if resources.exercises:
            generated.append("exercise")
        if resources.video_script is not None:
            generated.append("video_script")
        if resources.code_case is not None:
            generated.append("code_case")
        if resources.image is not None and "image" not in generated:
            generated.append("image")
        return generated

    @classmethod
    def _failed_resource_types(
        cls,
        requested_types: list[ResourceType],
        resources: GeneratedResources,
    ) -> list[ResourceType]:
        requested = list(dict.fromkeys(requested_types))
        generated = set(cls._generated_resource_types(resources))
        return [item for item in requested if item not in generated]

    @classmethod
    def _generation_status(
        cls,
        requested_types: list[ResourceType],
        resources: GeneratedResources,
    ) -> str:
        success_types = cls._generated_resource_types(resources)
        if not success_types:
            return "failed"
        failed_types = cls._failed_resource_types(requested_types, resources)
        return "partial_success" if failed_types else "success"
