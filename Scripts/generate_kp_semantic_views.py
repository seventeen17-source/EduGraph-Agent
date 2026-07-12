"""用 LLM 为每个知识点生成 14 条多视角语义视图。

每条视图是学生口吻的自然语言描述/提问/困惑/辨析/应用，
用于构建语义索引（ChromaDB），配合 Neo4j 做混合 GraphRAG。

用法：
  python Scripts/generate_kp_semantic_views.py --dry-run
  python Scripts/generate_kp_semantic_views.py --output data/course/kp_llm_views.json
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import sys
from pathlib import Path

# 修复 Windows GBK 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from neo4j import AsyncGraphDatabase  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402


# ━━━ 提示词 ━━━

SYSTEM_PROMPT = """你是 EduGraph-Agent 的学习内容生成器。你的任务是为一个机器学习知识点生成 14 条不同视角的自然语言描述，用于构建语义检索索引。

## 核心要求
- **每条 150-400 字**，有实质内容，不凑字数
- **学生口吻**——不是教科书定义，而是学生理解/提问/困惑/应用时说的话
- **不重复 Neo4j 已有的结构化数据**——你生成的是自然语言视角，不是 key-value 式的定义
- **结合提供的文档原文**——尽量从文档原文中提取关键细节融入输出
- **每条独立有价值**——即使只命中一条，也足以帮助学生理解相关知识

## 14 个视角

### 概念理解（3 条）
1. **直觉解释** — 用类比/比喻/生活例子解释核心概念，让完全不懂的人也能大致理解
2. **一句话总结** — 用最精炼的一句话概括这个概念的本质，适合记住
3. **解决什么问题** — 说明这个概念是为了解决什么实际问题而提出的，没有它会有什么后果

### 动手实践（2 条）
4. **推导步骤** — 列出核心推导的关键步骤，每一步用一两句话解释，适合"手推一遍"的需求
5. **代码实现** — 用 Python/PyTorch 等说明怎么用代码实现或调用，核心 API 或关键代码片段

### 概念辨析（2 条）
6. **易混对比** — 对比一个最容易和这个概念混淆的其他概念，说清楚区别和联系
7. **常见误区** — 描述一个初学者常见的理解错误，然后纠正它

### 应用场景（3 条）
8. **面试问答** — 模拟一道典型面试题，给出回答思路和要点
9. **选型指南** — 说明在什么场景下需要深入理解这个概念，什么场景下只需知道大概
10. **适用范围** — 说明这个概念的前提假设和局限性，什么情况下不适用

### 学习路径（2 条）
11. **前置引导** — 列出学好这个概念之前需要掌握的前置知识，以及为什么需要它们
12. **后续延伸** — 理解这个概念之后，可以接着学什么，它们之间有什么联系

### 跨概念关联（2 条）
13. **上下游串联** — 把这个概念放在更大的知识网络里，说明它和前后知识点的关系
14. **平行对比** — 对比一个和这个概念同级别的其他方法/算法，说明各自优缺点

