# EduGraph-Agent 项目进度台账

最后更新：2026-07-08

## 1. 系统架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EduGraph-Agent 系统架构                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────┐ │
│  │ 登录/注册 │──→│ 学生画像 │──→│ 知识诊断 │──→│ LangGraph 编排    │ │
│  │ (JWT)    │   │ (8维)    │   │ (拓扑排序)│   │ (18节点)         │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────┬───────────┘ │
│                                                       │              │
│  ┌──────────────────────────────────────────────────────┼──────┐     │
│  │                    多智能体协同                       │      │     │
│  │  ┌────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐   │      │     │
│  │  │意图识别│ │GraphRAG   │ │AI备课台│ │练习辅导   │   │      │     │
│  │  │Agent   │ │证据检索   │ │Agent   │ │Agent     │←──┘      │     │
│  │  └────────┘ └──────────┘ └────────┘ └──────────┘          │     │
│  │  ┌────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐          │     │
│  │  │学习路径│ │语义记忆   │ │反馈分析│ │成长时间轴 │          │     │
│  │  │Agent   │ │Agent     │ │Agent   │ │Agent     │          │     │
│  │  └────────┘ └──────────┘ └────────┘ └──────────┘          │     │
│  └───────────────────────────────────────────────────────────┘     │
│                                                                      │
│  数据层：                                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐   │
│  │ Neo4j    │ │ SQLite   │ │ ChromaDB │ │ JWT (python-jose)    │   │
│  │ 370节点  │ │ 画像/对话 │ │ 语义记忆 │ │ bcrypt 密码哈希      │   │
│  │ 1067边   │ │ 反馈/认证 │ │ 向量检索 │ │ 双 token 轮换        │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘   │
│                                                                      │
│  前端：Vue 3 + Pinia + Element Plus + ECharts + Markdown             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. 模块完成度

| 模块 | 状态 | 核心能力 |
|------|------|---------|
| 认证系统 | ✅ DONE | 注册/登录/JWT双token/自动刷新/路由守卫/bcrypt密码哈希 |
| 学生画像 | ✅ DONE | 8维画像 + 对话式构建 + node_mastery + 练习回写 + 行为画像(learning_behavior) |
| LangGraph编排 | ✅ DONE | 18节点StateGraph + SSE流式 + 实时AgentTracePanel可视化 + 打字机效果 |
| GraphRAG | ✅ DONE | 多跳依赖(1-3 hop) + 课程语义入口索引 + 质量评分 + 个性化推理 + 宽泛查询降级匹配 |
| 运行可观测性 | ✅ DONE | `/api/admin/runtime-status` 暴露 Neo4j/SQLite/LLM/Embedding/Chroma 状态、索引数量和 degraded_features |
| 语义记忆 | ✅ DONE | ChromaDB向量存储 + 混合检索(语义+元数据+图谱扩展) + LLM记忆提取 |
| AI 备课台 | ✅ DONE | 5类资源Agent(文档/导图/练习/视频/代码) + 增量生成 + 知识中心持久化 |
| 练习评估 | ✅ DONE | 知识点搜索 + 逐题反馈 + 整轮提交 + 练习记录持久化 + 错题本 + 画像回写 |
| 学习路径 | ✅ DONE | Kahn拓扑排序 + 数据驱动 + mastery接入 + 遗忘节点优先 |
| 反馈闭环 | ✅ DONE | 8种快速标签 + 自由文本 + BehaviorProfileUpdater(增量EMA更新) + LLM批量分析 |
| 成长时间轴 | ✅ DONE | 日历热力图(月/周/日三层下钻) + 学习统计 + 艾宾浩斯遗忘检测 + 决策面板 |
| 知识图谱 | ✅ DONE | 全览力导向图 + 搜索/章节/难度筛选 + 状态图例 + 节点聚焦 + zoom按钮 |
| 前端响应式 | ✅ DONE | 3断点(1400/1024/768px) + 汉堡菜单 + 过渡动画 |
| 知识库 | ✅ DONE | Neo4j 50节点 + 161FAQ + 24代码案例 + 11文档章节 + 1182条课程语义视图 |
| 认证 | ✅ DONE | 注册/登录/JWT + 路由守卫 + token自动刷新 |

