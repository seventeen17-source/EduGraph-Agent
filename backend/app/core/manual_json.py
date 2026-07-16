"""
手动 JSON 解析工具 —— 当 LLM API 不支持 structured output (tool_choice / response_format) 时使用。
通过 prompt 引导 LLM 输出 JSON，然后从回复中提取并解析。
"""
import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> str:
    """从 LLM 回复中提取 JSON 字符串。"""
    # 先尝试 ```json ``` 代码块（用贪婪匹配取最后一个，避免文中 ``` 提前截断）
    matches = list(re.finditer(r'```(?:json)?\s*([\s\S]*?)```', text))
    if matches:
        # 取最后一个（通常是完整的 JSON 块）
        best = max(matches, key=lambda m: len(m.group(1)))
        json_str = best.group(1).strip()
    else:
        # 尝试找 JSON 对象
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            json_str = match.group(0).strip()
        else:
            json_str = text.strip()

    # 清理 thinking 标签
    json_str = re.sub(r'</?think>', '', json_str)
    return json_str.strip()


def parse_model(text: str, output_model: type[T]) -> T:
    """从 LLM 回复中提取 JSON 并解析为 Pydantic 模型。

    如果 JSON 解析失败，会尝试将纯文本内容回填到模型的核心字段中。
    """
    json_str = extract_json_from_text(text)

    try:
        data = json.loads(json_str)
        return output_model.model_validate(data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"JSON loads failed: {e}, json_str[:300]={json_str[:300]}")

    # 尝试截断修复：从末尾往前找合法截断点
    for end_idx in range(len(json_str), max(0, len(json_str) - 2000), -1):
        if json_str[end_idx - 1 : end_idx] in ("}", "]"):
            try:
                data = json.loads(json_str[:end_idx])
                return output_model.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                continue

    # 都失败了，尝试用原始文本内容回填到 content 字段（对文档类特别有用）
    fallback = _try_text_fallback(text, output_model)
    if fallback is not None:
        return fallback

    # 最后返回空对象
    logger.error(f"All parse attempts failed, returning empty {output_model.__name__}")
    return output_model()


def _try_text_fallback(text: str, output_model: type[T]) -> T | None:
    """当 JSON 解析失败时，尝试把 LLM 的纯文本回复直接填入 content 字段。"""
    from app.agents.schemas import GeneratedDocument, GeneratedMindmap

    # 对于 GeneratedDocument：把去除 thinking 标签后的全文作为 content
    if output_model is GeneratedDocument:
        clean = re.sub(r'</?think>', '', text)
        # 移除 JSON 代码块标记，保留中间的文本
        clean = re.sub(r'```(?:json)?\s*', '', clean)
        clean = re.sub(r'```', '', clean)
        # 移除明显的 JSON 结构残留
        clean = re.sub(r'^\s*\{[^}]*"content"\s*:\s*"', '', clean)
        clean = _strip_leaked_json_fields(clean)
        clean = re.sub(r'"[,\s]*\}[,\s]*$', '', clean)
        clean = clean.replace(r'\"', '"').replace(r'\r\n', '\n').replace(r'\n', '\n')
        clean = clean.strip()
        if len(clean) >= 50:
            return output_model(
                title="讲解文档",
                content=clean[:50000],
                source_uids=[],
            )

    # 对于 GeneratedMindmap：尝试提取 mermaid 内容
    if output_model is GeneratedMindmap:
        clean = re.sub(r'</?think>', '', text)
        mermaid_match = re.search(r'(mindmap[\s\S]*?)(?:```|$)', clean)
        if mermaid_match:
            return output_model(
                title="思维导图",
                content=mermaid_match.group(1).strip(),
                source_uids=[],
            )

    return None


def _strip_leaked_json_fields(text: str) -> str:
    """Trim malformed JSON fields that may leak after document.content."""
    pattern = re.compile(
        r'",\s*"(?:(?:代码|code|explanation|learning_objectives|prerequisites|additional_references|证据来源|source_uids|key_points)|[a-z_]{3,})"\s*:',
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if match and match.start() >= 80:
        return text[: match.start()]
    return text
