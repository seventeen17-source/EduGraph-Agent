# EduGraph-Agent Backend

FastAPI backend for EduGraph-Agent — a personalized learning multi-agent platform.

## 快速启动

```bash
cd backend
pip install -r requirements.txt

# 配置 .env
cat > .env << 'EOF'
LLM_API_KEY=你的key
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=你的base_url       # 使用 DeepSeek 等代理时必填
EMBEDDING_API_KEY=你的key        # 可与 LLM_API_KEY 相同
EMBEDDING_MODEL=text-embedding-3-small
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=edugraph123
DATABASE_URL=sqlite+aiosqlite:///./data/edugraph.db
EOF

uvicorn app.main:app --reload --port 8000
```

Neo4j 必须在 `bolt://localhost:7687` 运行，且已导入知识图谱数据。

## 数据存储

| 存储 | 用途 |
|------|------|
| **Neo4j** | 知识图谱：KnowledgePoint / Exercise / DocumentChunk / CodeCase / Misconception / Source + 关系边 |
| **SQLite** | 业务数据：users / students / profiles / conversations / messages / feedback / resource_records / node_mastery |
| **ChromaDB** | 语义记忆：learning_memories collection（向量嵌入 + 元数据） |

## 核心模块

| 模块 | 路径 | 功能 |
|------|------|------|
| 认证 | `app/auth/` | 注册/登录/JWT双token/自动刷新/bcrypt密码哈希 |
| 学习助手 | `app/assistant/` | LangGraph 18节点编排 / SSE流式 / 对话持久化 / 反馈闭环 |
| 语义记忆 | `app/memory/` | ChromaDB向量存储 / 混合检索 / LLM记忆提取 |
| 学生画像 | `app/profile/` | 8维画像 + node_mastery + 行为画像(learning_behavior) + 成长时间轴 |
| GraphRAG | `app/graphrag/` | 多跳证据检索(1-3 hop) / 质量评分 / 降级匹配 / 备选建议 |
| 资源生成 | `app/agents/` | 5类资源Agent / 增量生成 / 知识中心持久化 |
| 知识图谱 | `app/graph/` | Neo4j查询 / 多跳依赖树 / 节点解析(双层) / 宽泛查询检测 |
| 诊断推荐 | `app/diagnosis/` | 多源候选 + Kahn拓扑排序 + 优先级评分 |

## 全部 API 端点

### 认证 (/api/auth)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 (email + username + password) |
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/demo` | 演示账号一键登录 |
| POST | `/api/auth/refresh` | 刷新 access_token |

### 学习助手 (/api/assistant)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/assistant/chat` | 对话（非流式） |
| POST | `/api/assistant/stream` | 对话（SSE流式，含节点进度+质量评分） |
| GET | `/api/assistant/{student_id}/history` | 对话历史 |
| POST | `/api/assistant/feedback` | 提交反馈（8种快速标签） |
| GET | `/api/assistant/feedback/stats/{student_id}` | 反馈统计 |
| POST | `/api/assistant/feedback/analyze/{student_id}` | 触发LLM反馈分析 |

### 学生画像 (/api/profile)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/profile/init` | 初始化画像 |
| POST | `/api/profile/chat` | 画像对话补充 |
| GET | `/api/profile/{student_id}` | 获取画像 |
| GET | `/api/profile/{student_id}/dashboard` | 画像仪表盘 |
| GET | `/api/profile/{student_id}/history` | 画像更新时间线 |
| GET | `/api/profile/{student_id}/chat-history` | 画像对话历史 |
| GET | `/api/profile/{student_id}/timeline` | 成长时间轴 |
| PATCH | `/api/profile/{student_id}` | 手动编辑画像 |
| POST | `/api/profile/events/exercise-result` | 练习结果回写 |
| POST | `/api/profile/events/exercise-round` | 整轮练习提交 |
| POST | `/api/profile/events/learning-progress` | 学习进度更新 |

### 知识图谱 (/api/graph, /api/graphrag)
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/graph/node/{uid}` | 节点详情 |
| GET | `/api/graph/subgraph/{uid}` | 子图（含前置/关联/资源） |
| GET | `/api/graph/all` | 全量节点 |
| GET | `/api/graphrag/evidence?uid=xxx` | 按UID检索证据包 |
| POST | `/api/graphrag/query` | 自然语言查询证据包 |
| GET | `/api/graphrag/semantic-search` | 语义搜索调试接口（查看semantic hits、排序原因） |

### 资源生成 (/api/agents)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agents/generate-resources` | 生成5类学习资源 |
| GET | `/api/agents/resource-center` | 知识中心列表 |
| GET | `/api/agents/resource-center/{id}` | 资源详情 |
| PATCH | `/api/agents/resource-center/{id}/mindmap` | 编辑思维导图 |

### 诊断 (/api/diagnosis)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/diagnosis/recommend` | 学习路径推荐 |

### 练习 (/api/exercises)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/exercises/sessions` | 创建练习会话 |
| POST | `/api/exercises/sessions/{session_id}/submit` | 提交答案 |
| GET | `/api/exercises/sessions/{student_id}` | 获取练习历史 |
| GET | `/api/exercises/sessions/{student_id}/{session_id}` | 获取会话详情 |

### 管理 (/api/admin)
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/runtime-status` | 运行状态（Neo4j/SQLite/LLM/Embedding/Chroma） |

## LangGraph 智能体编排

18 个图节点，按以下流程执行：

```
load_context → retrieve_memory → understand_intent
  → update_profile / record_progress / retrieve_evidence / compose_response
    → evaluate_evidence → expand_evidence
    → generate_resources → reflect_on_resources
    → explain_exercise / plan_learning_path / review_assessment / general_tutor
    → compose_response → extract_memory → END
```

SSE 流式事件：`run_started` → `node_started` → `trace_item` → `node_completed` → `quality_update` → `final_response` → `persisted`

## 反馈闭环

```
学生点反馈标签 → POST /feedback
  → 校验消息归属 (message.student_id == payload.student_id, role == "assistant")
  → create_or_update (同student_id+message_id去重, 首次创建/后续更新)
  → BehaviorProfileUpdater.update() (增量EMA更新)
  → save_learning_behavior() → commit
  → 下次对话 load_context → behavior注入prompt
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| LLM_API_KEY | - | LLM API密钥（必填） |
| LLM_MODEL | gpt-4o-mini | 模型名 |
| LLM_BASE_URL | - | API基础URL（使用代理时必填） |
| LLM_PROVIDER | openai | openai / deepseek |
| EMBEDDING_API_KEY | - | Embedding API密钥（默认复用LLM_API_KEY） |
| EMBEDDING_MODEL | text-embedding-3-small | Embedding模型 |
| NEO4J_URI | bolt://localhost:7687 | Neo4j地址 |
| NEO4J_USERNAME | neo4j | Neo4j用户名 |
| NEO4J_PASSWORD | edugraph123 | Neo4j密码 |
| DATABASE_URL | sqlite+aiosqlite:///... | SQLite地址 |