## 3. 后端模块清单

```
backend/app/
├── auth/            # 认证 (JWT + bcrypt)
│   ├── models.py    # User, RefreshToken ORM
│   ├── schemas.py   # RegisterRequest, LoginRequest, AuthResponse
│   ├── jwt.py       # 令牌签发/验证/轮换/撤销
│   ├── service.py   # AuthService (register/login/demo_login/refresh)
│   └── routes.py    # POST /auth/register, /auth/login, /auth/demo, /auth/refresh
├── assistant/       # LangGraph 学习主智能体 (18节点)
│   ├── graph.py     # StateGraph 编排 + 路由函数
│   ├── tools.py     # 18个节点实现 + 意图识别 + 证据检索 + AI备课 + 记忆
│   ├── state.py     # AssistantState TypedDict (30+字段)
│   ├── schemas.py   # 请求/响应 Schema
│   ├── service.py   # AssistantService (chat/stream/persist/SSE)
│   ├── memory.py    # AssistantMemoryRepository (对话/运行记录)
│   ├── models.py    # 对话/消息/运行/反馈 ORM
│   ├── feedback.py  # FeedbackRepository (CRUD + create_or_update去重)
│   └── feedback_analyzer.py  # LLM批量反馈分析引擎
├── memory/          # 语义记忆 (ChromaDB)
│   ├── schemas.py   # MemoryEntry (含知识点锚点/困惑信号/掌握信号)
│   ├── embedding.py # EmbeddingService (OpenAI兼容API)
│   ├── vector_store.py  # MemoryVectorStore (混合检索)
│   ├── extractor.py # MemoryExtractor (LLM结构化提取)
│   └── seed.py      # 种子记忆 (仅demo用户)
├── profile/         # 学生画像
│   ├── schemas.py   # StudentProfile (8维 + learning_behavior + 时间轴)
│   ├── models.py    # Student/ProfileRecord/NodeMastery ORM
│   ├── repository.py # ProfileRepository (CRUD + save_learning_behavior)
│   ├── service.py   # ProfileService (init/chat/exercise/progress/dashboard)
│   ├── extractor.py # ProfileExtractor (LLM结构化抽取)
│   ├── behavior_updater.py  # BehaviorProfileUpdater (增量EMA更新)
│   └── timeline.py  # TimelineBuilder + ForgettingDetector
├── graphrag/        # GraphRAG 证据检索
│   ├── schemas.py   # EvidencePackage (含多跳依赖/质量评分)
│   ├── evidence_retriever.py  # 多跳证据收集 + 个性化推理
│   ├── service.py   # GraphRAGService (query + fallback降级)
│   └── ranking.py   # 基于画像排序
├── agents/          # AI 备课台
│   ├── schemas.py   # 5类资源 + 质量报告
│   ├── resource_agents.py  # LangChain资源Agent
│   ├── service.py   # ResourceGenerationService
│   └── repository.py # 资源中心持久化
├── graph/           # 知识图谱
│   ├── models.py    # GraphNode/GraphPath/DependencyPath/MultiHopSummary
│   ├── neo4j_store.py # Neo4jGraphStore (含多跳查询)
│   ├── node_resolver.py # 双层解析(规则+LLM) + 宽泛查询检测
│   ├── expansion_policy.py # 多跳策略 (depth=2, max_hop_depth=3)
│   └── llm_resolver.py # LLM节点解析 (含heuristic fallback)
├── diagnosis/       # 诊断推荐
│   ├── schemas.py
│   └── service.py   # 多源候选 + Kahn拓扑排序 + 优先级评分
├── api/             # API路由
│   ├── deps.py      # 依赖注入 (含get_current_user)
│   ├── router.py    # 路由注册
│   └── routes/      # 8个路由文件，含 admin runtime-status
└── core/            # 配置
    └── config.py    # Settings (含LLM/Embedding/Neo4j/ChromaDB配置)
```

