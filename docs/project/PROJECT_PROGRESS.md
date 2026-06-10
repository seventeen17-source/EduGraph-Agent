# EduGraph-Agent 项目进度台账

最后更新：2026-06-07

本文档用于记录 EduGraph-Agent 项目的已完成事项、待做事项和下一步优先级。后续每完成一个任务，都需要同步更新本文档。

状态说明：

| 状态 | 含义 |
| --- | --- |
| `DONE` | 已完成并通过基础校验 |
| `DOING` | 正在推进 |
| `TODO` | 尚未开始 |
| `BLOCKED` | 暂时受阻，需要决策或外部条件 |
| `LATER` | 后续增强，不影响当前 MVP |

## 1. 总体进度

| 模块 | 状态 | 当前结果 | 下一步 |
| --- | --- | --- | --- |
| 项目需求与赛题理解 | DONE | 已形成 A3 初步开发文档和开发时间表 | 后续按功能变化持续修订 |
| 项目专属 Skill | DONE | Codex 与 Claude 均有 `edugraph-agent` skill | 每次新增关键规则时同步两边 |
| 文档目录整理 | DONE | 项目文档已迁入 `docs/project`，知识库文档已迁入 `docs/knowledge-base` | 维护 `docs/README.md` 索引 |
| 参考教材整理 | DONE | 10 本参考教材 PDF 已放在 `参考教材/`，并在 `data/sources/sources.json` 中登记本地路径 | 不直接放入知识库正文，只作为参考来源 |
| 知识库章节结构 | DONE | `chapters.json` 已完成 11 章结构 | 后续只做小范围修订 |
| 知识点结构 | DONE | `knowledge_points.json` 已完成 50 个知识点 | 后续补增强字段或修正关系 |
| 图谱边结构 | DONE | `graph_edges.json` 已有 133 条边，其中包含 ch01、ch02、ch03、ch04、ch05 与 ch06 题目 `ASSESSES` 边 | 下一步开发 GraphRAG 数据加载服务 |
| Neo4j 导入脚本 | DONE | `Scripts/import_to_neo4j.py` 已实现对 course / chapter / knowledge point / source / exercise / document / chunk / FAQ / code case / graph edges 的导入 | 在本地 Neo4j 环境执行 dry run 和正式导入 |
| GraphRAG 对外实现提示词 | DONE | 已形成可直接发给其他 AI 的实现提示词文档 | 供并行协作或外部 AI 辅助开发 |
| 章节讲义框架 | DOING | `data/docs/` 已有 11 个章节 Markdown；ch01-ch06 已补入可解析 DocumentChunk | 下一步开始补 P0 CodeCase/FAQ，或继续补 P2 章节 |
| 练习题结构 | DONE | 题库已按章节拆分并采用增强版 schema，ch01 到 ch06 的 P0 章节已补到目标数量并挂载图谱 | 下一步开发 GraphRAG 服务 |
| 代码案例 | DOING | 当前有 `gradient_descent_demo.py` | 统一代码案例 ID 规则并补更多案例 |
| FAQ/误区 | DOING | 当前有基础误区样例 | 按 P0 主线补 FAQ |
| GraphRAG 实现 | DOING | 已创建 FastAPI + Neo4j-only GraphRAG MVP 后端骨架，完成 `ml_kmeans` / `ml_gradient_descent` / `ml_backpropagation` 三节点证据包审查 | 继续补 Evidence Package 质量字段与 P0 讲义 chunk |
| 前端/后端项目骨架 | DOING | 已创建 `backend/` FastAPI 骨架；前端尚未创建 | 后续搭建前端 Vue 骨架并接 GraphRAG API |
| Agent 编排 | TODO | 尚未创建 LangGraph 流程 | 先做 Profile/Retrieval/Resource 的最小图 |
| 提交材料 | TODO | 还未开始 PPT、视频、测试说明 | 等 MVP 闭环跑通后制作 |

## 2. 已完成事项

### 2.1 项目需求与规划

