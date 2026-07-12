import json
import random
from typing import Any, TypeVar

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import Settings
from app.core.manual_json import parse_model
from app.graph.models import GraphNode, GraphPath
from app.graphrag.schemas import EvidencePackage, StudentProfileInput
from app.agents.schemas import (
    GeneratedCodeCase,
    GeneratedDocument,
    GeneratedExercise,
    GeneratedExercises,
    GeneratedMindmap,
    GeneratedVideoScript,
)


T = TypeVar("T", bound=BaseModel)


class LangChainResourceAgents:
    """LangChain-backed resource generators grounded in one EvidencePackage."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate_document(
        self,
        evidence: EvidencePackage,
        profile: StudentProfileInput,
    ) -> GeneratedDocument:
        return await self._invoke_structured(
            output_model=GeneratedDocument,
            agent_name="DocumentAgent",
            task=(
                "生成一份 Markdown 讲解文档。要求：先给直观解释，再说明核心机制，"
                "再区分易混概念，最后给下一步学习建议。内容必须适合学生画像。"
                "如果包含数学公式，行内公式必须使用 $...$，独立公式必须使用 $$...$$，"
                "不要输出未加 LaTeX 分隔符的裸公式。"
            ),
            evidence=evidence,
            profile=profile,
        )

    async def generate_mindmap(
        self,
        evidence: EvidencePackage,
        profile: StudentProfileInput,
    ) -> GeneratedMindmap:
        result = await self._invoke_structured(
            output_model=GeneratedMindmap,
            agent_name="MindmapAgent",
            task=(
                "生成一张适合 Markmap 渲染的 Mermaid mindmap，用作复习导航和概念地图，"
                "不是讲义摘要、不是公式表、不是代码清单。content 字段只放 Mermaid 文本。\n"
                "硬性格式：第一行必须是 mindmap；第二行必须是 root((中心知识点名称))；"
                "后续每个节点独占一行，用两个空格表示一级缩进；不要压缩成一行。\n"
                "结构要求：root 下建议 4 到 6 个一级分支，可从『概念定位、前置基础、核心流程、关键分工、常见误区、应用延伸、学习抓手』中选择；"
                "每个一级分支下放 2 到 4 个二级关键词，必要时最多再展开一层。\n"
                "节点内容要求：每个节点必须是短标签，优先 2 到 10 个中文字符，最长不超过 14 个中文字符或 4 个英文词；"
                "禁止把完整句子、解释性长句、公式、代码、循环语句、参数更新代码放进节点。"
                "如果证据里有公式或代码，只能概括成『更新公式』『训练循环』『梯度回传』这类短标签。"
                "避免同层重复节点，例如 Mini-batch 只出现一次。"
                "不要使用冒号解释，如不要写『SGD：每次用一个样本估计梯度』，应写成『SGD』，解释留给讲解文档。"
            ),
            evidence=evidence,
            profile=profile,
        )
        center_name = ""
        if evidence.center_node is not None:
            center_name = str(evidence.center_node.properties.get("name") or evidence.resolved_uid or "")
        result.content = _polish_mindmap_content(result.content, center_name=center_name)
        return result

    async def generate_exercises(
        self,
        evidence: EvidencePackage,
        profile: StudentProfileInput,
        *,
        count: int = 3,
        exercise_type: str | None = None,
    ) -> list[GeneratedExercise]:
        count = max(1, min(int(count or 3), 20))
        center_name = ""
        if evidence.center_node is not None:
            center_name = str(evidence.center_node.properties.get("name") or evidence.resolved_uid or "")

        type_instruction = (
            f"所有题目都必须是 {exercise_type} 类型。"
            if exercise_type
            else "题型可包含 choice、short_answer、coding、case_analysis，但至少一道是 choice 类型。"
        )

        # 强制选择题必须包含选项的提示
        choice_hint = ""
        if exercise_type == "choice" or not exercise_type:
            choice_hint = """
