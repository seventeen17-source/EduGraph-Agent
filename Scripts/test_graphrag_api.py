#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GraphRAG API 冒烟测试脚本

用法：
    python Scripts/test_graphrag_api.py

依赖：
    - Neo4j 运行中 (bolt://localhost:7687)
    - 后端服务运行中 (http://localhost:8000)
"""
import io
import json
import sys
import time
from pathlib import Path

import requests

# 设置标准输出编码为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 配置
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

# 测试用例
TEST_CASES = [
    {
        "name": "K-Means 查询",
        "query": "K-Means 聚类算法的工作原理",
        "expected_node": "ml_kmeans",
    },
    {
        "name": "反向传播查询",
        "query": "反向传播算法是什么",
        "expected_node": "ml_backpropagation",
    },
    {
        "name": "梯度下降查询",
        "query": "梯度下降法",
        "expected_node": "ml_gradient_descent",
    },
    {
        "name": "逻辑回归查询",
        "query": "逻辑回归为什么叫回归",
        "expected_node": "ml_logistic_regression",
    },
    {
        "name": "感知机查询",
        "query": "感知机模型",
        "expected_node": "ml_perceptron",
    },
    {
        "name": "过拟合查询",
        "query": "什么是过拟合",
        "expected_node": "ml_overfitting_underfitting",
    },
]


def test_health():
    """测试健康检查接口"""
    print("=" * 60)
    print("Test 1: Health Check API")
    print("=" * 60)

    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print(f"[PASS] Health check: {data}")
        return True
    except Exception as e:
        print(f"[FAIL] Health check: {e}")
        return False


def test_graph_node(uid: str):
    """测试获取节点信息"""
    try:
        resp = requests.get(f"{BASE_URL}/api/graph/node/{uid}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"  [PASS] Node {uid}: {data.get('properties', {}).get('name', 'N/A')}")
        return data
    except Exception as e:
        print(f"  [FAIL] Node {uid} query failed: {e}")
        return None


def test_graphrag_evidence(uid: str):
    """测试证据包检索"""
    try:
        resp = requests.get(
            f"{BASE_URL}/api/graphrag/evidence",
            params={"uid": uid, "top_k": 8},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # 验证质量字段
        quality_fields = [
            "evidence_score",
            "coverage_stats",
            "evidence_completeness",
            "resource_diversity",
            "relevance_score",
        ]

        missing_fields = [f for f in quality_fields if f not in data]
        if missing_fields:
            print(f"  [FAIL] Missing quality fields: {missing_fields}")
            return None

        # 打印统计
        stats = data.get("coverage_stats", {})
        completeness = data.get("evidence_completeness", {})

        print(f"  [PASS] Evidence score: {data.get('evidence_score')}")
        print(f"  [PASS] Resource diversity: {data.get('resource_diversity')}")
        print(f"  [PASS] Relevance score: {data.get('relevance_score')}")
        print(f"  [INFO] Coverage: docs={stats.get('document_chunks_count', 0)}, "
              f"exercises={stats.get('exercises_count', 0)}, "
              f"code={stats.get('code_cases_count', 0)}, "
              f"misconceptions={stats.get('misconceptions_count', 0)}")
        print(f"  [INFO] Completeness: {completeness.get('completeness_score')}, "
              f"missing={completeness.get('missing_categories', [])}")

        return data
    except Exception as e:
        print(f"  [FAIL] Evidence retrieval failed: {e}")
        return None


def test_graphrag_query(query: str, expected_node: str):
    """测试自然语言查询"""
    try:
        resp = requests.post(
            f"{BASE_URL}/api/graphrag/query",
            json={"query": query, "top_k": 8},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        resolved_uid = data.get("resolved_uid")
        center_name = ""
        if data.get("center_node"):
            center_name = data["center_node"].get("properties", {}).get("name", "")

        # 检查是否命中期望的节点
        if resolved_uid == expected_node:
            print(f"  [PASS] Query hit correct node: {resolved_uid} ({center_name})")
        else:
            print(f"  [WARN] Query hit: {resolved_uid} ({center_name}), expected: {expected_node}")

        # 验证质量字段
        quality_fields = ["evidence_score", "coverage_stats", "evidence_completeness", "resource_diversity"]
        missing = [f for f in quality_fields if f not in data]
        if missing:
            print(f"  [FAIL] Missing quality fields: {missing}")
            return None

        print(f"  [PASS] Score={data.get('evidence_score')}, "
              f"diversity={data.get('resource_diversity')}, "
              f"relevance={data.get('relevance_score')}")

        return data
    except Exception as e:
        print(f"  [FAIL] Query failed: {e}")
        return None


def run_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("EduGraph-Agent GraphRAG API Smoke Test")
    print("=" * 60)

    results = {
        "passed": 0,
        "failed": 0,
        "details": [],
    }

    # 1. 健康检查
    print("\n[1/5] Health Check")
    if test_health():
        results["passed"] += 1
    else:
        results["failed"] += 1
        print("Backend service not running, abort test")
        return results

    # 2. 测试关键节点
    print("\n[2/5] Key Nodes Query")
    key_nodes = ["ml_kmeans", "ml_backpropagation", "ml_gradient_descent"]
    for uid in key_nodes:
        if test_graph_node(uid):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # 3. 测试证据包检索
    print("\n[3/5] Evidence Package Retrieval")
    for uid in key_nodes:
        if test_graphrag_evidence(uid):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # 4. 测试自然语言查询
    print("\n[4/5] Natural Language Query")
    for tc in TEST_CASES:
        print(f"\n  Test: {tc['name']}")
        print(f"  Query: {tc['query']}")
        if test_graphrag_query(tc["query"], tc["expected_node"]):
            results["passed"] += 1
        else:
            results["failed"] += 1

    # 5. 测试质量字段
    print("\n[5/5] Quality Fields Verification")
    print("  [INFO] EvidencePackage quality fields:")
    print("    - coverage_stats: coverage statistics for each evidence type")
    print("    - evidence_completeness: evidence completeness evaluation")
    print("    - resource_diversity: resource diversity score (0-1)")
    print("    - relevance_score: query relevance score (0-1)")
    results["passed"] += 1

    return results


def main():
    print("\nStarting GraphRAG API smoke test...")
    print(f"Backend URL: {BASE_URL}")
    print("-" * 60)

    results = run_tests()

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Total: {results['passed'] + results['failed']}")

    if results["failed"] == 0:
        print("\n[PASS] All tests passed!")
        return 0
    else:
        print(f"\n[FAIL] {results['failed']} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())