- DONE：明确项目名称 `EduGraph-Agent`。
- DONE：明确赛题方向为中国软件杯 A3：基于大模型的个性化资源生成与学习多智能体系统。
- DONE：明确核心闭环：

```text
学生画像 -> 知识诊断 -> GraphRAG 检索 -> 多智能体资源生成 -> 学习路径规划 -> 学习效果评估 -> 画像更新
```

- DONE：形成 [A3_initial_development_doc.md](A3_initial_development_doc.md)。
- DONE：形成 [A3_development_schedule.md](A3_development_schedule.md)。
- DONE：形成 [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md)，用于持续记录已做事项、待做事项、优先级和后续更新规则。
- DONE：明确技术栈：Vue 3 + FastAPI + LangChain + LangGraph。
- DONE：明确知识库首选课程为机器学习。

### 2.2 项目 Skill 与上下文沉淀

- DONE：创建 `.codex/skills/edugraph-agent`。
- DONE：创建 `.claude/skills/edugraph-agent`。
- DONE：同步项目目标、技术栈、知识库来源、章节 schema、题库 schema。
- DONE：两份 skill 均通过 `quick_validate.py` 校验。
- DONE：两份 skill 已加入 `PROJECT_PROGRESS.md` 读取与任务完成后更新规则。
- TODO：后续关键规则变化时，继续同步两份 skill。

### 2.3 知识库来源与教材

- DONE：收集 10 本参考教材 PDF，存放在 `参考教材/`。
- DONE：清理文件名中的 z-library / z-lib / 1lib 相关字样。
- DONE：在 [ML_知识库收集指南.md](../knowledge-base/ML_知识库收集指南.md) 中记录十本本地参考教材、公开课资料和官方文档。
- DONE：在 `data/sources/sources.json` 中建立来源基线，当前包含 16 个来源，并为 10 本本地 PDF 登记 `local_file`。
- TODO：后续补讲义时，为每个文档块绑定 `source_ids`。

### 2.4 知识库数据框架

- DONE：建立 `data/course/course_meta.json`。
- DONE：建立 `data/course/chapters.json`，包含 11 章结构。
- DONE：建立 `data/course/knowledge_points.json`，包含 50 个知识点。
- DONE：建立 `data/course/graph_edges.json`，包含 133 条结构/认知/资源边。
- DONE：建立 `data/docs/` 下 11 个章节讲义框架。
- DONE：补充 `data/docs/ch02_math_optimization.md` 的 5 个 DocumentChunk，覆盖线性代数、概率统计、微积分与优化、损失函数、梯度与最优化。
- DONE：补充 `data/docs/ch03_linear_models_optimization.md` 的 5 个 DocumentChunk，覆盖线性回归、逻辑回归、线性判别分析、梯度下降、SGD 与 Mini-batch。
- DONE：补充 `data/docs/ch04_supervised_algorithms.md` 的 5 个 DocumentChunk，覆盖决策树、支持向量机、贝叶斯分类器、集成学习和随机森林。
- DONE：补充 `data/docs/ch05_unsupervised_representation.md` 的 6 个 DocumentChunk，覆盖聚类、K-Means、降维、度量学习、特征选择和稀疏学习。
- DONE：补充 `data/docs/ch06_neural_deep_learning.md` 的 11 个 DocumentChunk，覆盖感知机、多层神经网络、激活函数、反向传播、Dropout、BatchNorm、CNN、RNN、LSTM、注意力机制和 Transformer。
- DONE：建立 `data/sources/sources.json`。
- DONE：建立 `data/faq/misconceptions.json`。
- DONE：建立 `data/code_cases/gradient_descent_demo.py`。
- DONE：JSON 基础解析校验通过。

### 2.5 章节结构

- DONE：将章节结构定为 11 章：

