---
name: "edugraph"
description: "EduGraph-Agent 个性化学习平台开发技能。基于 FastAPI + LangChain/LangGraph + Neo4j + ChromaDB + Vue 3 构建。当需要修改此项目代码、添加新功能、修复 bug、或理解项目架构时调用此技能。"
---

# EduGraph-Agent 开发技能

## 项目定位

基于知识图谱 + LLM 的个性化学习平台，提供学习助手、资源生成、练习评估、学生画像、学习成长追踪等能力。

---

## 技术栈

### 后端
| 技术 | 用途 |
|------|------|
| FastAPI + Uvicorn | Web 框架 |
| SQLAlchemy + aiosqlite | 关系数据库 ORM（SQLite） |
| Neo4j 5.x | 知识图谱存储 |
| ChromaDB | 向量数据库（语义记忆 + 课程语义视图） |
| LangChain + LangGraph | LLM Agent 编排 |
| python-jose + bcrypt | JWT 认证 |
| SSE (sse-starlette) | 流式响应 |

### 前端
| 技术 | 用途 |
|------|------|
| Vue 3 + TypeScript | 核心框架 |
| Vite 6 | 构建工具 |
| Pinia | 状态管理 |
| Vue Router 4 | 路由 |
| Element Plus 2.x | UI 组件库 |
| Axios | HTTP 客户端 |
| ECharts 5 | 图表（雷达图、热力图等） |
| markmap-lib | 思维导图渲染 |
| Mermaid | 流程图渲染 |
| KaTeX | 数学公式渲染 |
| highlight.js | 代码语法高亮 |
| markdown-it | Markdown 解析 |

---

## 项目目录结构

```
EduGraph-Agent/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口，lifespan，路由注册
│   │   ├── agents/                  # AI 资源生成（5 个 Agent）
│   │   │   ├── models.py            # GeneratedResourceRecord ORM
│   │   │   ├── resource_agents.py   # LangChainResourceAgents（Document/Mindmap/Exercise/VideoScript/Code）
│   │   │   ├── service.py           # ResourceGenerationService
│   │   │   ├── repository.py        # ResourceRepository
│   │   │   └── schemas.py           # 资源生成请求/响应 Schema
│   │   ├── api/
│   │   │   ├── deps.py              # 依赖注入（从 ServiceCache 获取服务）
│   │   │   ├── router.py            # 路由聚合器（9 个路由模块）
│   │   │   └── routes/
│   │   │       ├── admin.py         # 运行时状态
│   │   │       ├── agents.py        # 资源生成端点
│   │   │       ├── assistant.py     # 学习助手（对话 + 流式 + 反馈）
│   │   │       ├── diagnosis.py     # 诊断推荐
│   │   │       ├── exercises.py     # 练习记录（含搜索端点）
│   │   │       ├── graph.py         # 知识图谱查询
│   │   │       ├── graphrag.py      # GraphRAG 证据检索
│   │   │       └── profile.py       # 学生画像
│   │   ├── assistant/               # 学习助手核心
│   │   │   ├── graph.py             # LangGraph 对话图
│   │   │   ├── state.py             # 对话状态定义
│   │   │   ├── tools.py             # 工具调用（资源生成/练习/记忆等）
│   │   │   ├── service.py           # AssistantService（含流式 SSE）
│   │   │   ├── models.py            # 会话/消息/反馈 ORM
│   │   │   └── schemas.py           # 助手请求/响应 Schema
│   │   ├── auth/                    # 认证（JWT + bcrypt）
│   │   ├── core/                    # 基础设施
│   │   │   ├── config.py            # Settings（含环境变量）
│   │   │   ├── logging.py           # JSON 结构化日志
│   │   │   ├── service_cache.py     # 服务单例缓存
│   │   │   ├── manual_json.py       # LLM JSON 手动解析
│   │   │   └── errors.py            # HTTP 异常类
│   │   ├── db/
│   │   │   ├── neo4j.py             # Neo4j 异步客户端
│   │   │   └── relational.py        # SQLAlchemy async 引擎
│   │   ├── diagnosis/               # 诊断推荐（拓扑排序 + 优先级）
│   │   ├── exercises/               # 练习记录
│   │   │   ├── models.py            # Session/Attempt/Review/Bookmark ORM
│   │   │   ├── schemas.py           # 含 ExerciseSearchRequest/Response
│   │   │   ├── service.py           # ExerciseRecordService（含评分引擎）
│   │   │   └── repository.py        # ExerciseRepository
│   │   ├── graph/                   # 知识图谱
│   │   │   ├── neo4j_store.py       # Neo4jGraphStore
│   │   │   ├── node_resolver.py     # NodeResolver
│   │   │   └── models.py            # GraphNode/GraphPath/SubgraphResult
│   │   ├── graphrag/                # GraphRAG 证据检索
│   │   │   ├── service.py           # GraphRAGService
│   │   │   ├── evidence_retriever.py
│   │   │   ├── langgraph/           # Hybrid RAG LangGraph 工作流
│   │   │   └── schemas.py           # EvidencePackage 等
│   │   ├── memory/                  # 语义记忆
│   │   │   ├── vector_store.py      # MemoryVectorStore (ChromaDB)
│   │   │   ├── embedding.py         # EmbeddingService
│   │   │   └── extractor.py         # 记忆提取器
│   │   ├── profile/                 # 学生画像
│   │   │   ├── models.py            # Student/ProfileRecord/NodeMastery 等 6 个 ORM
│   │   │   ├── schemas.py           # 含 LearningBehaviorProfile
│   │   │   ├── service.py           # ProfileService
│   │   │   ├── extractor.py         # ProfileExtractor（LLM 抽取）
│   │   │   ├── behavior_updater.py  # 行为画像增量更新
│   │   │   ├── timeline.py          # 成长时间轴 + 遗忘检测
│   │   │   └── completeness.py      # 画像完整度计算
│   │   └── rag/                     # 课程语义检索
│   ├── data/                        # SQLite/ChromaDB 数据文件
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.ts                  # 入口（Element Plus + Pinia + Router）
│   │   ├── App.vue                  # 根组件（侧边栏 + 头部 + 路由视图）
│   │   ├── router/index.ts          # 16 条路由 + 登录守卫
│   │   ├── api/                     # 9 个 API 文件（client.ts 含自动 token 刷新）
│   │   ├── stores/                  # 4 个 Pinia store
│   │   │   ├── auth.ts              # useAuthStore（登录/注册/刷新）
│   │   │   ├── profile.ts           # useProfileStore（画像 CRUD）
│   │   │   ├── assistant.ts         # useAssistantStore（对话流式 SSE）
│   │   │   └── learning.ts          # useLearningStore（图谱/证据/资源）
│   │   ├── views/                   # 15 个页面
│   │   ├── components/              # 6 个子目录，17 个组件
│   │   ├── types/                   # 7 个类型定义文件
│   │   ├── utils/format.ts          # 27 个工具函数（标签/日期/格式化）
│   │   └── styles/global.css        # 656 行全局样式（CSS 变量 + 响应式）
│   ├── package.json
│   └── vite.config.ts
└── .trae/
    ├── specs/refactor-exercise-assessment/  # 当前活跃 spec
    └── skills/edugraph/SKILL.md             # 本文件
```