## 4. 前端模块清单

```
frontend/src/
├── views/           # 15个页面
│   ├── LoginView.vue          # 登录 (邮箱+密码 / 演示入口)
│   ├── RegisterView.vue       # 注册 (用户名+邮箱+密码+确认)
│   ├── AssistantView.vue      # 学习助手 (流式+反馈标签+AgentTracePanel+MemoryPanel)
│   ├── ProfileChatView.vue    # 画像对话
│   ├── ProfilePanelView.vue   # 画像面板 (8维卡片+行为画像+更新时间线)
│   ├── KnowledgeGraphView.vue # 知识图谱 (全览力导向图)
│   ├── LearningPathView.vue   # 学习路径 (拓扑排序+数据驱动)
│   ├── ResourceGenerationView.vue  # AI 备课台 (5类+增量+降级提示)
│   ├── ExerciseView.vue       # 练习测试 (搜索+逐题反馈+整轮提交)
│   ├── AssessmentView.vue     # 效果评估 (雷达图+柱状图+饼图)
│   ├── KnowledgeCenterView.vue # 知识中心 (搜索+排序)
│   ├── LearningGrowthView.vue  # 学习成长 (日历热力图+事件列表+遗忘预警)
│   ├── AdminView.vue           # 系统管理 (健康检查+反馈仪表盘)
│   ├── TutorChatView.vue       # 辅导对话
│   └── ProfilePanelView.vue    # (已合并)
├── stores/          # Pinia状态管理
│   ├── auth.ts      # 登录态 (token/localStorage持久化/自动刷新)
│   ├── assistant.ts # 助手 (18节点/流式/实时trace/反馈状态)
│   ├── profile.ts   # 画像 (initFromAuth/loadCurrentStudent)
│   └── learning.ts  # 学习 (AI 备课台)
├── components/      # 17个组件
│   ├── assistant/   # AgentTracePanel, MemoryPanel
│   ├── profile/     # ProfileCard, CompletenessBar, UpdateTimeline, LearningTimeline
│   ├── graphrag/    # EvidencePanel (含多跳依赖可视化)
│   ├── resources/   # DocumentCard, MindmapCard, ExerciseCard, CodeCaseCard, VideoScriptCard, AgentProgressPanel
│   ├── graph/       # FullGraphCanvas, GraphCanvas
│   └── common/      # ErrorAlert, LoadingSkeleton, ChatBubble
├── api/             # API层 (axios + token拦截器 + 自动刷新)
│   ├── client.ts    # 请求/响应拦截器 (Bearer token + 401自动refresh)
│   ├── assistant.ts # 对话/流式/历史/反馈
│   ├── profile.ts   # 画像/时间轴
│   └── ...
└── router/
    └── index.ts     # 路由守卫 (未登录→/login, 刷新自动恢复)
```

## 5. 核心闭环

### 5.1 学习闭环

```
注册/登录 → 画像建立(8维) → LangGraph对话
  → GraphRAG多跳证据检索 → 5类AI备课 → 练习评估
  → 诊断推荐(Kahn拓扑排序) → 学习路径 → 画像更新
```

### 5.2 反馈闭环

```
学生回复下方点反馈标签 → POST /feedback
  → 校验消息归属 → create_or_update去重
  → BehaviorProfileUpdater.update() (增量EMA更新格式有效性/深度偏好/理解缺口)
  → save_learning_behavior() → commit
  → 下次对话 load_context → behavior.is_reliable()
  → 注入 understand_intent/general_tutor/compose_response prompt
```

