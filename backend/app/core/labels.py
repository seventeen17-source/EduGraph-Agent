"""User-facing labels for graph ids and backend enum values."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parents[3]
_KNOWLEDGE_POINTS_PATH = _ROOT / "data" / "course" / "knowledge_points.json"

_STATIC_NODE_LABELS: dict[str, str] = {
    "ml_backpropagation": "反向传播",
    "ml_gradient_descent": "梯度下降",
    "ml_kmeans": "K均值聚类",
    "ml_linear_regression": "线性回归",
    "ml_logistic_regression": "逻辑回归",
    "ml_multilayer_neural_network": "多层神经网络",
    "ml_overfitting_underfitting": "过拟合与欠拟合",
}

_GENERAL_LABELS: dict[str, str] = {
    "self_reported": "学生自述",
    "diagnosed": "练习诊断",
    "mastery": "掌握度计算",
    "exercise_result": "练习结果",
    "forgetting_detection": "遗忘检测",
    "dialogue_rule": "对话规则抽取",
    "llm_profile_extractor": "大模型画像抽取",
    "llm_rubric": "智能逐点评分",
    "llm_code_rubric": "智能代码评分",
    "student_profile_weak_point_fallback": "按学生薄弱点降级检索",
    "fallback_used": "使用降级方案",
    "source_uids": "证据来源",
    "resolved_uid": "定位知识点",
    "grounded": "证据支撑",
    "repair_actions": "修复动作",
}

_INTERNAL_PREFIX_LABELS: dict[str, str] = {
    "ml": "相关知识点",
    "faq": "FAQ 证据",
    "chunk": "文档证据",
    "code": "代码案例",
    "ex": "练习题",
    "assess": "测评证据",
    "source": "课程来源",
    "book": "教材来源",
    "mem": "学习记忆",
    "session": "练习记录",
    "attempt": "作答记录",
}

_INTERNAL_ID_RE = re.compile(r"\b(?:ml|faq|chunk|code|ex|assess|source|book|mem|session|attempt)_[A-Za-z0-9_-]+\b")


@lru_cache(maxsize=1)
def node_label_map() -> dict[str, str]:
    labels = dict(_STATIC_NODE_LABELS)
    try:
        items = json.loads(_KNOWLEDGE_POINTS_PATH.read_text(encoding="utf-8"))
        for item in items:
            node_id = str(item.get("node_id") or "").strip()
            name = str(item.get("name") or "").strip()
            if node_id and name:
                labels[node_id] = name
    except Exception:
        pass
    return labels


def is_internal_id(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return text in node_label_map() or bool(_INTERNAL_ID_RE.fullmatch(text))


def internal_id_label(value: Any, fallback: str = "相关内容") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    labels = node_label_map()
    if text in labels:
        return labels[text]
    prefix = text.split("_", 1)[0]
    return _INTERNAL_PREFIX_LABELS.get(prefix, fallback)


def node_label(node_id: Any, fallback: str = "相关知识点") -> str:
    if node_id is None:
        return fallback
    text = str(node_id).strip()
    if not text:
        return fallback
    return internal_id_label(text, fallback) if is_internal_id(text) else localize_text(text)


def choose_node_label(name: Any, node_id: Any = None, fallback: str = "相关知识点") -> str:
    if name is not None:
        text = str(name).strip()
        if text:
            return node_label(text, fallback=fallback) if is_internal_id(text) else localize_text(text)
    return node_label(node_id, fallback=fallback)


def localize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    replacements: dict[str, str] = {}
    replacements.update(_GENERAL_LABELS)
    replacements.update(node_label_map())
    for key in sorted(replacements, key=len, reverse=True):
        text = text.replace(key, replacements[key])
    return _INTERNAL_ID_RE.sub(lambda m: internal_id_label(m.group(0)), text)