---

## 路由总览

### 后端 API 路由（共 38 个端点）

| 前缀 | 端点数量 | 功能 |
|------|---------|------|
| `/auth` | 4 | 注册、登录、演示登录、Token 刷新 |
| `/graph` | 5 | 知识点查询、搜索、子图、标签映射 |
| `/graphrag` | 3 | 证据检索、查询、语义搜索 |
| `/diagnosis` | 1 | 诊断推荐 |
| `/agents` | 4 | 资源生成、资源中心 CRUD |
| `/profile` | 11 | 画像初始化、对话、事件、仪表盘、时间轴 |
| `/assistant` | 6 | 对话、流式、历史、反馈 |
| `/exercises` | 8 | 练习提交、搜索、记录、错题、统计 |
| `/admin` | 1 | 运行时状态 |

### 前端路由（共 16 条）

| 路径 | 组件 | 说明 |
|------|------|------|
| `/` | 重定向 | → `/assistant` |
| `/login` | LoginView | 登录（公开） |
| `/register` | RegisterView | 注册（公开） |
| `/assistant` | AssistantView | 学习助手 |
| `/profile/chat` | ProfileChatView | 对话画像 |
| `/profile/panel` | ProfilePanelView | 我的画像 |
| `/graph` | KnowledgeGraphView | 知识图谱 |
| `/learning-path` | LearningPathView | 学习路径 |
| `/resources` | ResourceGenerationView | AI 备课台 |
| `/knowledge-center` | KnowledgeCenterView | 知识中心 |
| `/exercise` | ExerciseView | 练习与评估 |
| `/exercise-history` | ExerciseHistoryView | 练习记录 |
| `/assessment` | AssessmentView | 效果评估 |
| `/learning-growth` | LearningGrowthView | 学习成长 |
| `/admin` | AdminView | 系统设置 |

---

## 核心数据流

### 学习闭环
```
用户提问 → 学习助手(AssistantService) → GraphRAG(HybridRAG) → 返回证据
    ↓
资源生成(ResourceGenerationService) → 5 个 Agent 并行生成 → 保存到 GeneratedResourceRecord
    ↓
练习与评估(ExerciseView) → 搜索(/exercises/search) → 作答 → 提交(/exercises/sessions)
    ↓
画像更新(ProfileService) → NodeMastery 增量更新 → 评价反馈
    ↓
学习成长(LearningGrowthView) → 时间轴 + 遗忘预警
```

