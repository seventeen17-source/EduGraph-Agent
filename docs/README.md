# EduGraph-Agent 文档索引

## 项目文档

- [需求分析说明书](project/需求分析说明书.md)
- [A3 初步开发文档](project/A3_initial_development_doc.md)
- [A3 开发时间表](project/A3_development_schedule.md)
- [项目进度台账](project/PROJECT_PROGRESS.md) — **2026-07-08 更新**
- [课程语义 RAG 建设计划](project/课程语义RAG建设计划.md) — Chroma 语义入口层、Neo4j canonical evidence 回灌、嵌入模型选择、P0/P1/P2 路线
- [系统可用化审查与改造路线](project/系统可用化审查与改造路线.md) — 基于当前代码复审，区分已完成、需硬化和待增强事项
- [Hybrid RAG 与 GraphRAG 融合升级方案](project/HybridRAG与GraphRAG融合升级方案.md) — 三路召回、统一重排、证据质量评估、fallback 分级和 LangGraph 检索子图
- [演示前检查清单](project/演示前检查清单.md)
- [启动服务说明](../启动服务.md)

## 后端文档

- [FastAPI 后端 README](../backend/README.md) — 含认证/助手/画像/GraphRAG/AI备课/诊断全部 API

## 知识库文档

- [机器学习课程知识库收集指南](knowledge-base/ML_知识库收集指南.md)
- [graph_edges 设计方案](knowledge-base/graph_edges_设计方案.md)
- [数据收集操作手册](knowledge-base/数据收集操作手册.md)
- [学生画像模块设计方案](knowledge-base/学生画像模块设计方案.md)

## 数据讲义文档

位于 `data/docs/`，用于知识库正文与 GraphRAG 检索：

- `ch01_intro_evaluation.md`
- `ch02_math_optimization.md`
- `ch03_linear_models_optimization.md`
- `ch04_supervised_algorithms.md`
- `ch05_unsupervised_representation.md`
- `ch06_neural_deep_learning.md`
- `ch07_learning_theory.md`
- `ch08_semi_supervised.md`
- `ch09_probabilistic_graphical_models.md`
- `ch10_rule_learning.md`
- `ch11_reinforcement_learning.md`