| 章节 | 标题 | 优先级 |
| --- | --- | --- |
| ch01 | 机器学习导论与模型评估 | P0 |
| ch02 | 数学基础与优化基础 | P0 |
| ch03 | 线性模型与梯度优化 | P0 |
| ch04 | 经典监督学习算法 | P0 |
| ch05 | 无监督学习与特征表示 | P0 |
| ch06 | 神经网络与深度学习基础 | P0 |
| ch07 | 计算学习理论 | P2 |
| ch08 | 半监督学习 | P2 |
| ch09 | 概率图模型 | P2 |
| ch10 | 规则学习 | P2 |
| ch11 | 强化学习 | P2 |

- DONE：章节数据包含 `recommended_resource_types`、`assessment_focus`、`demo_usage` 等字段。
- TODO：随着知识点补充，继续完善各章 `key_node_ids`。

### 2.6 知识点结构

- DONE：`knowledge_points.json` 已完成 50 个知识点。
- DONE：所有知识点章节引用合法。
- DONE：所有 `prerequisites` / `related` 引用合法。
- TODO：为 P0 主线知识点补齐增强字段：
  - `aliases`
  - `node_type`
  - `role_in_path`
  - `common_queries`
  - `common_misconceptions`
  - `mastery_objectives`
  - `doc_chunk_ids`
  - `exercise_ids`
  - `code_case_ids`

### 2.7 图谱边结构

- DONE：形成 [graph_edges_设计方案.md](../knowledge-base/graph_edges_设计方案.md)。
- DONE：`graph_edges.json` 首版完成 77 条结构/认知边。
- DONE：`graph_edges.json` 已补 ch01、ch02、ch03、ch04、ch05 与 ch06 题目 `ASSESSES` 资源边，当前共 133 条边。
- DONE：已覆盖结构层和认知层：
  - `CONTAINS`
  - `PREREQUISITE`
  - `RELATED`
  - `EXTENDS`
  - `CONTRASTS`
- DONE：已补资源层 `ASSESSES` 边：ch01、ch02、ch03、ch04、ch05 与 ch06 题目已挂载到对应知识点。
- TODO：继续补资源层边：
  - `SUPPORTS`
  - `PRACTICES`
  - `ILLUSTRATES`

### 2.8 练习题题库

- DONE：决定采用方案 C 增强版 Exercise Schema。
- DONE：决定按章节拆分题库。
- DONE：删除旧的单文件 `data/exercises/exercises.json`。
- DONE：建立 `data/exercises/exercises_index.json`。
- DONE：建立 11 个章节题库文件。
- DONE：`ch03_linear_models_optimization.json` 已补到 12 题。
- DONE：`ch01_intro_evaluation.json` 已补到 8 题。
- DONE：`ch02_math_optimization.json` 已补到 8 题。
- DONE：`ch04_supervised_algorithms.json` 已补到 8 题。
- DONE：`ch05_unsupervised_representation.json` 已补到 6 题。
- DONE：`ch06_neural_deep_learning.json` 已补到 12 题。
- DONE：题型覆盖：
  - `choice`
  - `short_answer`
  - `coding`
  - `case_analysis`
- DONE：题库索引一致性校验通过。
- DONE：为 ch03 题目补 `ASSESSES` 边。
- DONE：为 ch06 题目补 `ASSESSES` 边。
- DONE：为 ch01 题目补 `ASSESSES` 边。
- DONE：为 ch02 题目补 `ASSESSES` 边。
- DONE：为 ch04 题目补 `ASSESSES` 边。
- DONE：为 ch05 题目补 `ASSESSES` 边。
- TODO：后续按需补 P2 扩展章节题目。

### 2.9 FastAPI 后端与 GraphRAG MVP

- DONE：创建 `backend/` 后端目录结构。
- DONE：创建 FastAPI 应用入口 `backend/app/main.py`。
- DONE：创建 Neo4j 连接层 `backend/app/db/neo4j.py`。
- DONE：创建 `Neo4jGraphStore`，支持按 `uid` 查询节点、前置知识、相关节点、题目、文档块、代码案例、来源和子图。
- DONE：创建 `NodeResolver`，MVP 阶段支持 uid 和关键词规则解析中心知识点。
- DONE：创建 `GraphExpansionPolicy`，区分 GraphRAG 可扩展关系与 `HAS_*` 工程导航关系。
- DONE：创建 `EvidencePackage`、`EvidenceRetriever` 和 `GraphRAGService`。
- DONE：创建 P0 API：
  - `GET /health`
  - `GET /api/graph/node/{uid}`
  - `GET /api/graph/subgraph/{uid}`
  - `GET /api/graphrag/evidence`
  - `POST /api/graphrag/query`