## 输出格式
严格输出 JSON 数组，包含 14 个对象，每个对象有 angle 和 text 两个字段：
[
  {"angle": "直觉解释", "text": "..."},
  {"angle": "一句话总结", "text": "..."},
  ...
  {"angle": "平行对比", "text": "..."}
]
不要输出其他内容，只输出 JSON 数组。"""


# ━━━ Neo4j 数据提取 ━━━


async def fetch_knowledge_point(driver, uid: str) -> dict:
    """从 Neo4j 提取一个知识点的全部可用数据。"""
    async with driver.session() as session:
        # 知识点本体
        r = await session.run(
            "MATCH (k:KnowledgePoint {uid: $uid}) RETURN properties(k) as props", uid=uid
        )
        row = await r.single()
        if not row:
            return {}
        props = row["props"]

        # 关联的文档块
        r2 = await session.run(
            """MATCH (c:DocumentChunk)-[:SUPPORTS]->(k:KnowledgePoint {uid: $uid})
               RETURN c.content as content ORDER BY size(c.content) DESC LIMIT 3""",
            uid=uid,
        )
        doc_texts = [row["content"] async for row in r2 if row.get("content")]

        # 前置知识点的名称
        r3 = await session.run(
            """MATCH (pre:KnowledgePoint)-[:PREREQUISITE]->(k:KnowledgePoint {uid: $uid})
               RETURN pre.uid as uid, pre.name as name""",
            uid=uid,
        )
        prereqs = [{"uid": row["uid"], "name": row["name"]} async for row in r3]

    return {
        "uid": uid,
        "name": props.get("name", uid),
        "summary": props.get("summary", ""),
        "keywords": props.get("keywords", []),
        "mastery_objectives": props.get("mastery_objectives", []),
        "common_misconceptions": props.get("common_misconceptions", []),
        "difficulty": props.get("difficulty", 3),
        "prerequisites": prereqs,
        "doc_chunks": doc_texts,
    }


def build_kp_context(kp: dict) -> str:
    """构建给 LLM 的输入上下文。"""
    parts = [
        f"## 知识点：{kp['name']}",
        f"- 摘要：{kp['summary']}",
        f"- 关键词：{', '.join(kp['keywords'][:8])}",
        f"- 难度：{kp['difficulty']} 星",
    ]
    if kp.get("mastery_objectives"):
        parts.append(f"- 掌握目标：{'；'.join(kp['mastery_objectives'][:3])}")
    if kp.get("common_misconceptions"):
        parts.append(f"- 常见误区：{'；'.join(kp['common_misconceptions'][:3])}")
    if kp.get("prerequisites"):
        names = [p["name"] for p in kp["prerequisites"][:5]]
        parts.append(f"- 前置知识：{'、'.join(names)}")

    if kp.get("doc_chunks"):
        parts.append("\n## 讲义原文")
        for i, doc in enumerate(kp["doc_chunks"][:2], 1):
            parts.append(f"\n### 文档片段 {i}\n{doc[:2000]}")

    return "\n".join(parts)


# ━━━ LLM 调用 ━━━


async def generate_views_for_kp(kp: dict, llm) -> list[dict] | None:
    """为一个知识点生成 14 条语义视图。"""
    context = build_kp_context(kp)
    try:
        result = await llm.ainvoke(
            [("system", SYSTEM_PROMPT), ("human", f"请基于以下数据生成 14 条不同视角的自然语言描述：\n\n{context}")],
        )
        text = result.content if hasattr(result, "content") else str(result)
        # 清理可能的 markdown 代码块包裹
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if lines[0].startswith("```") else text
            if text.endswith("```"):
                text = text[:-3]
        text = text.strip()
        # 修复 LLM 输出中的非法控制字符（保留 \n \r \t）
        import re
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        views = json.loads(text)
        if isinstance(views, list) and len(views) > 0:
            return views
    except Exception as exc:
        print(f"  ✗ {kp['name']}: {type(exc).__name__}: {exc}")
    return None


# ━━━ 主流程 ━━━


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只生成第一个知识点并打印")
    parser.add_argument("--output", default="data/course/kp_llm_views.json", help="输出文件")
    parser.add_argument("--limit", type=int, default=0, help="限制知识点数量（0=全部）")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.llm_api_key:
        print("ERROR: LLM_API_KEY 未配置")
        sys.exit(1)

    # LLM
    llm_kwargs = {
        "model": settings.llm_model,
        "api_key": settings.llm_api_key,
        "temperature": 0.3,
    }
    if settings.llm_base_url:
        llm_kwargs["base_url"] = settings.llm_base_url
    llm = ChatOpenAI(**llm_kwargs)

    # Neo4j
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    # 获取所有知识点
    async with driver.session(database=settings.neo4j_database) as session:
        r = await session.run(
            "MATCH (k:KnowledgePoint) RETURN k.uid as uid, k.name as name ORDER BY k.name"
        )
        all_kps = [{"uid": row["uid"], "name": row["name"]} async for row in r]

    if args.limit > 0:
        all_kps = all_kps[: args.limit]

    print(f"知识点总数: {len(all_kps)}")
    print(f"LLM 模型: {settings.llm_model}")
    print(f"输出文件: {args.output}")
    print()

    if args.dry_run:
        # 只跑第一个
        kp = all_kps[0]
        print(f"=== 测试: {kp['name']} ({kp['uid']}) ===")
        full = await fetch_knowledge_point(driver, kp["uid"])
        print(build_kp_context(full))
        print("\n--- 生成视图 ---")
        views = await generate_views_for_kp(full, llm)
        if views:
            print(json.dumps(views, ensure_ascii=False, indent=2))
            print(f"\n生成 {len(views)} 条视图")
        else:
            print("生成失败")
        await driver.close()
        return

    # 全量生成
    all_views: list[dict] = []
    total = len(all_kps)
    for i, kp in enumerate(all_kps):
        name = kp["name"]
        print(f"[{i+1}/{total}] {name} ...", end=" ", flush=True)
        full = await fetch_knowledge_point(driver, kp["uid"])
        if not full.get("summary"):
            print("(skip: no data)")
            continue

        views = await generate_views_for_kp(full, llm)
        if views:
            # 包装为 CourseSemanticView
            for v in views:
                all_views.append({
                    "target_uid": full["uid"],
                    "target_name": name,
                    "angle": v.get("angle", ""),
                    "text": v.get("text", ""),
                    "chapter_id": full.get("chapter_id", ""),
                    "difficulty": full.get("difficulty"),
                    "keywords": full.get("keywords", [])[:5],
                })
            print(f"✓ {len(views)} views")
        else:
            print("✗ failed")

    await driver.close()

    # 保存
    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(all_views, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n保存 {len(all_views)} 条视图到 {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
