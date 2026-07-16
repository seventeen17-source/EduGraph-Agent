from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from Scripts.import_to_neo4j import parse_code_case, parse_doc_chunks
from app.rag.schemas import CourseSemanticView

logger = logging.getLogger(__name__)


ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
COURSE_DIR = DATA_DIR / "course"
DOCS_DIR = DATA_DIR / "docs"
EXERCISES_DIR = DATA_DIR / "exercises"
FAQ_PATH = DATA_DIR / "faq" / "misconceptions.json"
CODE_CASES_DIR = DATA_DIR / "code_cases"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _clean_text(value: Any, max_len: int = 1200) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:max_len]


def _append_view(
    views: list[CourseSemanticView],
    *,
    view_id: str,
    text: str,
    target_uid: str,
    target_type: str,
    view_type: str,
    node_ids: list[str],
    chapter_id: str = "",
    source_uids: list[str] | None = None,
    title: str = "",
    difficulty: int | None = None,
    cognitive_level: str = "",
    tags: list[str] | None = None,
) -> None:
    text = _clean_text(text)
    if not text:
        return
    views.append(
        CourseSemanticView(
            id=view_id,
            text=text,
            target_uid=target_uid,
            target_type=target_type,  # type: ignore[arg-type]
            view_type=view_type,  # type: ignore[arg-type]
            node_ids=list(dict.fromkeys([node for node in node_ids if node])),
            chapter_id=chapter_id,
            source_uids=list(dict.fromkeys(source_uids or [])),
            title=title,
            difficulty=difficulty,
            cognitive_level=cognitive_level,
            tags=list(dict.fromkeys(tags or [])),
        )
    )