### 5.3 记忆闭环

```
对话完成 → extract_memory节点 → LLM提取MemoryEntry
  → EmbeddingService.embed() → ChromaDB insert
  → 下次对话 retrieve_memory节点 → 混合检索(语义+知识点+图谱扩展)
  → 相关记忆注入 understand_intent/general_tutor prompt
```

## 6. 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 后端框架 | FastAPI | ≥0.111 |
| Agent编排 | LangGraph | ≥0.2 |
| LLM集成 | LangChain + langchain-openai | ≥0.2 / ≥0.1.8 |
| 图数据库 | Neo4j | ≥5.20 |
| 向量数据库 | ChromaDB | ≥0.5 |
| 关系数据库 | SQLite (aiosqlite) | ≥0.20 |
| 前端框架 | Vue 3 + Vite | latest |
| 状态管理 | Pinia | latest |
| UI组件 | Element Plus | latest |
| 图表 | ECharts | latest |
| 认证 | python-jose + bcrypt | ≥3.3 / ≥4.0 |
| Markdown | markdown-it + KaTeX | latest |

## 7. 关键数据

| 指标 | 数值 |
|------|------|
| LangGraph节点 | 18 (load_context → retrieve_memory → understand_intent → update_profile → record_progress → retrieve_evidence → evaluate_evidence → expand_evidence → generate_resources → reflect_on_resources → explain_exercise → plan_learning_path → review_assessment → general_tutor → compose_response → extract_memory → error_recovery) |
| Neo4j节点 | 370 (50 KnowledgePoint + 308 Entity + 11 Chapter + 1 Course) |
| Neo4j关系 | 1067 |
| FAQ条目 | 161 (24个知识主题) |
| 代码案例 | 24 |
| 前端页面 | 15 |
| 前端组件 | 17 |
| API端点 | 45 |
| 学生画像维度 | 8 + learning_behavior + timeline |
| 资源生成类型 | 5 (document/mindmap/exercise/video_script/code_case) |
| 反馈标签 | 8 (有帮助/很清楚/没看懂/太难/太简单/想要例子/想要总结/不够具体) |

## 7.1 运行状态观测

新增后端运行状态接口：

```text
GET /api/admin/runtime-status
```

该接口用于区分系统当前是否真的启用了核心能力，还是处于降级状态。返回内容包括：

- Neo4j 连接状态与数据库名
- SQLite 连接状态、业务表数量和表名
- LLM provider/model/base_url/API key 配置状态
- Embedding model/dimension/base_url/API key 配置状态
- Chroma `learning_memories` 与 `course_semantic_views` collection 是否存在、数量和维度匹配情况
- `degraded_features` 与 `warnings`

同时已将默认 `CHROMA_PERSIST_DIR` 固定到项目根目录 `data/chroma`，避免后端从 `backend/` 启动、索引脚本从项目根目录启动时看到不同的 Chroma 路径。

## 7.2 HybridRAG 课程语义索引与 LangGraph 子图进展

更新时间：2026-07-07

