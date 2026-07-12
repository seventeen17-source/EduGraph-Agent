import json
from typing import Any, Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.profile.schemas import StudentProfile


ExtractionMode = Literal["initialization", "update"]


class ExtractedKnownTopic(BaseModel):
    topic: str
    level: str | None = None
    evidence: str = ""


class ExtractedWeakPoint(BaseModel):
    topic: str
    description: str = ""


class ProfileExtractionResult(BaseModel):
    """LLM-produced profile delta. It is not written to DB directly."""

    background: dict[str, Any] | None = None
    learning_goal: dict[str, Any] | None = None
    known_topics: list[ExtractedKnownTopic] = Field(default_factory=list)
    unknown_topics: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] | None = None
    cognitive_style: dict[str, Any] | None = None
    self_reported_weak_points: list[ExtractedWeakPoint] = Field(default_factory=list)
    ability_signals: dict[str, str] = Field(default_factory=dict)
    confidence: float = 0.0
    confidence_notes: list[str] = Field(default_factory=list)

    def has_updates(self) -> bool:
        return bool(
            self.background
            or self.learning_goal
            or self.known_topics
            or self.unknown_topics
            or self.preferences
            or self.cognitive_style
            or self.self_reported_weak_points
            or self.ability_signals
        )


class ProfileExtractor:
    """LangChain structured-output extractor for student profile deltas."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._chain = None

    async def extract(
        self,
        message: str,
        existing_profile: StudentProfile,
        mode: ExtractionMode,
    ) -> ProfileExtractionResult:
        if not self.settings.llm_resolver_enabled or not self.settings.llm_api_key:
            return ProfileExtractionResult(confidence_notes=["llm_profile_extractor_disabled"])

        try:
            chain = self._get_chain()
            return await chain.ainvoke(
                {
                    "mode": mode,
                    "student_message": message,
                    "existing_profile": json.dumps(
                        _compact_profile(existing_profile),
                        ensure_ascii=False,
                    ),
                }
            )
        except Exception as exc:
            return ProfileExtractionResult(
                confidence_notes=[f"llm_profile_extractor_error:{type(exc).__name__}:{exc}"]
            )

    def _get_chain(self):
        if self._chain is not None:
            return self._chain

        model_kwargs: dict[str, Any] = {
            "model": self.settings.llm_model,
            "api_key": self.settings.llm_api_key,
            "temperature": 0,
        }
        if self.settings.llm_base_url:
            model_kwargs["base_url"] = self.settings.llm_base_url

        llm = ChatOpenAI(**model_kwargs)
        method = "json_mode" if self.settings.llm_provider in ("deepseek", "qwen", "anthropic") else "function_calling"
        structured_llm = llm.with_structured_output(ProfileExtractionResult, method=method)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是 EduGraph-Agent 的学生画像抽取器。"
                    "你的任务是从学生本轮输入中抽取画像增量，不是回答学生问题。"
                    "必须严格输出符合 schema 的 JSON，且必须包含以下全部顶层字段：\n"
                    '  "background": 对象或 null\n'
                    '  "learning_goal": 对象或 null\n'
                    '  "known_topics": 数组（如无新增则为 []）\n'
                    '  "unknown_topics": 数组（如无新增则为 []）\n'
                    '  "preferences": 对象或 null\n'
                    '  "cognitive_style": 对象或 null\n'
                    '  "self_reported_weak_points": 数组（如无新增则为 []）\n'
                    '  "ability_signals": 对象（如无信号则为 {{}}）\n'
                    '  "confidence": 数字 0-1\n'
                    '  "confidence_notes": 数组\n\n'
                    "模式说明：\n"
                    "- initialization: 首次建档，尽量抽取明确出现的背景、目标、已学课程、偏好、自述薄弱点。\n"
                    "- update: 后续补充，只抽取相对于已有画像新增、修正或冲突的信息，不要重复已有字段。\n\n"
                    "硬性规则：\n"
                    "1. 只抽取学生明确表达的信息，不要脑补。\n"
                    "2. 不要输出 progress。\n"
                    "3. 不要输出 diagnosed weak points。\n"
                    "4. 不要编造 node_id；薄弱点只输出自然语言 topic。\n"
                    "5. ability_signals 只能作为低置信度信号，不能代表最终诊断。\n"
                    "6. 学生自述学过某主题时，known_topics 的 level 最高通常只能到 basic/intermediate。\n"
                    "7. 如果没有新增信息，返回空增量结构但务必包含所有顶层字段。\n"
                    "8. confidence 字段必须填写，不可省略或设为 null。",
                ),
                (
                    "human",
                    "抽取模式：{mode}\n\n"
                    "当前已有画像：\n{existing_profile}\n\n"
                    "本轮学生输入：\n{student_message}\n\n"
                    "请输出画像增量 JSON。",
                ),
            ]
        )
        self._chain = prompt | structured_llm
        return self._chain


def _compact_profile(profile: StudentProfile) -> dict[str, Any]:
    return {
        "student_id": profile.student_id,
        "background": profile.background.model_dump(mode="json"),
        "learning_goal": profile.learning_goal.model_dump(mode="json"),
        "knowledge_base": profile.knowledge_base.model_dump(mode="json"),
        "cognitive_style": profile.cognitive_style.model_dump(mode="json"),
        "weak_points": profile.weak_points.model_dump(mode="json"),
        "preferences": profile.preferences.model_dump(mode="json"),
        "ability_state": profile.ability_state.model_dump(mode="json"),
        "node_mastery": {
            key: value.model_dump(mode="json")
            for key, value in profile.node_mastery.items()
        },
    }
