"""
手动 JSON 解析工具 —— 当 LLM API 不支持 structured output (tool_choice / response_format) 时使用。
通过 prompt 引导 LLM 输出 JSON，然后从回复中提取并解析。
"""
import json
import re
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def extract_json_from_text(text: str) -> str:
    """从 LLM 回复中提取 JSON 字符串。"""
    # 先尝试 ```json ``` 代码块
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        json_str = match.group(1).strip()
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
    """从 LLM 回复中提取 JSON 并解析为 Pydantic 模型。"""
    json_str = extract_json_from_text(text)

    try:
        data = json.loads(json_str)
        return output_model.model_validate(data)
    except (json.JSONDecodeError, ValueError) as e:
        import sys
        print(f"[parse_model] JSON loads failed: {e}", file=sys.stderr)
        print(f"[parse_model] json_str[:300]={json_str[:300]}", file=sys.stderr)
        sys.stderr.flush()
        pass

    # 尝试截断修复
    for end_idx in range(len(json_str), max(0, len(json_str) - 1000), -1):
        if json_str[end_idx - 1 : end_idx] in ("}", "]"):
            try:
                data = json.loads(json_str[:end_idx])
                return output_model.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                continue

    # 都失败了，返回空对象
    import sys
    print(f"[parse_model] All parse attempts failed, returning empty {output_model.__name__}", file=sys.stderr)
    sys.stderr.flush()
    return output_model()