- Chroma `course_semantic_views` 已完成真实入库，当前记录数为 1182，维度为 2560，对应 `Qwen/Qwen3-Embedding-4B`。
- 语义索引定位为“语义入口层”，不是 Neo4j 的事实副本；每条 semantic view 通过 `target_uid` / `target_type` 指回 Neo4j canonical evidence。
- 新增调试接口 `GET /api/graphrag/semantic-search`，可查看自然语言问题命中的 semantic views、候选图谱节点、语义分数、图谱加权、画像加权和排序原因。
- `EvidenceRetriever` 已接入 semantic hit 回灌：`DocumentChunk`、`Exercise`、`CodeCase`、`Misconception` 命中后会按 `target_uid` 回 Neo4j 重新读取 canonical node，再合并进 `EvidencePackage`。
- `KnowledgePoint` 类型 semantic hit 只作为语义线索保留在 `semantic_hits`，不伪造图谱关系，不直接塞入 `related_nodes`。
- 回灌节点会带临时 `_semantic_match` 追踪信息，用于前端/调试面板解释“为什么这条证据被语义检索补充进来”。
- 前端 `EvidencePanel` 已展示 semantic hits、HybridRAG 融合摘要和 `_semantic_match` 标记，可区分图谱直接证据与语义检索补充证据。
- 新增 `backend/app/graphrag/langgraph/` HybridRAG 检索子图，节点包括 `prepare_query`、`resolve_learning_target`、`retrieve_graph_context`、`retrieve_semantic_context`、`retrieve_memory_context`、`fuse_canonical_evidence`、`grade_evidence`、`repair_evidence`、`finalize_evidence`。
- GraphRAG 服务已切换为通过 HybridRAG 子图输出 `EvidencePackage`，并保持 `/api/graphrag/evidence`、`/api/graphrag/query`、资源生成和 assistant 主链路的兼容。
- `grade_evidence` 已输出 `hybrid_rag_quality`，包含 coverage、relevance、grounding、personal_fit、overall、missing_categories、weak_reasons、repair_actions、enough。
- `repair_evidence` 不再只是记录日志，会真实执行 profile-guided search、global semantic search、related/prerequisite expansion，并把补充 semantic hits 回查 Neo4j canonical evidence 后合并。
- 自然语言解析失败时，系统会按学生画像薄弱点或最低 mastery 节点做 fallback 中心节点，同时在 `uncertainty` 中保留“不确定/降级匹配”提示，避免无中心证据包。
- Assistant 主 LangGraph 的 `retrieve_evidence` / `evaluate_evidence` / `expand_evidence` 已接入 HybridRAG 子图结果，主 trace 会展开 `hybrid_rag:*` 子节点。
- Memory RAG 已注入 GraphRAGService，`student_id` 可从 `/api/graphrag/query` 传入，命中摘要写入 `student_profile_adaptation.memory_hits`，便于解释个性化历史如何参与检索。
- 服务级 smoke test 已通过：查询“loss 震荡/学习率太大”在 resolver 未精确命中时 fallback 到 `ml_gradient_descent`，返回 docs=6、code=2、exercises=11、FAQ=25、sources=12，`hybrid_rag_quality.overall_score=0.876`。
- 本轮受执行环境外网审批限制，未能重新访问外部 embedding API；因此 smoke test 中 `semantic_hits=0` 只能说明当前环境未完成外网语义检索复测，不代表本地 Chroma 索引为空。

## 7.3 助手流式输出稳定性修复

更新时间：2026-07-07

- 修复 `/api/assistant/stream` 在 LangGraph trace 项为 Pydantic `AssistantTraceItem` 时调用 `.get()` 导致 SSE 中途断流的问题。
- 修复 LangGraph 内部事件 output 为字符串时，流式服务错误调用 `.get()` 的问题。
- 流式接口现在只向前端暴露业务节点，过滤 `RunnableSequence` 等内部节点，避免右侧执行面板出现非学习流程节点。
- 流式接口增加异常兜底：若后续节点仍发生异常，会发送 SSE `error` 事件并尽量返回降级 `final_response`，避免前端只显示笼统 `network error`。
- 前端 `streamAssistant` 已补充登录 token 请求头，并能识别 SSE `error` 事件。
- 直连验证通过：`AssistantService.stream()` 能完整输出 `final_response`，前端 `npm.cmd run build` 通过。

## 7.4 助手练习生成意图修复

更新时间：2026-07-07