【选择题强制要求 - 必须严格遵守】
- type 字段必须为 "choice"
- options 字段必须是长度为 4 的数组，格式：[{"label": "A", "text": "选项A的内容"}, {"label": "B", "text": "选项B的内容"}, {"label": "C", "text": "选项C的内容"}, {"label": "D", "text": "选项D的内容"}]
- answer 字段必须包含 correct（A/B/C/D 之一）和 explanation
- 禁止省略 options 字段，禁止选项数量少于 4 个
"""

        result = await self._invoke_structured(
            output_model=GeneratedExercises,
            agent_name="ExerciseAgent",
            task=(
                f"生成 {count} 道练习题，以 JSON 格式输出。"
                f"{type_instruction}"
                "每道题必须填写 title、type（choice/short_answer/coding）、question、difficulty（1-5 整数）、"
                "answer（对象格式）、adaptive_feedback（对象格式，包含 default 字段）和 source_uids 数组。"
                "{choice_hint}"
            ).format(choice_hint=choice_hint),
            evidence=evidence,
            profile=profile,
        )
        # 调试：写入文件
        import json, sys
        debug_info = {
            "count": len(result.items) if result.items else 0,
            "items": [item.model_dump() for item in (result.items or [])]
        }
        with open("debug_exercise.json", "w", encoding="utf-8") as f:
            json.dump(debug_info, f, ensure_ascii=False, indent=2)
        print(f"[ExerciseAgent] 返回 {len(result.items) if result.items else 0} 个题目", file=sys.stderr)
        for i, item in enumerate(result.items or []):
            print(f"  题{i+1}: type={item.type}, options={item.options}, question[:60]={item.question[:60] if item.question else 'N/A'}", file=sys.stderr)
        sys.stderr.flush()
        if not result.items:
            # LLM 没有返回有效 JSON，使用 topic-specific 模板生成
            fallback = self._build_topic_specific_exercises(evidence, center_name, count, exercise_type)
            result.items = fallback
        items = result.items[:count]
        if len(items) < count:
            items.extend(_build_fallback_exercises(evidence, count - len(items), exercise_type=exercise_type))

        normalized = _normalize_generated_exercises(
            items,
            evidence,
            count=count,
            exercise_type=exercise_type,
        )
        return normalized

    async def generate_video_script(
        self,
        evidence: EvidencePackage,
        profile: StudentProfileInput,
    ) -> GeneratedVideoScript:
        return await self._invoke_structured(
            output_model=GeneratedVideoScript,
            agent_name="VideoScriptAgent",
            task=(
                "生成 2 分钟左右教学动画脚本。每个分镜必须包含画面 visual、旁白 narration "
                "和动画提示 animation_hint。脚本要突出该知识点为什么重要以及学生容易混淆的地方。"
            ),
            evidence=evidence,
            profile=profile,
        )

    async def generate_code_case(
        self,
        evidence: EvidencePackage,
        profile: StudentProfileInput,
    ) -> GeneratedCodeCase:
        return await self._invoke_structured(
            output_model=GeneratedCodeCase,
            agent_name="CodeAgent",
            task=(
                "生成一个 Python 代码案例。代码应短小、可读、尽量可直接运行。"
                "必须解释输入、输出和关键步骤，并提供简单 test_cases。"
            ),
            evidence=evidence,
            profile=profile,
        )

    # ---- per-agent evidence routing ----
    _AGENT_EVIDENCE_KEYS: dict[str, list[str]] = {
        "DocumentAgent": ["center_node", "document_chunks", "misconceptions", "prerequisites", "sources"],
        "MindmapAgent": ["center_node", "prerequisites", "related_nodes", "misconceptions"],
        "ExerciseAgent": ["center_node", "exercises", "misconceptions", "document_chunks"],
        "VideoScriptAgent": ["center_node", "prerequisites", "document_chunks", "misconceptions", "related_nodes"],
        "CodeAgent": ["center_node", "code_cases", "exercises", "document_chunks"],
    }

    def _personalized_task(
        self,
        agent_name: str,
        task: str,
        profile: StudentProfileInput,
        evidence: EvidencePackage,
    ) -> str:
        parts = [task]
        center_name = ""
        if evidence.center_node is not None:
            center_name = str(evidence.center_node.properties.get("name") or evidence.resolved_uid or "")
        if center_name:
            parts.append(
                f"本次资源的中心主题是「{center_name}」。所有标题、正文、题目、脚本和代码案例都必须围绕这个中心主题生成，"
                "不能因为学生画像里的薄弱点而改讲其他知识点。"
            )
        relevant_weak_points, background_weak_points = _split_relevant_weak_points(
            profile.weak_points,
            evidence,
        )
        if relevant_weak_points:
            parts.append(f"与本主题相关的学生薄弱点：{', '.join(relevant_weak_points)}。可适当多解释这些相关薄弱概念。")
        if background_weak_points:
            parts.append(
                f"画像中还记录了其他薄弱点：{', '.join(background_weak_points)}。"
                "这些只作为学习背景，不要把本次资源主题改成这些薄弱点。"
            )
        prefs = profile.preferences or []
        if prefs:
            pref_labels = {
                "diagram": "偏好图解和可视化，多用『可以把这想象成』『从图上可以看到』",
                "code_case": "偏好代码示例，可以适当加入伪代码或 Python 片段辅助理解",
                "exercise": "偏好通过做题巩固，可以在讲解中穿插小思考题",
                "document": "偏好文字阅读，可适当展开上下文和原理",
                "video_script": "偏好动画讲解，多用场景化的描述",
            }
            hints = [pref_labels[p] for p in prefs[:2] if p in pref_labels]
            if hints:
                parts.append(f"学生偏好：{'；'.join(hints)}。")
        return "\n".join(parts)

    async def _invoke_structured(
        self,
        output_model: type[T],
        agent_name: str,
        task: str,
        evidence: EvidencePackage,
        profile: StudentProfileInput,
    ) -> T:
        personalized_task = self._personalized_task(agent_name, task, profile, evidence)
        allowed_keys = self._AGENT_EVIDENCE_KEYS.get(agent_name, list(self._AGENT_EVIDENCE_KEYS["DocumentAgent"]))
        llm = self._build_raw_llm(agent_name)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是 EduGraph-Agent 的 {agent_name}。"
                    "你必须基于 GraphRAG 证据包生成学习资源，不能编造不存在的来源。"
                    "如果证据不足，可以在输出中温和提示，但仍要围绕已有证据生成可用资源。"
                    "你必须在回复的【末尾】输出一段严格 JSON，以 ```json 开头、``` 结尾，"
                    "包含 schema 要求的全部顶层字段，不可遗漏。"
                    "title 字段不可为空字符串。content/code/explanation 等核心字段必须有实质内容。"
                    "source_uids 字段必须从证据包已有来源中选择，不可凭空编造。"
                    "\n\n【输出格式要求】\n"
                    "在回复末尾，用以下格式输出 JSON：\n"
                    "```json\n{{你的JSON内容}}\n```\n"
                    "注意：不要遗漏任何顶层字段，空值用 [] 或 \"\" 表示。",
                ),
                (
                    "human",
                    "个性化指令：\n{task}\n\n"
                    "学生画像：\n{student_profile}\n\n"
                    "GraphRAG 证据包（{agent_name} 专属）：\n{evidence_context}\n\n"
                    "请先给出内容，最后输出 ```json ... ``` 格式的结构化结果。",
                ),
            ]
        )
        chain = prompt | llm
        raw_response = await chain.ainvoke(
            {
                "agent_name": agent_name,
                "task": personalized_task,
                "student_profile": json.dumps(profile.model_dump(), ensure_ascii=False),
                "evidence_context": json.dumps(
                    _compact_evidence(evidence, allowed_keys=allowed_keys), ensure_ascii=False
                ),
            }
        )
        response_text = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
        return parse_model(response_text, output_model)

    def _build_raw_llm(self, agent_name: str) -> ChatOpenAI:
        """构建原始 LLM（不使用 structured output，手动解析 JSON）。"""
        model_kwargs: dict[str, Any] = {
            "model": self.settings.llm_model,
            "api_key": self.settings.llm_api_key,
            "temperature": 0.15 if agent_name in ("DocumentAgent", "CodeAgent") else 0.25,
        }
        if self.settings.llm_base_url:
            model_kwargs["base_url"] = self.settings.llm_base_url
        return ChatOpenAI(**model_kwargs)


def _compact_evidence(
    evidence: EvidencePackage,
    allowed_keys: list[str] | None = None,
) -> dict[str, Any]:
    full: dict[str, Any] = {
        "query": evidence.query,
        "resolved_uid": evidence.resolved_uid,
        "center_node": _node_brief(evidence.center_node),
        "prerequisites": [_path_brief(path) for path in evidence.prerequisites[:5]],
        "related_nodes": [_path_brief(path) for path in evidence.related_nodes[:5]],
        "document_chunks": [_node_brief(node) for node in evidence.document_chunks[:5]],
        "exercises": [_node_brief(node) for node in evidence.exercises[:5]],
        "code_cases": [_node_brief(node) for node in evidence.code_cases[:3]],
        "misconceptions": [_node_brief(node) for node in evidence.misconceptions[:5]],
        "semantic_hits": [_semantic_hit_brief(hit) for hit in evidence.semantic_hits[:8]],
        "sources": [_source_brief(node) for node in evidence.sources[:8]],
        "ranking_reason": evidence.ranking_reason,
        "missing_evidence": evidence.missing_evidence,
        "uncertainty": evidence.uncertainty,
    }
    if allowed_keys is not None:
        return {k: v for k, v in full.items() if k in allowed_keys or k in ("query", "resolved_uid", "missing_evidence", "uncertainty")}
    return full


def _node_brief(node: GraphNode | None) -> dict[str, Any] | None:
    if node is None:
        return None
    props = node.properties
    keys = [
        "name",
        "title",
        "summary",
        "content",
        "question",
        "answer",
        "options",
        "keywords",
        "aliases",
        "mastery_objectives",
        "common_misconceptions",
        "source_ids",
        "chapter_id",
        "difficulty",
    ]
    compact = {key: props.get(key) for key in keys if key in props}
    if "content" in compact and isinstance(compact["content"], str):
        compact["content"] = compact["content"][:900]
    return {"uid": node.uid, "labels": node.labels, "properties": compact}


def _source_brief(node: GraphNode) -> dict[str, Any]:
    props = node.properties
    return {
        "uid": node.uid,
        "title": props.get("title") or props.get("name"),
        "type": props.get("type"),
        "url": props.get("url"),
        "local_file": props.get("local_file"),
    }


def _semantic_hit_brief(hit: Any) -> dict[str, Any]:
    view = getattr(hit, "view", None)
    if view is None:
        return {}
    return {
        "view_id": view.id,
        "target_uid": view.target_uid,
        "target_type": view.target_type,
        "view_type": view.view_type,
        "node_ids": view.node_ids,
        "title": view.title,
        "score": getattr(hit, "score", 0.0),
        "rank_reason": getattr(hit, "rank_reason", []),
    }


    def _build_topic_specific_exercises(
        self,
        evidence: EvidencePackage,
        center_name: str,
        count: int,
        exercise_type: str | None = None,
    ) -> list[GeneratedExercise]:
        """基于知识点生成有意义的练习题，包含正确的选项。"""
        if not center_name:
            center_name = "该知识点"
        node_id = evidence.resolved_uid or ""
        source_uids = [source.uid for source in evidence.sources[:3]]
        topic_options = _get_topic_specific_options(center_name)

        # 根据知识点生成针对性的题目模板
        templates = self._get_exercise_templates(center_name, topic_options)

        exercises: list[GeneratedExercise] = []
        requested_type = exercise_type or "choice"

        for idx in range(count):
            idx_in_templates = idx % len(templates)
            title, question, correct_idx, explanation = templates[idx_in_templates]

            if requested_type != "choice":
                exercises.append(
                    GeneratedExercise(
                        title=f"{center_name}{title}自测 {idx + 1}",
                        type=requested_type,
                        related_node_id=node_id,
                        difficulty=2 + (idx % 3),
                        question=f"关于{center_name}，{question}",
                        answer={"reference_answer": explanation},
                        adaptive_feedback={"default": explanation},
                        source_uids=source_uids,
                    )
                )
                continue

            # 构建选择题选项
            options = [
                {"label": "A", "text": topic_options[0] if len(topic_options) > 0 else "正确理解并能灵活应用"},
                {"label": "B", "text": topic_options[1] if len(topic_options) > 1 else "需要死记硬背"},
                {"label": "C", "text": topic_options[2] if len(topic_options) > 2 else "不需要理解原理"},
                {"label": "D", "text": topic_options[3] if len(topic_options) > 3 else "与机器学习无关"},
            ]
            correct_label = ["A", "B", "C", "D"][correct_idx]

            exercises.append(
                GeneratedExercise(
                    title=f"{center_name}{title}选择题 {idx + 1}",
                    type="choice",
                    related_node_id=node_id,
                    difficulty=2 + (idx % 3),
                    question=f"关于{center_name}，{question}",
                    options=options,
                    answer={"correct": correct_label, "explanation": explanation},
                    adaptive_feedback={"default": explanation},
                    source_uids=source_uids,
                )
            )

        return exercises

    def _get_exercise_templates(
        self,
        center_name: str,
        topic_options: list[str],
    ) -> list[tuple[str, str, int, str]]:
        """根据知识点名称返回题目模板。"""
        name_lower = center_name.lower()

        # 神经网络相关
        if any(k in name_lower for k in ["neural", "mlp", "多层", "神经网络"]):
            return [
                ("核心机制", "哪项描述最准确地说明了核心机制？", 0, f"{topic_options[0] if topic_options else '反向传播调整权重'}是理解核心机制的关键。"),
                ("常见误区", "哪项是初学者最需要避免的误区？", 1, f"认为{topic_options[1] if len(topic_options) > 1 else '只需要记住公式'}是常见误区。"),
                ("实际应用", "在实际应用中，哪项做法最合理？", 0, f"应该{topic_options[0] if topic_options else '理解原理后再应用'}。"),
            ]

        # 聚类相关
        if any(k in name_lower for k in ["cluster", "聚类", "kmeans", "k-means"]):
            return [
                ("核心目标", "该算法的核心目标是什么？", 0, "最小化簇内距离、最大化簇间距离是聚类的核心目标。"),
                ("初始中心", "关于初始中心点，哪项说法正确？", 0, "初始中心的选择会影响最终聚类结果，应多次运行取最优。"),
                ("簇数选择", "如何确定最佳的簇数？", 0, "可以使用肘部法则、轮廓系数等方法综合判断。"),
            ]

        # 梯度下降相关
        if any(k in name_lower for k in ["gradient", "梯度", "下降", "sgd", "学习率"]):
            return [
                ("更新方向", "参数更新的方向应该是？", 0, "沿梯度负方向更新以最小化损失函数。"),
                ("学习率", "学习率过大可能导致什么问题？", 0, "学习率过大会导致参数震荡或无法收敛。"),
                ("收敛条件", "如何判断训练是否收敛？", 0, "可观察损失函数值是否趋于稳定。"),
            ]

        # 默认模板
        return [
            ("核心概念", "哪项描述最准确地概括了核心概念？", 0, f"{topic_options[0] if topic_options else '掌握核心概念是学习的基础'}。"),
            ("常见误区", "关于该知识点，哪项说法需要纠正？", 1, f"认为'{topic_options[1] if len(topic_options) > 1 else '不需要深入理解'}'是常见误区。"),
            ("实际应用", "在应用中，哪项最重要？", 0, f"理解原理后灵活应用最为重要。"),
        ]


def _build_fallback_exercises(
    evidence: EvidencePackage,
    count: int,
    *,
    exercise_type: str | None = None,
) -> list[GeneratedExercise]:
    center_name = "该知识点"
    if evidence.center_node is not None:
        center_name = str(evidence.center_node.properties.get("name") or evidence.resolved_uid or center_name)
    node_id = evidence.resolved_uid or ""
    source_uids = [source.uid for source in evidence.sources[:3]]
    templates = [
        (
            "核心目标",
            f"学习 {center_name} 时，最应该优先理解哪一项？",
            [
                ("A", "算法要优化的目标或评价标准"),
                ("B", "只需要记住所有公式符号"),
                ("C", "只要会调用库函数就不需要理解过程"),
                ("D", "忽略数据特点也能稳定得到好结果"),
            ],
            "A",
            "理解目标函数、迭代过程或评价标准，是掌握该知识点的基础。",
        ),
        (
            "常见误区",
            f"关于 {center_name} 的常见误区，哪一项最需要避免？",
            [
                ("A", "把算法输出当成永远唯一且绝对正确的结果"),
                ("B", "结合数据分布和参数设置分析结果"),
                ("C", "检查模型假设是否适合当前任务"),
                ("D", "用练习验证自己是否真的理解流程"),
            ],
            "A",
            "机器学习算法通常受数据、初始化、参数和假设影响，不能机械理解。",
        ),
        (
            "实践判断",
            f"在实际使用 {center_name} 时，哪种做法更可靠？",
            [
                ("A", "先明确输入、输出、关键参数和评价方式"),
                ("B", "不看数据直接套默认参数"),
                ("C", "只看一次运行结果就下结论"),
                ("D", "跳过可视化和误差分析"),
            ],
            "A",
            "真实学习和建模都需要把算法机制、数据特征和评价反馈结合起来。",
        ),
    ]
    exercises: list[GeneratedExercise] = []
    for idx in range(count):
        title, question, options, correct, explanation = templates[idx % len(templates)]
        requested_type = exercise_type or "choice"
        if requested_type != "choice":
            exercises.append(
                GeneratedExercise(
                    title=f"{center_name}{title}自测 {idx + 1}",
                    type=requested_type,  # type: ignore[arg-type]
                    related_node_id=node_id,
                    difficulty=2 + (idx % 3),
                    question=question,
                    answer={"reference_answer": explanation},
                    adaptive_feedback={"default": explanation},
                    source_uids=source_uids,
                )
            )
            continue
        exercises.append(
            GeneratedExercise(
                title=f"{center_name}{title}选择题 {idx + 1}",
                type="choice",
                related_node_id=node_id,
                difficulty=2 + (idx % 3),
                question=question,
                options=[{"label": label, "text": text} for label, text in options],
                answer={"correct": correct, "explanation": explanation},
                adaptive_feedback={"default": explanation},
                source_uids=source_uids,
            )
        )
    return exercises


def _parse_inline_options(question: str) -> tuple[list[dict[str, str]], str] | None:
    """
    从问题文本中解析内联的 A/B/C/D 选项。
    返回 (options, remaining_question) 或 None。
    """
    import re

    # 提取选项部分和问题部分
    # 先把整个字符串按 A. B. C. D. 分割
    combined = question
    options: list[dict[str, str]] = []

    # 方法1：按换行符分割（多行格式）
    lines = combined.split('\n')
    found_options = []
    question_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 匹配选项行
        match = re.match(r'^([A-D])[\.\、\s]+(.+)$', line)
        if match:
            label, text = match.groups()
            text = ' '.join(text.split())[:80]
            found_options.append({"label": label.strip().upper(), "text": text})
        elif found_options:
            # 如果已经找到了选项，继续收集剩余的选项行
            match2 = re.match(r'^([A-D])[\.\、\s]+(.+)$', line)
            if match2:
                label, text = match2.groups()
                text = ' '.join(text.split())[:80]
                found_options.append({"label": label.strip().upper(), "text": text})
        else:
            question_lines.append(line)

    if len(found_options) >= 4:
        # 提取问题部分（去掉选项行）
        remaining_question = '\n'.join(question_lines) if question_lines else question.split('A.')[0].split('A、')[0].strip()
        return found_options[:4], remaining_question

    # 方法2：单行格式 A. xxx B. xxx C. xxx D. xxx
    # 替换换行
    single = combined.replace('\n', ' ')
    pattern = r'([A-D])[\.\、\s]+([^A-D\n]{3,100}?)(?=[A-D][\.\、\s]|$)'
    matches = re.findall(pattern, single)
    if len(matches) >= 4:
        options = []
        for label, text in matches[:4]:
            text = ' '.join(text.split())[:80]
            options.append({"label": label.strip().upper(), "text": text})
        # 提取问题部分
        question_part = re.split(r'[A-D][\.\、\s]+', single, maxsplit=1)[0].strip()
        return options, question_part

    return None


def _normalize_generated_exercises(
    items: list[GeneratedExercise],
    evidence: EvidencePackage,
    *,
    count: int,
    exercise_type: str | None = None,
) -> list[GeneratedExercise]:
    requested_type = exercise_type or ""
    fallback_type = exercise_type or "choice"
    fallbacks = _build_fallback_exercises(evidence, count, exercise_type=fallback_type)
    normalized: list[GeneratedExercise] = []
    node_id = evidence.resolved_uid or ""
    source_uids = [source.uid for source in evidence.sources[:3]]

    for idx, item in enumerate(items[:count]):
        fallback = fallbacks[idx]
        if requested_type and item.type != requested_type:
            if requested_type == "choice":
                repaired = _try_repair_choice_exercise(item, evidence, node_id, source_uids)
                if repaired:
                    normalized.append(repaired)
                    continue
            normalized.append(fallback)
            continue
        if item.type == "choice":
            # 检查选项是否有效
            if not _is_valid_choice_exercise(item):
                # 尝试从问题文本中解析内联选项
                result = _parse_inline_options(item.question)
                if result:
                    inline_options, remaining_question = result
                    item.options = inline_options
                    if remaining_question:
                        item.question = remaining_question
                # 如果解析后仍然无效，使用 repair 函数从证据构建
                if not _is_valid_choice_exercise(item):
                    repaired = _try_repair_choice_exercise(item, evidence, node_id, source_uids)
                    if repaired:
                        normalized.append(repaired)
                        continue
                    normalized.append(fallback)
                    continue
        if node_id and not item.related_node_id:
            item.related_node_id = node_id
        if source_uids and not item.source_uids:
            item.source_uids = source_uids
        if item.type == "choice" and "explanation" not in item.answer:
            default_feedback = item.adaptive_feedback.get("default")
            if default_feedback:
                item.answer["explanation"] = default_feedback
        normalized.append(item)

    if len(normalized) < count:
        normalized.extend(fallbacks[len(normalized):count])
    return normalized[:count]


def _get_topic_specific_options(center_name: str) -> list[str]:
    """
    根据知识点名称返回 topic-specific 的选择题选项文本。
    包含 ML/DL 核心概念的模板，确保生成的选项有实质内容而非通用废话。
    """
    name_lower = center_name.lower()

    # 按关键词匹配模板
    templates: dict[str, list[str]] = {
        # 神经网络
        "neural": [
            "通过反向传播算法调整网络权重",
            "只能处理线性可分的分类问题",
            "需要手工设计特征作为输入",
            "只能在CPU上运行",
        ],
        "mlp": [
            "通过反向传播算法调整网络权重",
            "只能处理线性可分的分类问题",
            "需要手工设计特征作为输入",
            "只能在CPU上运行",
        ],
        "多层": [
            "通过反向传播算法调整网络权重",
            "只能处理线性可分的分类问题",
            "需要手工设计特征作为输入",
            "只能在CPU上运行",
        ],
        # 激活函数
        "激活": [
            "为网络引入非线性，使其能拟合复杂模式",
            "对输入进行归一化，使其和为1",
            "减少网络层数，降低计算复杂度",
            "将所有负值直接置为零",
        ],
        "activation": [
            "为网络引入非线性，使其能拟合复杂模式",
            "对输入进行归一化，使其和为1",
            "减少网络层数，降低计算复杂度",
            "将所有负值直接置为零",
        ],
        # 梯度下降
        "梯度": [
            "沿损失函数梯度的负方向更新参数",
            "沿损失函数梯度的正方向更新参数",
            "参数更新方向与梯度无关",
            "只在训练开始时更新一次",
        ],
        "gradient": [
            "沿损失函数梯度的负方向更新参数",
            "沿损失函数梯度的正方向更新参数",
            "参数更新方向与梯度无关",
            "只在训练开始时更新一次",
        ],
        # 反向传播
        "反向传播": [
            "从输出层向输入层逐层计算梯度并更新权重",
            "从输入层向输出层逐层计算损失",
            "只在网络最后一层进行梯度计算",
            "不需要计算梯度直接调整参数",
        ],
        "backprop": [
            "从输出层向输入层逐层计算梯度并更新权重",
            "从输入层向输出层逐层计算损失",
            "只在网络最后一层进行梯度计算",
            "不需要计算梯度直接调整参数",
        ],
        # CNN
        "cnn": [
            "权重共享大幅减少参数量",
            "卷积核大小固定为1×1",
            "只能处理一维序列数据",
            "每个卷积核只关注一个像素点",
        ],
        "卷积": [
            "权重共享大幅减少参数量",
            "卷积核大小固定为1×1",
            "只能处理一维序列数据",
            "每个卷积核只关注一个像素点",
        ],
        # RNN
        "rnn": [
            "通过隐藏状态在序列中传递上下文信息",
            "各时间步之间没有信息传递",
            "可以并行处理任意长度的序列",
            "只能处理固定长度的输入",
        ],
        "循环": [
            "通过隐藏状态在序列中传递上下文信息",
            "各时间步之间没有信息传递",
            "可以并行处理任意长度的序列",
            "只能处理固定长度的输入",
        ],
        # 过拟合
        "过拟合": [
            "模型在训练数据上表现好但泛化能力差",
            "模型在训练和测试数据上表现都很差",
            "模型参数过少导致无法学习模式",
            "增加训练数据使测试误差增大",
        ],
        "overfit": [
            "模型在训练数据上表现好但泛化能力差",
            "模型在训练和测试数据上表现都很差",
            "模型参数过少导致无法学习模式",
            "增加训练数据使测试误差增大",
        ],
        # 欠拟合
        "欠拟合": [
            "模型过于简单，无法捕捉数据中的复杂模式",
            "模型过于复杂，在训练数据上过拟合",
            "训练数据量不足导致泛化误差大",
            "学习率设置过大导致震荡",
        ],
        # 归一化
        "归一化": [
            "将数据缩放到特定范围或调整为均值为0方差为1",
            "增加数据的数值范围提高精度",
            "减少数据集中的特征数量",
            "将所有数据变为唯一值",
        ],
        "normaliz": [
            "将数据缩放到特定范围或调整为均值为0方差为1",
            "增加数据的数值范围提高精度",
            "减少数据集中的特征数量",
            "将所有数据变为唯一值",
        ],
        # 损失函数
        "损失": [
            "衡量模型预测值与真实值之间的差异",
            "评估模型在测试集上的泛化能力",
            "衡量模型参数量的大小",
            "用于决定训练数据的使用顺序",
        ],
        "loss": [
            "衡量模型预测值与真实值之间的差异",
            "评估模型在测试集上的泛化能力",
            "衡量模型参数量的大小",
            "用于决定训练数据的使用顺序",
        ],
        # 优化器
        "优化": [
            "Adam等优化器可以自适应调整学习率",
            "所有优化器都使用固定学习率",
            "优化器的作用是增加模型复杂度",
            "优化器只在模型训练开始时运行一次",
        ],
        "optim": [
            "Adam等优化器可以自适应调整学习率",
            "所有优化器都使用固定学习率",
            "优化器的作用是增加模型复杂度",
            "优化器只在模型训练开始时运行一次",
        ],
        # 学习率
        "学习率": [
            "控制参数更新的步长，过大会导致震荡或发散",
            "学习率越大模型收敛越快",
            "学习率不影响梯度的大小",
            "学习率在训练过程中应该不断增大",
        ],
        "learning_rate": [
            "控制参数更新的步长，过大会导致震荡或发散",
            "学习率越大模型收敛越快",
            "学习率不影响梯度的大小",
            "学习率在训练过程中应该不断增大",
        ],
        # 正则化
        "正则": [
            "通过惩罚模型复杂度防止过拟合",
            "增加模型层数提高拟合能力",
            "减少训练数据量以提高泛化能力",
            "降低损失函数值使模型效果更好",
        ],
        "regulariz": [
            "通过惩罚模型复杂度防止过拟合",
            "增加模型层数提高拟合能力",
            "减少训练数据量以提高泛化能力",
            "降低损失函数值使模型效果更好",
        ],
        # 聚类
        "聚类": [
            "KMeans通过迭代找到使簇内距离最小的聚类中心",
            "聚类不需要定义距离度量方式",
            "所有聚类算法的结果都是确定的",
            "聚类算法可以自动确定最优的簇数",
        ],
        "cluster": [
            "KMeans通过迭代找到使簇内距离最小的聚类中心",
            "聚类不需要定义距离度量方式",
            "所有聚类算法的结果都是确定的",
            "聚类算法可以自动确定最优的簇数",
        ],
        "kmeans": [
            "KMeans通过迭代找到使簇内距离最小的聚类中心",
            "KMeans的初始中心不影响最终结果",
            "KMeans总是能找到全局最优解",
            "KMeans不需要预先指定簇的个数",
        ],
        # 降维
        "降维": [
            "PCA通过找到方差最大的方向进行投影实现降维",
            "降维会增加数据的特征维度",
            "所有降维方法都是线性的",
            "降维后的数据可以直接用于分类任务",
        ],
        "pca": [
            "PCA通过找到方差最大的方向进行投影实现降维",
            "PCA会增加数据的特征维度",
            "PCA降维后的主成分有明确的可解释含义",
            "PCA可以自动确定最优的主成分数量",
        ],
        # 交叉熵
        "交叉熵": [
            "交叉熵衡量两个概率分布之间的差异，常用于分类任务",
            "交叉熵只在回归任务中使用",
            "交叉熵值越大说明两个分布越相似",
            "交叉熵不需要概率输出",
        ],
        "cross_entropy": [
            "交叉熵衡量两个概率分布之间的差异，常用于分类任务",
            "交叉熵只在回归任务中使用",
            "交叉熵值越大说明两个分布越相似",
            "交叉熵不需要概率输出",
        ],
        # 泛化
        "泛化": [
            "模型在未见过的数据上表现良好的能力",
            "训练误差越小泛化能力越好",
            "泛化能力与模型复杂度无关",
            "测试集上的表现就是泛化能力的真实反映",
        ],
        # Embedding
        "embedding": [
            "将高维稀疏向量映射到低维稠密向量空间",
            "Embedding会增加特征向量的维度",
            "Embedding是手工设计的特征",
            "Embedding只能用于文本数据",
        ],
        # Transformer
        "transformer": [
            "通过自注意力机制捕获序列中任意位置之间的依赖关系",
            "Transformer需要循环结构来处理序列",
            "Transformer的注意力权重是固定的",
            "Transformer不能并行处理序列",
        ],
        # dropout
        "dropout": [
            "训练时随机丢弃部分神经元以减少过拟合",
            "Dropout会增加模型的参数量",
            "Dropout在推理时也会随机丢弃神经元",
            "Dropout对CNN比RNN更有效",
        ],
        # batch normalization
        "batch": [
            "对每一批次的数据进行均值方差归一化，稳定训练",
            "BatchNorm会增加梯度消失问题",
            "BatchNorm只在网络的第一层使用",
            "BatchNorm可以完全替代Dropout",
        ],
        "normali": [
            "对每一批次的数据进行均值方差归一化，稳定训练",
            "BatchNorm会增加梯度消失问题",
            "BatchNorm只在网络的第一层使用",
            "BatchNorm可以完全替代Dropout",
        ],
        # SVM
        "svm": [
            "通过找到最大间隔超平面实现分类",
            "SVM只能处理线性可分的数据",
            "SVM对特征缩放不敏感",
            "SVM的核函数必须使用线性核",
        ],
        # 决策树
        "决策树": [
            "通过递归分裂特征空间构建树形结构进行预测",
            "决策树的深度越大泛化能力越好",
            "决策树不需要特征缩放",
            "决策树一定会产生过拟合",
        ],
        "tree": [
            "通过递归分裂特征空间构建树形结构进行预测",
            "决策树的深度越大泛化能力越好",
            "决策树不需要特征缩放",
            "决策树一定会产生过拟合",
        ],
        # 集成学习
        "集成": [
            "通过组合多个模型的预测提升整体性能",
            "集成学习一定会增加模型的偏差",
            "Bagging和Boosting都是通过减小方差提升性能",
            "集成学习的模型数量越多越好",
        ],
        "boost": [
            "通过串行训练弱学习器逐步减少偏差",
            "Boosting中的各学习器可以完全独立训练",
            "Boosting主要用于减少方差",
            "Boosting一定会导致过拟合",
        ],
        "bagging": [
            "通过并行训练多个独立模型并对预测做平均减少方差",
            "Bagging主要用于减少偏差",
            "Bagging要求各基学习器之间强相关",
            "Bagging不会改变模型的泛化能力",
        ],
        # 参数/超参数
        "超参数": [
            "如学习率、网络层数等需要人工设定的参数",
            "超参数通过损失函数自动优化",
            "超参数在训练过程中不需要调整",
            "超参数越复杂模型效果越好",
        ],
        "hyperparam": [
            "如学习率、网络层数等需要人工设定的参数",
            "超参数通过损失函数自动优化",
            "超参数在训练过程中不需要调整",
            "超参数越复杂模型效果越好",
        ],
        # Epoch/Batch
        "epoch": [
            "完整遍历一次训练数据集称为一个epoch",
            "一个epoch意味着所有参数只更新一次",
            "epoch数越多模型效果一定越好",
            "epoch与batch size无关",
        ],
        "batch_size": [
            "每次迭代使用的样本数量，影响梯度估计的稳定性",
            "batch_size越大训练速度越快且内存占用越小",
            "batch_size不影响梯度的随机性",
            "batch_size必须能被数据集大小整除",
        ],
        # 偏差方差
        "偏差": [
            "模型预测值的期望与真实值之间的差异，反映模型的拟合能力",
            "偏差越大说明模型越复杂",
            "偏差与方差是独立的，没有权衡关系",
            "偏差只影响模型在训练集上的表现",
        ],
        # 距离度量
        "距离": [
            "如欧氏距离、曼哈顿距离等度量样本间相似性的指标",
            "所有距离度量对特征缩放都是不敏感的",
            "余弦相似度可以完全替代欧氏距离",
            "距离度量只用于聚类任务",
        ],
        # 评估指标
        "准确率": [
            "正确预测样本占总样本的比例",
            "准确率越高模型效果一定越好",
            "准确率可以解决类别不平衡问题",
            "准确率在多分类中等于召回率",
        ],
        "precision": [
            "预测为正的样本中真正为正的比例",
            "精确率越高召回率一定越高",
            "精确率可以单独评估不需要其他指标",
            "精确率在所有任务中比召回率更重要",
        ],
        "recall": [
            "真正为正的样本中被正确预测的比例",
            "召回率越高精确率一定越高",
            "召回率可以独立评估不需要其他指标",
            "召回率在所有任务中比精确率更重要",
        ],
        "f1": [
            "精确率和召回率的调和平均，综合反映模型性能",
            "F1分数越高说明模型越复杂",
            "F1分数不需要精确率和召回率就能计算",
            "F1分数在所有场景下都比准确率更合适",
        ],
        "auc": [
            "ROC曲线下的面积，衡量分类器在不同阈值下的整体表现",
            "AUC值越高说明模型区分正负样本的能力越强",
            "AUC对类别不平衡问题不敏感",
            "AUC值越大说明模型越复杂",
        ],
        "roc": [
            "以假阳性率为横轴、真阳性率为纵轴绘制的曲线",
            "ROC曲线越靠近左上角模型性能越好",
            "ROC曲线不受阈值选择的影响",
            "ROC曲线只能用于二分类任务",
        ],
    }

    # 查找匹配的模板
    for keyword, options in templates.items():
        if keyword in name_lower:
            return options

    # 默认模板（兜底）
    return [
        f"通过机器学习算法从数据中自动学习和调整参数",
        f"{center_name}是机器学习中的重要概念",
        f"需要大量标注数据才能训练出有效的模型",
        f"可以通过验证集评估模型的泛化性能",
    ]


def _try_repair_choice_exercise(
    item: GeneratedExercise,
    evidence: EvidencePackage,
    node_id: str,
    source_uids: list[str],
) -> GeneratedExercise | None:
    """从证据中构建有效的选择题。如果无法构建，返回 None。"""
    center_name = evidence.center_node.properties.get("name", node_id) if evidence.center_node else node_id

    # 收集可用于构建选项的文本
    texts: list[str] = []

    # 从 misconceptions 提取
    for m in (evidence.misconceptions or [])[:4]:
        props = m.properties or {}
        text = props.get("question") or props.get("summary") or props.get("content", "")
        if text and len(text) > 10:
            texts.append(str(text)[:100])

    # 从图谱 exercises 提取
    for ex in (evidence.exercises or [])[:4]:
        props = ex.properties or {}
        text = props.get("question") or props.get("title", "")
        if text and len(text) > 10:
            texts.append(str(text)[:100])

    # 从 document_chunks 提取关键词
    for doc in (evidence.document_chunks or [])[:3]:
        props = doc.properties or {}
        content = props.get("content", "") or props.get("summary", "")
        if content:
            texts.append(str(content)[:100])

    # 从 related_nodes 提取节点名称和描述
    for path in (evidence.related_nodes or [])[:4]:
        node = path.get("target_node") or path.get("source_node") or {}
        props = node.get("properties", {})
        name = props.get("name", "")
        desc = props.get("description", "") or props.get("summary", "") or props.get("definition", "")
        if name:
            texts.append(str(name)[:100])
        if desc and len(desc) > 10:
            texts.append(str(desc)[:100])

    # 从 sources 提取名称和摘要
    for source in (evidence.sources or [])[:3]:
        props = source.properties or {}
        name = props.get("name", "") or props.get("title", "")
        desc = props.get("abstract", "") or props.get("summary", "") or props.get("content", "")
        if name:
            texts.append(str(name)[:100])
        if desc and len(desc) > 10:
            texts.append(str(desc)[:100])

    # 如果收集不到足够的文本，使用 topic-specific 模板
    if len(texts) < 3:
        texts = _get_topic_specific_options(center_name)

    # 确保有 4 个选项
    while len(texts) < 4:
        texts.append(f"关于{center_name}的其他知识点")

    # 构建选择题：正确答案是第一个，错误答案是后三个
    correct_text = texts[0]
    wrong_texts = texts[1:4]

    # 构建选项：固定 A=正确, B/C/D=错误
    options = [
        {"label": "A", "text": correct_text},
        {"label": "B", "text": wrong_texts[0] if len(wrong_texts) > 0 else f"关于{center_name}的干扰选项"},
        {"label": "C", "text": wrong_texts[1] if len(wrong_texts) > 1 else f"关于{center_name}的其他说法"},
        {"label": "D", "text": wrong_texts[2] if len(wrong_texts) > 2 else f"{center_name}的常见误区"},
    ]

    # 使用原始题目或生成新题目
    question = item.question
    if not question or len(question) < 10:
        question = f"关于{center_name}，下列说法正确的是？"

    return GeneratedExercise(
        title=item.title or f"{center_name}理解测试",
        type="choice",
        related_node_id=node_id,
        difficulty=item.difficulty or 3,
        question=question,
        options=options,
        answer={"correct": "A", "explanation": f"正确答案是A。{correct_text[:50]}..."},
        adaptive_feedback={"default": f"请参考{center_name}的讲义内容加深理解。"},
        source_uids=source_uids,
    )


def _is_valid_choice_exercise(item: GeneratedExercise) -> bool:
    if item.type != "choice":
        return False
    if len(item.options) < 4:
        return False
    labels = {str(option.get("label", "")).strip().upper() for option in item.options if option.get("text")}
    if not {"A", "B", "C", "D"}.issubset(labels):
        return False
    correct = str(item.answer.get("correct", "")).strip().upper()
    return correct in {"A", "B", "C", "D"}


def _path_brief(path: GraphPath) -> dict[str, Any]:
    return {
        "nodes": [_node_brief(node) for node in path.nodes],
        "relationships": [
            {
                "type": rel.type,
                "source_uid": rel.source_uid,
                "target_uid": rel.target_uid,
                "explanation": rel.properties.get("explanation"),
            }
            for rel in path.relationships
        ],
    }


def _split_relevant_weak_points(
    weak_points: list[str],
    evidence: EvidencePackage,
) -> tuple[list[str], list[str]]:
    if not weak_points:
        return [], []

    related_terms: set[str] = set()
    related_uids: set[str] = set()

    def add_node(node: GraphNode | None) -> None:
        if node is None:
            return
        related_uids.add(node.uid)
        props = node.properties
        for value in [props.get("name"), props.get("title"), props.get("summary")]:
            if value:
                related_terms.add(str(value).lower())
        for key in ("aliases", "keywords"):
            for item in props.get(key, []) or []:
                related_terms.add(str(item).lower())

    add_node(evidence.center_node)
    for path in [*evidence.prerequisites, *evidence.related_nodes, *evidence.graph_paths]:
        for node in path.nodes:
            add_node(node)

    relevant: list[str] = []
    background: list[str] = []
    for weak_point in weak_points:
        normalized = str(weak_point).strip()
        lowered = normalized.lower()
        if not normalized:
            continue
        if lowered in {uid.lower() for uid in related_uids} or any(
            lowered in term or term in lowered for term in related_terms if term
        ):
            relevant.append(normalized)
        else:
            background.append(normalized)
    return relevant, background


def _polish_mindmap_content(content: str, center_name: str = "") -> str:
    """Keep mind map nodes as short labels, not lecture paragraphs."""
    cleaned = (content or "").strip()
    cleaned = cleaned.removeprefix("```mermaid").removeprefix("```").removesuffix("```").strip()
    if not cleaned:
        root = center_name or "思维导图"
        return f"mindmap\n  root(({root}))"

    lines = _normalize_mindmap_lines(cleaned)
    polished: list[str] = ["mindmap"]
    stack: dict[int, str] = {}
    seen_by_parent: dict[tuple[str, ...], set[str]] = {}
    has_root = False

    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped == "mindmap":
            continue

        indent_width = len(raw) - len(raw.lstrip(" "))
        level = max(1, min(indent_width // 2, 4))
        label = _short_mindmap_label(_readable_mindmap_label(stripped))
        if not label:
            continue

        if stripped.startswith("root"):
            label = _short_mindmap_label(center_name or label)
            polished.append(f"  root(({label}))")
            stack = {1: label}
            seen_by_parent = {(label,): set()}
            has_root = True
            continue

        if not has_root:
            root_label = _short_mindmap_label(center_name or label)
            polished.append(f"  root(({root_label}))")
            stack = {1: root_label}
            seen_by_parent = {(root_label,): set()}
            has_root = True
            if root_label == label:
                continue

        parent_path = tuple(stack.get(i, "") for i in range(1, level) if stack.get(i))
        siblings = seen_by_parent.setdefault(parent_path, set())
        if label in siblings:
            continue
        siblings.add(label)

        stack[level] = label
        for depth in list(stack):
            if depth > level:
                del stack[depth]
        polished.append(f"{'  ' * level}{label}")

    if len(polished) == 1:
        root = _short_mindmap_label(center_name or "思维导图")
        polished.append(f"  root(({root}))")
    return "\n".join(polished)


def _normalize_mindmap_lines(content: str) -> list[str]:
    if "\n" in content:
        return content.replace("\r\n", "\n").split("\n")
    tokens = _tokenize_mindmap_line(content)
    lines: list[str] = []
    for index, token in enumerate(tokens):
        if index == 0 and token == "mindmap":
            lines.append("mindmap")
        elif token.startswith("root"):
            lines.append(f"  {token}")
        else:
            lines.append(f"    {token}")
    return lines


def _tokenize_mindmap_line(content: str) -> list[str]:
    source = " ".join(content.split())
    tokens: list[str] = []
    current: list[str] = []
    square_depth = 0
    round_depth = 0
    for char in source:
        if char == "[":
            square_depth += 1
        elif char == "]":
            square_depth = max(0, square_depth - 1)
        elif char == "(":
            round_depth += 1
        elif char == ")":
            round_depth = max(0, round_depth - 1)

        if char == " " and square_depth == 0 and round_depth == 0:
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        tokens.append("".join(current))
    return tokens


def _readable_mindmap_label(text: str) -> str:
    label = text.strip()
    wrappers = [
        ("root((", "))"),
        ("root(", ")"),
        ("((", "))"),
        ("(", ")"),
        ("[", "]"),
    ]
    for prefix, suffix in wrappers:
        if label.startswith(prefix) and label.endswith(suffix):
            return label[len(prefix) : -len(suffix)].strip()

    if "[" in label and label.endswith("]"):
        return label[label.rfind("[") + 1 : -1].strip()
    if "((" in label and label.endswith("))"):
        return label[label.rfind("((") + 2 : -2].strip()
    if "(" in label and label.endswith(")"):
        return label[label.rfind("(") + 1 : -1].strip()
    return label


def _short_mindmap_label(label: str) -> str:
    text = " ".join(label.replace("`", "").split())
    text = text.strip(" -:：,，.;；。")
    if not text:
        return ""

    lowered = text.lower()
    if any(token in lowered for token in ("for epoch", "for ", "range(", "compute_loss")):
        return "训练循环"
    if any(token in lowered for token in ("params", "grad", "lr", "θ", "theta", "∇", "更新公式")):
        return "更新公式"
    if "mini-batch" in lowered or "minibatch" in lowered:
        return "Mini-batch"
    if lowered.startswith("sgd") or "随机梯度" in text:
        return "SGD"
    if "链式法则" in text:
        return "链式法则"
    if "梯度下降" in text:
        return "梯度下降"
    if "反向传播" in text:
        return "反向传播"

    for sep in ("：", ":", "，", "。", "；", ";", "，", ",", "（", "("):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break

    if len(text) > 16:
        text = text[:14].rstrip() + "..."
    return text
