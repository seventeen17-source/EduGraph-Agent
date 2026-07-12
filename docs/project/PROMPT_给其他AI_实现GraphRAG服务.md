# GraphRAG 服务实现提示词

你现在是一个资深后端 / AI 应用工程师，正在为 `EduGraph-Agent` 项目实现 **GraphRAG 服务 MVP**。

请严格基于以下项目现状和约束工作，不要擅自改方向，不要泛泛而谈。

---

## 一、项目背景

项目名称：`EduGraph-Agent`

项目目标：构建一个基于知识图谱、GraphRAG、多智能体资源生成和学习路径规划的个性化学习系统。

当前课程：**机器学习（Machine Learning）**

当前阶段目标：先实现 **Neo4j-only GraphRAG MVP**，支撑比赛演示闭环。

---

## 二、当前重要约定（必须遵守）

1. **Neo4j 查询节点必须用 `uid`，不是 `id`。**
2. `HAS_*` 关系主要用于工程结构导航。
3. `CONTAINS / PREREQUISITE / RELATED / EXTENDS / CONTRASTS / ASSESSES` 主要用于知识推理和 GraphRAG。
4. `CITES_SOURCE` 用于证据溯源。
5. `SUPPORTS / PRACTICES` 用于资源挂载。
6. 当前优先做 **Neo4j-only GraphRAG**，先不要把向量库、LangGraph、多跳复杂推理做成必须依赖。
7. 必须保留未来扩展空间：
   - Neo4j 图数据库
   - 多跳推理
   - 社区摘要
   - 自动抽图
   - 向量库（Chroma / FAISS）
   - 混合检索
   - LangGraph 多智能体

---

## 三、当前数据现状（必须结合）

当前已经存在并可用的数据：

- `data/course/course_meta.json`
- `data/course/chapters.json`
- `data/course/knowledge_points.json`
- `data/course/graph_edges.json`
- `data/sources/sources.json`
- `data/exercises/exercises_index.json`
- `data/exercises/ch01~ch11*.json`
- `data/docs/ch01~ch11*.md`
- `data/faq/misconceptions.json`
- `data/code_cases/*.py`

当前 Neo4j 已导入成功，包含这些节点类型：

- `Course`
- `Chapter`
- `KnowledgePoint`
- `Exercise`
- `Source`
- `Document`
- `DocumentChunk`
- `CodeCase`
- `FAQ`
- `Misconception`

当前关系包括：

- `CONTAINS`
- `PREREQUISITE`
- `RELATED`
- `EXTENDS`
- `CONTRASTS`
- `ASSESSES`
- `SUPPORTS`
- `PRACTICES`
- `CITES_SOURCE`
- `HAS_CHAPTER`
- `HAS_KNOWLEDGE_POINT`
- `HAS_DOCUMENT`
- `HAS_CHUNK`
- `HAS_EXERCISE`
- `TRACKS_CHAPTER`

当前数据风险：

- `DocumentChunk` 只有很少数量，全文证据层偏弱
- Exercise 已较完整，适合先参与 GraphRAG 的练习推荐与诊断支撑
- 派生关系与领域关系同时存在，GraphRAG 需要有关系白名单，避免噪声扩展

---

## 四、你要实现的目标

实现一个 **GraphRAG 服务 MVP**，目标不是写论文，而是尽快支撑这些场景：

1. 用户直接输入知识点 UID，例如：`ml_kmeans`
2. 用户自然语言提问，例如：`我不理解 K-Means 的迭代过程`
3. 根据学生画像中的 `weak_points` 做个性化检索
4. 在资源生成前，返回一个**可解释 Evidence Package**

---

## 五、你应该优先设计 / 实现的抽象

请围绕以下抽象进行设计，不要跳过：

1. `Neo4jGraphStore`
2. `NodeResolver`
3. `GraphExpansionPolicy`
4. `EvidenceRetriever`
5. `EvidencePackage`
6. `GraphRAGService`

其中：

- `Neo4jGraphStore`：只负责图查询，不做业务编排
- `NodeResolver`：负责把自然语言问题解析到中心知识点
- `GraphExpansionPolicy`：控制可扩展关系、跳数、数量和 weak_points 调权
- `EvidenceRetriever`：从图里收集前置知识、相关知识、题目、文档块、代码案例、来源
- `EvidencePackage`：统一输出结构
- `GraphRAGService`：串联整个流程

---

## 六、必须遵守的 GraphRAG 关系使用规则

### 允许参与知识扩展的关系

- `PREREQUISITE`
- `RELATED`
- `EXTENDS`
- `CONTRASTS`
- `ASSESSES`
- `SUPPORTS`
- `PRACTICES`
- `CITES_SOURCE`（用于来源回溯，不用于认知扩展）

