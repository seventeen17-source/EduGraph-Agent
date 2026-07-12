#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
资源生成调试脚本
"""
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests

BASE_URL = "http://localhost:8000"

def test_resource_generation():
    print("=" * 60)
    print("测试资源生成接口")
    print("=" * 60)

    payload = {
        "query": "神经网络",
        "resource_types": ["exercise"],
        "exercise_count": 3,
        "exercise_type": "choice"
    }

    print(f"\n请求: {json.dumps(payload, ensure_ascii=False, indent=2)}")

    try:
        resp = requests.post(
            f"{BASE_URL}/api/agents/generate-resources",
            json=payload,
            timeout=120
        )
        print(f"\n状态码: {resp.status_code}")

        if resp.status_code != 200:
            print(f"错误响应: {resp.text[:500]}")
            return

        data = resp.json()

        print(f"\n=== 响应摘要 ===")
        print(f"resolved_uid: {data.get('resolved_uid')}")
        print(f"center_node: {data.get('center_node', {}).get('properties', {}).get('name', 'N/A')}")
        print(f"resolution_quality: {data.get('resolution_quality')}")
        print(f"resolution_notice: {data.get('resolution_notice', '')[:200]}")

        print(f"\n=== Agent Trace ===")
        for t in data.get('agent_trace', []):
            print(f"  [{t.get('status')}] {t.get('agent')}: {t.get('summary')}")

        exercises = data.get('resources', {}).get('exercises', [])
        print(f"\n=== 生成的练习题 ({len(exercises)} 道) ===")
        for i, e in enumerate(exercises, 1):
            print(f"\n--- 题目 {i} ---")
            print(f"标题: {e.get('title', 'N/A')}")
            print(f"问题: {e.get('question', 'N/A')[:100]}...")
            print(f"选项数: {len(e.get('options', []))}")
            print(f"答案: {e.get('answer', {})}")

        print(f"\n=== 质量报告 ===")
        qr = data.get('quality_report', {})
        print(f"grounded: {qr.get('grounded')}")
        print(f"score: {qr.get('score')}")
        print(f"warnings: {qr.get('warnings', [])}")

        print(f"\n=== 不确定性 ===")
        print(f"uncertainty: {data.get('uncertainty', [])}")
        print(f"missing_evidence: {data.get('missing_evidence', [])}")

    except Exception as e:
        print(f"\n异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_resource_generation()
