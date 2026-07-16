# EduGraph-Agent — 基于知识图谱与多智能体协同的个性化学习平台

> 融合 **知识图谱（Neo4j）+ GraphRAG + LangGraph 多智能体编排 + 多模态资源生成** 的机器学习课程个性化学习系统。

---

## 1. 项目简介

EduGraph-Agent 面向《机器学习》课程学习场景，解决传统在线学习"千人一面、缺乏诊断、资源单一"的痛点：

- **个性化**：8 维学生画像 + 行为画像 + 语义记忆，让智能体"认识"每一位学生；
- **可解释**：GraphRAG 多跳证据检索，每一条回答都能追溯到知识图谱中的依赖路径；
- **多模态**：一键生成讲解文档、思维导图、练习题、视频脚本、代码案例、教学图片 6 类学习资源；
- **闭环化**：对话 → 诊断 → 练习 → 反馈 → 画像回写 → 路径推荐，完整学习闭环。

## 2. 核心功能

| 功能 | 说明 |
|------|------|
| 学习助手 | LangGraph **17 节点** StateGraph 编排，SSE 流式输出，AgentTracePanel 实时展示每个智能体节点的执行过程 |
| GraphRAG 证据检索 | HybridRAG（图检索 + 课程语义向量检索），1–3 跳依赖分析、质量评分、宽泛查询降级匹配 |
| 学生画像 | 8 维画像、对话式构建、node_mastery 掌握度、行为画像（EMA 增量更新）、证据链可追溯 |
| AI 资源生成 | 6 类资源智能体并发生成（文档/导图/练习/视频脚本/代码/图片），LLM 自修复，知识中心持久化 |
| 练习评估 | 4 种练习模式，后端评分（选择/简答/代码/案例），错题本，成绩回写画像 |
| 学习路径 | Kahn 拓扑排序 + 5 种推荐类型 + 逐节点推荐理由，目标驱动 |
| 反馈闭环 | 8 种快速反馈标签 → BehaviorProfileUpdater → 下次对话自动适应 |
| 学习成长 | 日历热力图、遗忘检测预警、周报、事件时间轴 |
| 知识图谱可视化 | 370 节点 / 1067 关系交互式图谱，学习进度着色、子图展开、前置路径高亮 |

## 3. 前沿 AI 技术融合

| 技术 | 应用点 |
|------|--------|
| **LangGraph 多智能体编排** | 17 节点 StateGraph：意图识别 → 证据检索 → 质量评估 → 证据扩展 → 资源生成 → 自反思 → 回复合成 → 记忆提取 → 错误恢复 |
| **GraphRAG / HybridRAG** | Neo4j 子图检索 × ChromaDB 课程语义视图（1182 条，2560 维）混合排序，多跳依赖推理 |
| **语义记忆** | 对话后 LLM 自动提取记忆条目 → ChromaDB 向量化存储 → 下次对话混合检索注入 |
| **Agentic 自反思** | 资源生成后 reflect 节点自检质量，证据不足时自动 expand_evidence 二次检索 |
| **多模态生成** | 科大讯飞 HiDream 文生图 + Markmap 思维导图 + Mermaid 流程图 + 视频脚本生成 |
| **教育数据挖掘** | Kahn 拓扑排序诊断、艾宾浩斯遗忘检测、EMA 行为建模 |

## 4. 技术栈

- **后端**：FastAPI · LangGraph ≥0.2 · LangChain · Neo4j 5.x · ChromaDB · SQLite(aiosqlite) · python-jose/bcrypt(JWT)
- **前端**：Vue 3 + TypeScript · Vite 6 · Pinia · Element Plus · ECharts · markmap/Mermaid/KaTeX
- **LLM**：OpenAI / DeepSeek 兼容端点（可配置），Embedding 使用 Qwen3-Embedding-4B
- **图片生成**：科大讯飞 HiDream

## 5. 目录结构

```
EduGraph-Agent/
├── backend/            # FastAPI 后端（app/ 下按领域分模块）
│   ├── app/
│   │   ├── assistant/  # 学习助手（LangGraph 17节点编排）
│   │   ├── graphrag/   # GraphRAG 证据检索
│   │   ├── agents/     # 6类资源生成智能体
│   │   ├── profile/    # 学生画像
│   │   ├── exercises/  # 练习评估
│   │   ├── diagnosis/  # 诊断推荐（拓扑排序）
│   │   ├── memory/     # 语义记忆（ChromaDB）
│   │   ├── graph/      # Neo4j 图谱访问
│   │   ├── auth/       # JWT 认证
│   │   └── image_generation/  # 讯飞文生图
│   └── tests/          # 端到端冒烟测试
├── frontend/           # Vue 3 前端（14 个页面视图 / 16 条路由）
├── data/               # 数据集：课程结构/讲义/练习题/FAQ/图谱边
├── Scripts/            # Neo4j 数据导入脚本
├── docs/               # 设计文档与知识库文档
└── 提交材料/            # 本文件夹：配套文档与部署配置
```

## 6. 快速启动

```bash
# 1. 启动 Neo4j（本地安装或 Docker，见 部署配置/部署说明.md）
# 2. 导入图谱数据
python Scripts/import_to_neo4j.py --uri bolt://localhost:7687 --user neo4j --password edugraph123 --drop-existing

# 3. 配置环境变量（复制模板并填入你的 API Key）
cp 提交材料/部署配置/.env.example backend/.env

# 4. 启动后端
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 5. 启动前端
cd frontend && npm install && npm run dev
# 打开 http://127.0.0.1:5173
```

演示账号：`demo@edugraph.local` / `demo123`（登录页可一键体验）。

详细步骤见《用户使用手册》与《部署配置/部署说明.md》。

## 7. 配套文档索引

评分要点与文档的对应关系：**创新价值** → 开发说明书 §10 创新实践、需求分析 §3.4 技术-需求结合点；**功能与技术** → 开发说明书 §3 核心技术实现（含 Mermaid 架构/流程图）；**用户体验** → 开发说明书 §2.3 界面设计、§11 体验策略。

| 文档 | 位置 |
|------|------|
| 需求分析说明书 | `提交材料/需求分析说明书.md` |
| 系统开发说明书 | `提交材料/系统开发说明书.md` |
| 测试说明书 | `提交材料/测试说明书.md` |
| 用户使用手册 | `提交材料/用户使用手册.md` |
| AI Coding 工具使用说明 | `提交材料/AI_Coding工具使用说明.md` |
| 开源协议与第三方组件说明 | `提交材料/开源协议与第三方组件说明.md`、`提交材料/LICENSE` |
| 部署配置 | `提交材料/部署配置/`（.env.example / docker-compose.yml / Dockerfile） |
| 技术路线与实现全景 | `docs/project/技术路线与实现全景.md` |
| 架构总览 | `docs/project/PROJECT_PROGRESS.md` |
| 后端 API 全览 | `backend/README.md` |

## 8. 关键数据

| 指标 | 数值 |
|------|------|
| LangGraph 编排节点 | 17 |
| Neo4j 知识图谱 | 370 节点 / 1067 关系（50 知识点 + 308 实体 + 11 章节 + 1 课程） |
| 课程语义视图 | 1182 条（ChromaDB，2560 维向量） |
| 练习题库 | 54 题（覆盖 ch01–ch06 核心章节，ch07–ch11 预留扩展）+ FAQ 161 条 + 代码案例 24 个 |
| API 端点 | 52（51 个业务端点 + /health） |
| 前端页面 | 14（16 条路由） |
| 资源生成类型 | 6（文档/导图/练习/视频脚本/代码/图片） |