### 不应作为知识推理主关系的类型

- `HAS_CHAPTER`
- `HAS_KNOWLEDGE_POINT`
- `HAS_DOCUMENT`
- `HAS_CHUNK`
- `HAS_EXERCISE`
- `TRACKS_CHAPTER`

### `CONTAINS` 的用法

- 主要用于结构导航
- 可用于课程 / 章节 / 知识点组织
- 不应作为认知层多跳推理的核心关系

---

## 七、Evidence Package 必须包含这些字段

请输出一个统一结构，至少包含：

- `center_node`
- `prerequisites`
- `related_nodes`
- `exercises`
- `document_chunks` ⚠️ 注意：文档内容通过此字段返回，**不是** `documents`
- `code_cases`
- `misconceptions`
- `graph_paths`
- `sources`
- `ranking_reason`
- `student_profile_adaptation`
- `uncertainty`
- `missing_evidence`

### 质量字段（已实现，必须包含）

- `coverage_stats`: 各类型证据的数量统计
  - `exercises_count`, `document_chunks_count`, `code_cases_count`, `misconceptions_count`
  - `prerequisites_count`, `related_nodes_count`, `sources_count`
- `evidence_completeness`: 证据完整性评估
  - `has_document`, `has_code_case`, `has_exercises`, `has_misconceptions`
  - `completeness_score` (0-1), `missing_categories`
- `resource_diversity`: 资源多样性评分 (0-1)
- `relevance_score`: 与查询的相关性评分 (0-1)
- `evidence_score`: 证据包质量评分 (0-1)
- `query_type`: 查询类型 (concept_explanation / exercise_help / path_plan / assessment_review / general)
- `relation_summary`: 关键关系摘要列表
- `recommended_next_actions`: 推荐的下一步学习动作

要求：
- 必须可解释
- 必须能给资源生成服务复用
- 必须能用于后续智能辅导 / 学习路径规划

---

## 八、Neo4j 查询必须覆盖的能力

至少需要这些查询：

1. 根据 `uid` 查知识点
2. 查前置知识
3. 查相关 / 扩展 / 对比知识
4. 查测评题（`ASSESSES`）
5. 查文档块（`SUPPORTS`）
6. 查代码案例（`PRACTICES`）
7. 查来源（`CITES_SOURCE`）
8. 查 1~2 跳 GraphRAG 子图
9. 对结果进行去重、排序和数量限制

必须使用 `uid` 查询，不能假设有数据库内部 `id`。

---

## 九、FastAPI API 设计方向

请优先围绕这些接口设计：

- `GET /api/graph/node/{uid}`
- `GET /api/graph/subgraph/{uid}`
- `GET /api/graphrag/evidence`
- `POST /api/graphrag/query`
- `POST /api/diagnosis/recommend`

要求：
- 每个接口说明输入、输出和用途
- 标明哪些属于 MVP P0
- 输入输出结构必须具体，不要只写概念描述

---

## 十、实现优先级要求

### P0
必须支撑比赛演示闭环：
- GraphStore 可查图
- 能根据 `uid` 或自然语言定位中心知识点
- 能输出 Evidence Package
- 能基于 `weak_points` 做简单个性化排序

### P1
增强效果：
- 诊断推荐
- 更细 query_type
- tutor 入口
- 更细粒度个性化打分

### P2
未来扩展：
- 向量库
- Neo4j 向量索引
- 多跳推理
- 社区摘要
- 自动抽图
- LangGraph 多智能体编排

---

## 十一、当前最重要的数据风险（实现时必须考虑）

1. `DocumentChunk` 太少，不能过度依赖全文语义检索
2. 当前应优先做 **Neo4j-only GraphRAG**
3. Exercise 比文档块更完整，因此练习、误区、前置链应在 MVP 中发挥更大作用
4. 派生关系和原始关系并存，必须用白名单控制可扩展关系
5. 来源链路存在，但证据密度仍需后续补强

---

## 十二、你输出时必须做到的事

请你基于以上约束，输出以下内容：

1. 推荐的后端目录结构
2. 每个核心文件应该负责什么
3. `Neo4jGraphStore` 的方法清单
4. `NodeResolver` 的实现思路
5. `GraphExpansionPolicy` 的规则设计
6. `EvidencePackage` 的 Python 数据结构
7. 每个 API 的输入输出 schema
8. P0 实现顺序和验收标准
9. 当前不该做什么，以及为什么不要做

---

## 十三、输出要求

- 用中文
- 结构清晰
- 不要泛泛而谈
- 必须结合当前项目已有关系类型和数据现状
- 必须明确 MVP 范围
- 不要凭空假设不存在的文件结构
- 如果你需要查看某个现有文件的具体内容，请明确指出要看哪个文件