### 画像维度（10 维度）
- `background` / `learning_goal` / `knowledge_base` / `progress`
- `cognitive_style` / `weak_points` / `preferences`
- `ability_state` / `node_mastery` / `learning_behavior`

### 练习评分引擎
| 题型 | 评分方式 | grading_method |
|------|---------|---------------|
| choice | 规则匹配 | `rule` |
| short_answer | LLM + rubric | `llm_rubric` |
| coding | LLM 结构化评分 | `code_execution` |
| case_analysis | LLM rubric | `llm_rubric` |

---

## 关键约定

### 后端
- **配置管理**：所有配置通过 `Settings` 类（`app/core/config.py`）和环境变量管理，使用 `get_settings()` 获取
- **服务单例**：Neo4jGraphStore、GraphRAGService、DiagnosisService、ProfileExtractor 通过 `ServiceCache`（`app/core/service_cache.py`）管理
- **日志**：使用 `logging.getLogger(__name__)`，不要用 `print()`
- **异常处理**：所有 `except Exception:` 必须记录日志（`logger.debug/warning`），不要静默吞没
- **JWT 密钥**：生产环境必须通过 `JWT_SECRET` 环境变量配置，不允许使用默认密钥
- **数据库**：ORM 模型使用 SQLAlchemy 2.0 Mapped 风格，关系数据库使用 aiosqlite（异步 SQLite）
- **路由**：新路由在 `app/api/routes/` 下创建，然后在 `app/api/router.py` 注册

### 前端
- **状态管理**：根据功能域使用对应的 Pinia store：
  - 认证相关 → `useAuthStore`
  - 画像相关 → `useProfileStore`
  - 助手对话 → `useAssistantStore`
  - 图谱/证据/资源 → `useLearningStore`
- **API 调用**：统一使用 `frontend/src/api/` 下的封装函数，使用 `client.ts` 中的 Axios 实例（自动 token 注入 + 401 刷新）
- **类型定义**：所有数据类型在 `frontend/src/types/` 下定义，与后端 Schema 保持一致
- **组件结构**：`components/` 按功能域分组：`assistant/`、`common/`、`graph/`、`graphrag/`、`profile/`、`resources/`
- **工具函数**：标签/日期/格式化函数统一放在 `utils/format.ts`
- **样式**：使用全局 CSS 变量（`global.css`），组件内使用 `<style scoped>`
- **路由守卫**：`PUBLIC_PAGES = ['/login', '/register']` 之外的页面需要登录，401 自动刷新 token

---

## 当前活跃 Spec

### `refactor-exercise-assessment`（练习与评估系统重构）

**状态**：spec 已定义但未开始执行

**P0 任务（6 项）**：
1. 统一练习来源池（题库 + AI生成 + 错题 + 推荐）
2. AI备课台移除默认 query 和全选资源类型
3. 助手生成题后显示"立即开始作答"按钮
4. 区分练习模式（自由练习/正式测验/错题复习/诊断评估）
5. 后端按题型评分（choice/short_answer/coding/case_analysis）
6. 清理新用户 demo 数据

**P1 任务（5 项）**：全局搜索、知识中心全文搜索、练习记录画像变化、学习路径推荐队列、开发者/学生信息分层

---

## 开发工作流

### 启动后端
```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 启动前端
```powershell
cd frontend
npm install
npm run dev
```

### 类型检查
```powershell
cd frontend
npx vue-tsc --noEmit
```

### 关键环境变量
| 变量 | 说明 |
|------|------|
| `NEO4J_URI` | Neo4j 连接地址（默认 bolt://localhost:7687） |
| `NEO4J_PASSWORD` | Neo4j 密码 |
| `LLM_API_KEY` | LLM API 密钥 |
| `LLM_MODEL` | LLM 模型（默认 gpt-4o-mini） |
| `LLM_BASE_URL` | LLM API 地址 |
| `JWT_SECRET` | JWT 签名密钥（生产环境必填） |
| `DATABASE_URL` | 关系数据库地址（默认 SQLite） |
| `CHROMA_PERSIST_DIR` | ChromaDB 持久化目录（默认 data/chroma） |
| `ENVIRONMENT` | 运行环境（local/dev/prod） |

---

## 文件修改注意事项

1. **修改前端 Vue 文件前**：先读取完整文件确认当前内容，注意 `watch` 需要从 `vue` 导入
2. **修改后端路由前**：确认 `deps.py` 中已有对应的依赖注入函数
3. **修改 ORM 模型前**：确认 `alembic` 迁移或 SQLite 的自动建表逻辑
4. **修改 schemas 前**：同步更新前端 `types/` 下的对应类型定义
5. **修改评分逻辑**：在 `app/exercises/service.py` 的 `_grade_attempt` 方法中按题型分发
6. **新增 API 端点**：在 `app/api/routes/` 下添加，在 `app/api/router.py` 注册，在前端 `api/` 下封装调用函数