- 修复“帮我生成十道 Kmeans 的选择题”被当成普通 GraphRAG 检索/问答的问题。
- Assistant 意图识别后增加规则兜底：当用户话语中包含明确的题目/练习生成请求时，会自动切换到 `resource_generate`，补齐 `exercise` 资源类型。
- 支持从自然语言中解析练习数量与题型，例如“十道 Kmeans 的选择题”“10 道 K-means 单选题”“五个 Kmeans 题”。
- `ResourceGenerateRequest` 增加 `exercise_count` 与 `exercise_type`，并贯穿 Assistant → ResourceGenerationService → ExerciseAgent。
- ExerciseAgent 不再硬编码 2-3 道题，能够按请求生成 1-20 道题；当 LLM 返回数量不足时，后端会用证据约束的 fallback 题目补齐。
- 增加练习后处理校验：当请求选择题时，最终结果必须全部为 `choice`，且每题必须具备 A/B/C/D 四个选项与合法答案；LLM 返回缺项或混入其他题型时会被 fallback 替换。
- Assistant 最终回复会直接渲染生成的题目、选项、答案和解析，避免只返回“已检索/已准备资源”的空泛说明。
- 助手页新增“本轮备课内容”可见入口；AI 备课后会显示资源类型与数量，并可一键打开知识中心对应记录。
- 知识中心从助手记录跳转进入时，会根据资源内容自动打开最相关的 tab；只有练习题的记录会直接进入“练习题”页签，避免用户看到空的导图/文档页误以为没有生成。
- 修复资源反思和记忆提取中对旧数据结构的依赖，避免 `AttributeError` 出现在 LangGraph 执行面板中。

## 7.5 助手练习题渲染修复

更新时间：2026-07-08

- 修复助手生成练习题后，题目未正确显示在对话回复中的问题。
- 原因：`general_tutor` 节点先设置了 `final_reply`（知识点讲解），导致 `compose_response` 中 `_resource_reply` 因 `final_reply` 已有值而跳过。
- 修复方案：调整 `compose_response` 中的逻辑，当存在资源时，先追加资源信息再判断是否使用 fallback。
- 修改位置：[tools.py:984-993](backend/app/assistant/tools.py#L984-L993)

## 7.6 学习路径页面重构（新手友好）

更新时间：2026-07-08

### 问题分析
原版学习路径页面存在以下问题：
1. **新用户困惑**：未设置学习目标时页面无引导，用户不知道要做什么
2. **术语晦涩**："前置链""拓扑排序""核心概念"等术语对新手不友好
3. **信息混乱**：5种路径模式（当前目标/查漏补缺/考前复习/项目实战/自由探索）对新用户无意义
4. **缺乏引导**：没有解释"学习路径是什么、为什么需要"

### 重构方案
采用"三段式"简化布局，对新用户更友好：

1. **新用户引导卡片**：未设置目标时显示引导提示和快速体验按钮
2. **目标摘要栏**：显示学习目标 + 进度统计（已完成/进行中/待学习）
3. **三栏式布局**：
   - 当前章节（正在学习的内容）
   - 薄弱点（需要加强的知识点）
   - 推荐下一步（建议学习的内容）
4. **完整路径展开**：可展开查看全部节点的时间线视图
5. **简化推荐理由**：用自然语言解释为什么推荐这些内容

### 技术改进
- 移除 5 种路径模式（对新手无意义）
- 节点状态标签简化：已掌握/进行中/需加强/待学习
- 推荐理由面向用户友好表达
- 增加引导提示（问号图标悬停说明）

## 8. 当前待做

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | 运行状态可观测性 `/api/admin/runtime-status` | DONE |
| P0 | 真实LLM API Key 端到端联调验证 | TODO |
| P0 | Neo4j 启动 + 完整浏览器联调 | TODO |
| P0 | 外网 embedding API 环境复测 semantic hits 回灌 | TODO |
| P1 | 学生画像维度增强 (认知风格/能力状态) | TODO |
| P1 | E2E 自动化测试 (Playwright) | TODO |
| P2 | 演示材料 (PPT/视频/架构图/手册) | TODO |
| P2 | Docker 容器化部署 | TODO |