- DONE：创建 P1 诊断推荐接口骨架 `POST /api/diagnosis/recommend`。
- DONE：`python -m compileall backend/app` 通过。
- DONE：当前环境中 FastAPI / Neo4j driver / pydantic-settings 依赖导入通过。
- DONE：启动 uvicorn 后，基础接口和 GraphRAG 接口可访问。
- DONE：修复 Neo4j 查询结果转换问题，避免 `/api/graph/node/{uid}` 返回 500。
- DONE：完成 `ml_kmeans`、`ml_gradient_descent`、`ml_backpropagation` 三个核心 demo 节点 Evidence Package 审查。
- DONE：核对 `PREREQUISITE` 方向，确认 `ml_gradient_descent` 与 `ml_backpropagation` 显式前置边方向正确。
- DONE：为 `Neo4jGraphStore.get_prerequisites()` 和 `get_related_nodes()` 增加节点属性兜底路径，支持 `ml_kmeans` 这类尚未显式建边但属性中已有 `prerequisites` / `related` 的知识点。
- DONE：将 `NodeResolver` 改为“规则召回 + LLM 风格理解/重排”的双层解析器。
- DONE：新增 `QueryUnderstanding` 输出结构，包含 `normalized_query`、`intent`、`possible_nodes`、`reranked_nodes`、`confidence`、`reason`。
- DONE：新增本地启发式 LLM fallback，在未配置真实 LLM 时支持 query rewrite、query classification 和 candidate rerank。
- DONE：新增 `LangChainLLMResolverClient`，支持通过 LangChain structured output 调用真实 LLM 完成 query rewrite、query classification 和 candidate rerank。
- DONE：新增 LLM Resolver 配置项：`LLM_RESOLVER_ENABLED`、`LLM_PROVIDER`、`LLM_MODEL`、`LLM_API_KEY`、`LLM_BASE_URL`。
- DONE：在 `backend/README.md` 中补充 LangChain resolver 启用方式。
- DONE：验证三类自然语言问题可解析：
  - “我总是搞不清 K-Means 为什么要反复更新中心点” -> `ml_kmeans`
  - “神经网络训练时那个从后往前算梯度的过程是什么” -> `ml_backpropagation`
  - “为什么逻辑回归名字里有回归但实际在做分类” -> `ml_logistic_regression`
- TODO：补 Evidence Package 质量字段：
  - `evidence_score`
  - `relation_summary`
  - `recommended_next_actions`
  - `query_type`

## 3. 当前待做清单

### 3.1 高优先级 P0