def build_course_semantic_views(root: Path | None = None) -> list[CourseSemanticView]:
    """Build semantic retrieval views from canonical course data.

    These views are an index layer only: each view points back to a canonical
    target_uid that should be fetched from Neo4j before being used as evidence.
    """

    root = root or ROOT
    data_dir = root / "data"
    course_dir = data_dir / "course"
    docs_dir = data_dir / "docs"
    exercises_dir = data_dir / "exercises"
    faq_path = data_dir / "faq" / "misconceptions.json"
    code_cases_dir = data_dir / "code_cases"

    views: list[CourseSemanticView] = []
    knowledge_points = _load_json(course_dir / "knowledge_points.json")
    node_name_by_id = {
        item.get("node_id", ""): item.get("name") or item.get("title") or item.get("node_id", "")
        for item in knowledge_points
    }

    # ── 优先使用 LLM 生成的知识点视图 ──
    llm_views_path = course_dir / "kp_llm_views.json"
    if llm_views_path.exists():
        llm_views_raw = _load_json(llm_views_path)
        for item in llm_views_raw:
            uid = item.get("target_uid", "")
            _append_view(
                views,
                view_id=f"sv_{uid}_{item.get('angle', '')}",
                text=item.get("text", ""),
                target_uid=uid,
                target_type="KnowledgePoint",
                view_type="concept_explanation",
                node_ids=[uid],
                chapter_id=item.get("chapter_id", ""),
                title=item.get("target_name", uid),
                tags=item.get("keywords", []),
            )
        logger.info(f"加载 {len(llm_views_raw)} 条 LLM 知识点视图")
    else:
        # 回退：模板生成
        for item in knowledge_points:
            node_id = item.get("node_id", "")
            name = item.get("name") or item.get("title") or node_id
            keywords = item.get("keywords") or []
            chapter_id = item.get("chapter_id", "")
            _append_view(
                views, view_id=f"sv_{node_id}_concept",
                text=f"概念解释：{name}。关键词：{'、'.join(map(str, keywords))}。定义：{item.get('description', '')}",
                target_uid=node_id, target_type="KnowledgePoint",
                view_type="concept_explanation", node_ids=[node_id],
                chapter_id=chapter_id, title=str(name), tags=[str(t) for t in keywords],
            )

    if faq_path.exists():
        for faq in _load_json(faq_path):
            faq_id = faq.get("faq_id", "")
            node_id = faq.get("related_node_id", "")
            node_name = node_name_by_id.get(node_id, node_id)
            question = faq.get("question", "")
            answer = faq.get("answer", "")
            misconception = faq.get("misconception", "")
            sources = faq.get("source_ids") or []
            _append_view(
                views,
                view_id=f"sv_{faq_id}_confusion",
                text=f"学生困惑：{question}。常见误区：{misconception}。关联知识点：{node_name}",
                target_uid=faq_id,
                target_type="Misconception",
                view_type="student_confusion",
                node_ids=[node_id],
                source_uids=sources,
                title=question,
                tags=["faq", "misconception"],
            )
            _append_view(
                views,
                view_id=f"sv_{faq_id}_explain",
                text=f"解释需求：请解释{question}。正确理解：{answer}",
                target_uid=faq_id,
                target_type="Misconception",
                view_type="concept_explanation",
                node_ids=[node_id],
                source_uids=sources,
                title=question,
                tags=["faq"],
            )

    for doc_path in sorted(docs_dir.glob("*.md")):
        for chunk in parse_doc_chunks(doc_path):
            chunk_id = chunk.get("chunk_id", "")
            node_id = chunk.get("knowledge_node_id", "")
            title = chunk.get("title") or chunk.get("section_title") or chunk_id
            content = chunk.get("content", "")
            keywords = [str(item) for item in chunk.get("keywords", [])]
            sources = chunk.get("source_ids") or []
            chapter_id = chunk.get("chapter_id", "")
            _append_view(
                views,
                view_id=f"sv_{chunk_id}_summary",
                text=f"讲义片段：{title}。核心内容：{content}。关键词：{'、'.join(keywords)}",
                target_uid=chunk_id,
                target_type="DocumentChunk",
                view_type="raw_summary",
                node_ids=[node_id],
                chapter_id=chapter_id,
                source_uids=sources,
                title=title,
                tags=keywords,
            )
            _append_view(
                views,
                view_id=f"sv_{chunk_id}_question",
                text=f"解释需求：请用直觉、公式和例子解释{title}。我不理解{title}里的关键概念。",
                target_uid=chunk_id,
                target_type="DocumentChunk",
                view_type="concept_explanation",
                node_ids=[node_id],
                chapter_id=chapter_id,
                source_uids=sources,
                title=title,
                tags=keywords,
            )

    if exercises_dir.exists():
        for chapter_file in sorted(exercises_dir.glob("ch*.json")):
            payload = _load_json(chapter_file)
            chapter_id = payload.get("chapter_id", "")
            for exercise in payload.get("exercises", []):
                exercise_id = exercise.get("exercise_id", "")
                node_ids = [
                    exercise.get("related_node_id", ""),
                    *exercise.get("assesses", []),
                    *exercise.get("also_assesses", []),
                    *exercise.get("prerequisite_node_ids", []),
                ]
                title = exercise.get("title") or exercise_id
                question = exercise.get("question", "")
                answer = exercise.get("answer") or {}
                explanation = answer.get("explanation") or answer.get("reference_answer") or ""
                tags = [str(item) for item in exercise.get("misconception_tags", []) + exercise.get("tags", [])]
                _append_view(
                    views,
                    view_id=f"sv_{exercise_id}_diagnosis",
                    text=f"错题诊断：{question}。如果我做错了这道题，可能是哪里理解错了？解析：{explanation}",
                    target_uid=exercise_id,
                    target_type="Exercise",
                    view_type="error_diagnosis",
                    node_ids=node_ids,
                    chapter_id=chapter_id,
                    source_uids=exercise.get("source_ids") or [],
                    title=title,
                    difficulty=exercise.get("difficulty"),
                    cognitive_level=exercise.get("cognitive_level", ""),
                    tags=tags,
                )

    if code_cases_dir.exists():
        for code_path in sorted(code_cases_dir.glob("*.py")):
            code_case = parse_code_case(code_path)
            code_id = code_case.get("code_case_id", "")
            node_id = code_case.get("related_node_id", "")
            title = code_case.get("title") or code_id
            content = code_case.get("content", "")
            functions = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", content)
            excerpt = "\n".join(content.splitlines()[:40])
            _append_view(
                views,
                view_id=f"sv_{code_id}_intent",
                text=(
                    f"代码意图：如何用 Python 实现{title}？这个案例关联{node_name_by_id.get(node_id, node_id)}。"
                    f"核心函数：{'、'.join(functions[:6])}。代码片段：{excerpt}"
                ),
                target_uid=code_id,
                target_type="CodeCase",
                view_type="code_intent",
                node_ids=[node_id],
                source_uids=code_case.get("source_ids") or [],
                title=title,
                tags=["code", "python", *functions[:6]],
            )

    return views
