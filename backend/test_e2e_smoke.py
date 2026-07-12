"""
EduGraph-Agent 端到端冒烟测试
测试完整闭环：Profile -> Diagnosis -> GraphRAG -> Resource Generation -> Knowledge Center
"""

import requests
import json
import time
import sys
import io
import os

# 修复 Windows 控制台编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

def log(msg, ok=None):
    prefix = "[PASS]" if ok == True else ("[FAIL]" if ok == False else "[----]")
    print(f"{prefix} {msg}")

def test_health():
    """1. 健康检查"""
    log("测试健康检查...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        data = r.json()
        assert data["status"] == "ok", f"Unexpected status: {data}"
        log(f"健康检查通过 (Neo4j: {data.get('neo4j', 'unknown')})", True)
        return True
    except Exception as e:
        log(f"健康检查失败: {e}", False)
        return False

def test_graph_node():
    """2. 图谱节点查询"""
    log("测试图谱节点查询 (ml_kmeans)...")
    try:
        r = requests.get(f"{BASE_URL}/api/graph/node/ml_kmeans", timeout=10)
        assert r.status_code == 200, f"Status: {r.status_code}, {r.text}"
        node = r.json()
        assert node["uid"] == "ml_kmeans", f"Unexpected uid: {node.get('uid')}"
        log(f"图谱节点查询通过 (label: {node.get('label', 'N/A')}, type: {node.get('node_type', 'N/A')})", True)
        return True
    except Exception as e:
        log(f"图谱节点查询失败: {e}", False)
        return False

def test_graph_subgraph():
    """3. 图谱子图查询"""
    log("测试图谱子图查询 (ml_kmeans, depth=1)...")
    try:
        r = requests.get(f"{BASE_URL}/api/graph/subgraph/ml_kmeans?depth=1", timeout=10)
        assert r.status_code == 200, f"Status: {r.status_code}, {r.text}"
        subgraph = r.json()
        assert "nodes" in subgraph, "Missing nodes in subgraph"
        # relationships 可能为空（如果数据库中没有 PRACTICES 关系）
        nodes_count = len(subgraph.get("nodes", []))
        rels_count = len(subgraph.get("relationships", []))
        log(f"子图查询通过 (节点: {nodes_count}, 关系: {rels_count})", True)
        return True
    except Exception as e:
        log(f"子图查询失败: {e}", False)
        return False


def test_graphrag_evidence():
    """4. GraphRAG Evidence 查询"""
    log("测试 GraphRAG Evidence (ml_kmeans)...")
    try:
        r = requests.get(f"{BASE_URL}/api/graphrag/evidence?uid=ml_kmeans", timeout=10)
        assert r.status_code == 200, f"Status: {r.status_code}, {r.text}"
        evidence = r.json()
        log(f"Evidence 查询通过 (documents: {len(evidence.get('documents', []))}, exercises: {len(evidence.get('exercises', []))}, faqs: {len(evidence.get('faqs', []))}, code_cases: {len(evidence.get('code_cases', []))})", True)
        return True
    except Exception as e:
        log(f"Evidence 查询失败: {e}", False)
        return False

def test_profile_init():
    """5. 画像初始化"""
    log("测试画像初始化...")
    try:
        payload = {
            "student_id": "smoke_test_student",
            "message": "我是计算机科学专业大一学生，想系统学习机器学习，有 Python 基础",
            "display_name": "冒烟测试学生"
        }
        r = requests.post(f"{BASE_URL}/api/profile/init", json=payload, timeout=15)
        assert r.status_code == 200, f"Status: {r.status_code}, {r.text}"
        response = r.json()
        # ProfileChatResponse 包含 profile 和 reply
        profile = response.get("profile", {})
        assert profile.get("student_id") == "smoke_test_student"
        log(f"画像初始化通过 (student_id: {profile.get('student_id')}, grade: {profile.get('background', {}).get('grade')})", True)
        return profile.get("student_id")
    except Exception as e:
        log(f"画像初始化失败: {e}", False)
        return None

def test_assistant_chat(student_id):
    """6. 学习助手对话 (concept_explain)"""
    log("测试学习助手对话 (意图: 概念解释)...")
    try:
        payload = {
            "student_id": student_id,
            "message": "我总是搞不清 K-Means 为什么要反复更新中心点"
        }
        r = requests.post(f"{BASE_URL}/api/assistant/chat", json=payload, timeout=60)
        assert r.status_code == 200, f"Status: {r.status_code}, {r.text}"
        response = r.json()

        # 检查关键字段 (reply 不是 response)
        assert "reply" in response, "Missing reply field"
        assert "intent" in response, "Missing intent field"
        log(f"对话响应通过 (intent: {response.get('intent')}, reply_length: {len(response.get('reply', ''))})", True)

        # 检查动作追踪
        if "agent_trace" in response and response["agent_trace"]:
            trace = [t.get("node") for t in response["agent_trace"] if "node" in t]
            log(f"Agent trace: {trace}", None)

        return True
    except Exception as e:
        log(f"学习助手对话失败: {e}", False)
        return False


def test_resource_generation():
    """7. 资源生成"""
    log("测试资源生成 (ml_kmeans)...")
    try:
        payload = {
            "student_id": "smoke_test_student",
            "node_id": "ml_kmeans",
            "resource_types": ["document", "mindmap", "exercise"]
        }
        r = requests.post(f"{BASE_URL}/api/agents/generate-resources", json=payload, timeout=120)
        assert r.status_code == 200, f"Status: {r.status_code}, {r.text}"
        result = r.json()

        # 检查资源数量
        resources = result.get("resources", [])
        log(f"资源生成通过 (生成资源数: {len(resources)})", True)

        # 尝试提取 record_id（可能在顶层或 resources 元素中）
        record_id = result.get("resource_record_id")
        if not record_id and resources:
            # resources 可能是字符串列表，无法提取 record_id
            # 只要生成了资源就算成功
            record_id = resources[0] if resources and isinstance(resources[0], str) else None

        # 检查质量报告
        if "quality_report" in result and result["quality_report"]:
            report = result["quality_report"]
            log(f"质量报告 - completeness: {report.get('completeness')}, correctness: {report.get('correctness')}", None)

        return record_id
    except Exception as e:
        log(f"资源生成失败: {e}", False)
        return None

def test_knowledge_center(record_id):
    """8. 知识中心"""
    log(f"测试知识中心 (record_id: {record_id})...")
    try:
        # 获取资源详情
        r = requests.get(f"{BASE_URL}/api/agents/resource-center/{record_id}", timeout=10)
        assert r.status_code == 200, f"Status: {r.status_code}, {r.text}"
        resource = r.json()
        log(f"知识中心详情获取成功 (title: {resource.get('node_id')}, resources: {len(resource.get('resources', []))})", True)
        return True
    except Exception as e:
        log(f"知识中心查询失败: {e}", False)
        return False

def test_profile_dashboard(student_id):
    """9. 画像仪表盘"""
    log(f"测试画像仪表盘 (student_id: {student_id})...")
    try:
        r = requests.get(f"{BASE_URL}/api/profile/{student_id}/dashboard", timeout=10)
        assert r.status_code == 200, f"Status: {r.status_code}, {r.text}"
        dashboard = r.json()
        log(f"仪表盘获取成功 (weak_points: {len(dashboard.get('weak_points', []))}, total_learning_time: {dashboard.get('total_learning_time', 0)})", True)
        return True
    except Exception as e:
        log(f"画像仪表盘查询失败: {e}", False)
        return False

def main():
    print("=" * 60)
    print("EduGraph-Agent 端到端冒烟测试")
    print("=" * 60)

    results = {}

    # 1. 健康检查
    results["health"] = test_health()
    if not results["health"]:
        log("健康检查失败，终止测试", False)
        sys.exit(1)

    # 2-4. GraphRAG 相关
    results["graph_node"] = test_graph_node()
    results["graph_subgraph"] = test_graph_subgraph()
    results["graphrag_evidence"] = test_graphrag_evidence()

    # 5. 画像初始化
    student_id = test_profile_init()
    results["profile_init"] = student_id is not None
    if not student_id:
        log("画像初始化失败，终止测试", False)
        sys.exit(1)

    # 6. 学习助手对话
    results["assistant_chat"] = test_assistant_chat(student_id)

    # 7. 资源生成
    record_id = test_resource_generation()
    results["resource_generation"] = record_id is not None

    # 8. 知识中心
    if record_id:
        results["knowledge_center"] = test_knowledge_center(record_id)

    # 9. 画像仪表盘
    results["profile_dashboard"] = test_profile_dashboard(student_id)

    # 总结
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, ok in results.items():
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}  {name}")
    print(f"\n通过率: {passed}/{total} ({100*passed/total:.1f}%)")

    if passed == total:
        log("全部测试通过！🎉", True)
        sys.exit(0)
    else:
        log(f"有 {total - passed} 项测试失败", False)
        sys.exit(1)

if __name__ == "__main__":
    main()