| 状态 | 任务 | 目标文件/产出 | 验收标准 |
| --- | --- | --- | --- |
| DONE | 为 ch03 题目生成 `ASSESSES` 边 | `data/course/graph_edges.json` | 12 道题均挂载到对应知识点 |
| DONE | 统一练习题资源边命名规则 | `graph_edges_设计方案.md` / `graph_edges.json` | 使用 `assess_<exercise_id>_<knowledge_node_id>` 短 ID |
| DONE | 补 ch06 题库到 12 题 | `data/exercises/ch06_neural_deep_learning.json` | 覆盖反向传播、CNN、注意力机制、Transformer |
| DONE | 为 ch06 题目生成 `ASSESSES` 边 | `data/course/graph_edges.json` | 12 道题均挂载到对应知识点 |
| DONE | 补 ch01 题库到 8 题 | `data/exercises/ch01_intro_evaluation.json` | 覆盖过拟合、正则化、评估方法、性能度量 |
| DONE | 为 ch01 题目生成 `ASSESSES` 边 | `data/course/graph_edges.json` | 8 道题均挂载到对应知识点 |
| DONE | 补 ch02 题库到 8 题 | `data/exercises/ch02_math_optimization.json` | 覆盖损失函数、梯度、优化基础 |
| DONE | 为 ch02 题目生成 `ASSESSES` 边 | `data/course/graph_edges.json` | 8 道题均挂载到对应知识点 |
| DONE | 补 ch04 题库并生成 `ASSESSES` 边 | `data/exercises/ch04_supervised_algorithms.json` / `data/course/graph_edges.json` | 覆盖决策树、SVM、贝叶斯分类器、集成学习 |
| DONE | 补 ch05 题库并生成 `ASSESSES` 边 | `data/exercises/ch05_unsupervised_representation.json` / `data/course/graph_edges.json` | 覆盖聚类、K-Means、降维、特征选择 |
| TODO | 补 P0 讲义正文 | `data/docs/ch01~ch06*.md` | 每个核心知识点至少 1 个可检索文档块 |
| TODO | 建立讲义 chunk ID 规则 | `data/chunks/` 或文档内块 ID | 每个 chunk 有 `chunk_id`、`knowledge_node_id`、`source_ids` |
| TODO | 统一代码案例 ID 规则 | `data/code_cases/` | 代码案例可生成 `PRACTICES` 边 |

### 3.2 中优先级 P1

| 状态 | 任务 | 目标文件/产出 | 验收标准 |
| --- | --- | --- | --- |
| DONE | 设计 GraphRAG 数据加载服务 | `backend/app/graphrag/` | 已形成 Neo4j-only MVP 服务骨架 |
| DONE | 设计 GraphStore 抽象 | `backend/app/graph/neo4j_store.py` | 已支持 Neo4j 查询，统一使用 `uid` |
| TODO | 设计文档切片服务 | 后端模块设计 | 能生成 chunk metadata |
| TODO | 设计 VectorStore 抽象 | 后端模块设计 | 支持 FAISS/Chroma 扩展 |
| DONE | 设计 Evidence Package | `backend/app/graphrag/schemas.py` | 能返回图谱路径、文档块、题目、代码案例、来源 |

### 3.3 后续增强 P2

| 状态 | 任务 | 目标文件/产出 | 说明 |
| --- | --- | --- | --- |
| DONE | Neo4j 图数据库接入 | `Neo4jGraphStore` | 已作为 GraphRAG MVP 主图谱存储 |
| LATER | 自动抽图 | `data/extraction/` | 当前以人工整理为主 |
| LATER | 多跳推理策略 | GraphExpansionPolicy | 当前先做浅层扩展 |
| LATER | 社区摘要 | `data/summaries/` | 当前先不做 |
| LATER | 自动 PPT | 提交材料增强 | MVP 完成后再做 |
| LATER | 真实视频生成 | 提交材料增强 | 当前只生成视频脚本 |

## 4. 当前推荐下一步

当前最推荐执行：

1. 补 Evidence Package 质量字段，提升前端展示和 Agent 复用能力。
2. 给 `ml_kmeans`、`ml_gradient_descent`、`ml_backpropagation` 补最少量 P0 讲义 chunk。
3. 编写 GraphRAG API 冒烟测试脚本，固定三节点验收结果。

理由：

- ch01 到 ch06 的 P0 题库与 `ASSESSES` 资源边都已打通，诊断数据已经具备较完整覆盖面。
- 继续补 P2 章节收益较低，当前应优先把 Neo4j-only GraphRAG MVP 跑通。
- 后端骨架已经可启动、可查询，下一步要把证据包从“能返回”提升到“质量稳定、适合资源生成 Agent 使用”。

## 5. 更新规则

后续每完成一个任务，必须更新：

1. 本文档对应模块的状态。
2. `最后更新` 日期。
3. 如新增文档或数据文件，同时更新 [docs/README.md](../README.md)。
4. 如新增会影响 Codex/Claude 行为的长期规则，同时更新：
   - `.codex/skills/edugraph-agent/SKILL.md`
   - `.claude/skills/edugraph-agent/SKILL.md`
