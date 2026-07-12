#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试助手对话 API
"""
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests

BASE_URL = "http://localhost:8000"

def test_assistant_chat():
    print("=" * 60)
    print("测试助手对话 - 生成选择题")
    print("=" * 60)

    # 先登录获取 token
    login_resp = requests.post(
        f"{BASE_URL}/api/auth/demo",
        json={}
    )
    if login_resp.status_code != 200:
        print(f"登录失败: {login_resp.status_code} - {login_resp.text[:200]}")
        return

    token = login_resp.json().get("access_token", {})
    if isinstance(token, dict):
        token = token.get("token", "")
    print(f"获取到 token: {token[:30]}...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 测试非流式对话
    payload = {
        "message": "帮我生成五道有关神经网络的选择题",
        "student_id": "demo_student_001"
    }

    print(f"\n发送请求: {json.dumps(payload, ensure_ascii=False)}")

    try:
        resp = requests.post(
            f"{BASE_URL}/api/assistant/chat",
            json=payload,
            headers=headers,
            timeout=120
        )
        print(f"\n状态码: {resp.status_code}")

        if resp.status_code != 200:
            print(f"错误响应: {resp.text[:500]}")
            return

        data = resp.json()

        print(f"\n=== 响应内容 ===")
        reply = data.get("reply", "")
        print(f"回复长度: {len(reply)} 字符")
        print(f"回复内容:\n{reply[:2000]}")

        print(f"\n=== 意图信息 ===")
        print(f"intent: {data.get('intent')}")
        print(f"target_node_id: {data.get('evidence', {}).get('resolved_uid') if data.get('evidence') else 'N/A'}")

        print(f"\n=== 资源信息 ===")
        resources = data.get("resources", {})
        if resources:
            exercises = resources.get("exercises", [])
            print(f"练习题数量: {len(exercises)}")
            for i, ex in enumerate(exercises[:3], 1):
                print(f"  题目 {i}: {ex.get('title', 'N/A')}")
                print(f"    选项数: {len(ex.get('options', []))}")
                print(f"    答案: {ex.get('answer', {})}")
        else:
            print("resources: None 或为空")

        print(f"\n=== Agent Trace ===")
        for t in data.get("agent_trace", []):
            print(f"  [{t.get('status', '?')}] {t.get('node', t.get('agent', '?'))}: {t.get('summary', '')[:60]}")

        print(f"\n=== resource_record_id ===")
        print(f"  {data.get('resource_record_id', 'None')}")

    except Exception as e:
        print(f"\n异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_assistant_chat()
