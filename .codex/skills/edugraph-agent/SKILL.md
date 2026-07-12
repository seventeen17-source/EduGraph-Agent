---
name: edugraph-agent
description: Project-specific workflow for EduGraph-Agent, a China Software Cup A3 personalized learning multi-agent platform based on knowledge graphs, GraphRAG, student profiles, and multi-agent learning-resource generation. Use when working in this repo on requirements, architecture, Vue/FastAPI/LangChain/LangGraph implementation, GraphRAG, student profiles, knowledge graphs, resource generation, demo flow, frontend UX, testing, PPT/video/submission materials, or scope tradeoffs.
---

# EduGraph-Agent

## Purpose

Use this skill to keep work aligned with the competition goal: a demonstrable personalized learning loop, not isolated chat or content-generation features.

Core loop:

```text
student profile -> knowledge diagnosis -> GraphRAG retrieval -> multi-agent resource generation -> learning-path planning -> learning evaluation -> profile update
```

## Read First

Start with the latest local docs, especially:

- `docs/project/PROJECT_PROGRESS.md`
- `启动服务.md`
- `backend/README.md`
- `docs/knowledge-base/学生画像模块设计方案.md`
- `docs/project/A3_initial_development_doc.md`
- `docs/project/A3_development_schedule.md`
- `docs/project/PROMPT_给其他AI_实现前端MVP.md` when changing the frontend MVP

If Chinese text appears mojibake in PowerShell, read with explicit UTF-8:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[System.IO.File]::ReadAllText("docs/project/PROJECT_PROGRESS.md", [System.Text.Encoding]::UTF8)
```

## Current System Snapshot

As of 2026-06-26 this is no longer a blank skeleton.

- Frontend: `frontend/` is a Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus + ECharts app. Root redirects to `/assistant`. Main navigation is: 学习助手 → 我的画像 → 学习路径 → 知识图谱 → 资源中心 → 练习与评估 → 系统设置. New `AssistantView.vue` is the primary entry point with a three-column workspace (context / chat / action panel).
- Backend: `backend/` is a FastAPI app with GraphRAG, graph, diagnosis, profile, resource-agent, and **assistant** routes.
- Graph store: Neo4j is the active graph backend for the demo path. Do not revert core graph behavior to JSON/NetworkX-only fallbacks.
- Profile store: student profiles, mastery, update events, and chat history are persisted in relational SQLite at project root `data/edugraph.db`.
- Profile module: `backend/app/profile/` supports initialization, follow-up chat, exercise-result updates, learning-progress updates, knowledge-point mastery, dashboard DTO, update timeline, and persistent chat history.
- Profile extraction: LangChain structured output is used when configured, then deterministic rules supplement/fallback. LLM output is not trusted directly; normalize enum aliases before Pydantic validation or database writes.
- Frontend profile chat must restore history from `GET /api/profile/{student_id}/chat-history`; do not keep important chat state only in component-local memory.
- Knowledge graph UI supports fuzzy search suggestions and clicking any node to reload the subgraph centered on that node.
- Resource generation uses `POST /api/agents/generate-resources`, driven by GraphRAG evidence packages and visible `agent_trace`.
- Main demo nodes include `ml_kmeans`, `ml_gradient_descent`, `ml_backpropagation`, and `ml_logistic_regression`.

Important API surfaces:

- `GET /health`
- `GET /api/graph/node/{uid}`
- `GET /api/graph/subgraph/{uid}`
- `GET /api/graphrag/evidence`
- `POST /api/graphrag/query`
- `POST /api/diagnosis/recommend`
- `POST /api/agents/generate-resources`
- `POST /api/assistant/chat`
- `POST /api/assistant/stream`
- `GET /api/assistant/{student_id}/history`
- `POST /api/profile/init`
- `POST /api/profile/chat`
- `GET /api/profile/{student_id}/dashboard`
- `GET /api/profile/{student_id}/chat-history`
- `POST /api/profile/events/exercise-result`
- `POST /api/profile/events/learning-progress`

## Startup

Backend:

```powershell
cd D:\Code\EduGraph-Agent\backend
uvicorn app.main:app --reload
```

With `--reload`, normal Python edits usually hot-reload. Restart manually after dependency, environment, database-path, or startup-parameter changes, or when reload misses a change.

Frontend:

```powershell
cd D:\Code\EduGraph-Agent\frontend
npm.cmd run dev
```

Typical URLs:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

## Work Rules

- Default to implementing concrete fixes, not only proposing designs, unless the user explicitly asks for analysis only.
- Preserve the closed learning loop. A change that improves only chat polish but does not feed profile, graph retrieval, resources, path planning, evaluation, or profile updates is secondary.
- Classify scope:
  - `P0`: required for the demo loop or correctness.
  - `P1`: strong differentiator after the loop works.
  - `P2`: nice-to-have after the demo path is stable.
- The user prefers database-backed, end-to-end logic over temporary placeholders. Do not suggest in-memory/local-only substitutes for core profile persistence, graph behavior, or chat history unless explicitly requested.
- Keep outputs inspectable: visible profile deltas, graph evidence, agent traces, source IDs, quality reports, and update events.
- After completing a project task, update `docs/project/PROJECT_PROGRESS.md`. Update `docs/README.md` when adding major docs/data. If a long-lived behavior rule changes, keep `.codex/skills/edugraph-agent/SKILL.md` and `.claude/skills/edugraph-agent/SKILL.md` synchronized.

## Profile Rules

Student profile is a first-class frontend feature and backend data product.

Core dimensions:

- `background`
- `learning_goal`
- `knowledge_base`
- `progress`
- `cognitive_style`
- `weak_points`
- `preferences`
- `ability_state`
- `node_mastery`

Important constraints:

- Knowledge mastery must be knowledge-point-level, not only coarse global stages.
- Initialization and update are related but separate flows: initialization builds the first multi-dimensional profile; updates merge new/corrected information from later dialogue, exercises, progress, and graph interactions.
- The profile agent should reply like a helpful learning assistant: confirm what changed, mention uncertainty when relevant, and ask the next useful question. Avoid one-line robotic acknowledgements.
- Profile update logic must preserve user corrections, such as grade changes, and avoid letting old background text pollute learning goals.
- Internal resource types are exactly `document`, `diagram`, `exercise`, `video_script`, `code_case`. Normalize synonyms such as `practice`, `quiz`, `做题`, `刷题`, `coding`, and `code` before validation.
- Knowledge/ability levels are `weak`, `basic`, `intermediate`, `advanced`. Normalize LLM labels such as `beginner`, `medium`, and `strong`.

## Frontend Rules

- The app is for a Chinese demo. User-facing UI text should be Chinese. Do not expose raw English enums, relationship names, agent names, missing-evidence keys, or IDs unless they are intentionally technical.
- Prefer real workflow screens over landing-page or decorative UI. The first screen of a tool should be usable.
- Profile, graph, resources, learning path, exercises, and evaluation should feel connected. Show why a recommendation happened.
- For graph UX, support search suggestions while typing, fuzzy matches, and node-centered expansion on click, similar to the Neo4j Browser feel.
- Preserve chat history across route changes and refreshes by using backend history APIs.
- When changing frontend behavior, run `npm.cmd run build` when feasible and verify the local app in the browser for significant UI changes.

## GraphRAG And Resources

Treat GraphRAG as graph-guided retrieval for personalized learning:

1. Resolve the query to a knowledge node.
2. Expand prerequisites, related nodes, resources, exercises, and graph paths.
3. Retrieve supporting document chunks and assessments.
4. Rank using student weak points, mastery, learning goal, preferences, and difficulty.
5. Return evidence, uncertainty, missing evidence, and ranking reasons.

Resource generation should remain evidence-grounded. The five resource types are:

- explanation document
- mind map / diagram
- exercises
- video script
- code case

Generation responses should keep `resources`, `quality_report`, and `agent_trace` visible for frontend display and debugging. Current implementation is service/module based; migrating to LangGraph state graph with SSE progress is a high-value next step but should not break the current API contract.

## Knowledge Base Rules

The first course is Machine Learning. Current structured data includes:

- `data/course/course_meta.json` — 课程元信息
- `data/course/chapters.json` — 11 章结构（ch01-ch06 P0, ch07-ch11 P2 骨架）
- `data/course/knowledge_points.json` — 50 个知识点
- `data/course/graph_edges.json` — 约 500+ 条边（结构边、认知边、资源边）
- `data/docs/` — 11 章讲义 Markdown，ch01-ch06 已有 41 个 DocumentChunk
- `data/exercises/` — 按章节拆分的题库，共 54 道题（ch01 8题, ch02 8题, ch03 12题, ch04 8题, ch05 6题, ch06 12题）
- `data/sources/sources.json` — 16 个来源（10 本本地 PDF + 6 个在线资源）
- `data/faq/misconceptions.json` — 161 条 FAQ，覆盖 24 个知识主题常见误区
- `data/code_cases/` — 24 个代码案例，覆盖核心算法、深度学习、工程实践，每个案例已建立 PRACTICES 边

P0 chapters are ch01-ch06; ch07-ch11 are extension skeletons. Use official/public courses and self-authored summaries. Do not copy long textbook passages into the repo.

When editing exercises:

- Keep split chapter files under `data/exercises/`.
- Use `assess_<exercise_id>_<knowledge_node_id>` for assessment edge IDs.
- Include `assesses`, `also_assesses`, `prerequisite_node_ids`, `profile_update_policy`, `misconception_tags`, `grading`, and `adaptive_feedback` where relevant.

## Verification

Use focused checks appropriate to the change:

```powershell
python -c "import ast, pathlib; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in ['backend/app/profile/service.py']]; print('ast ok')"
npm.cmd run build
```

For backend behavior, prefer direct service/API smoke tests that cover the reported path. For profile extraction fixes, simulate bad LLM enum output and verify it normalizes before Pydantic validation. For frontend changes, use the browser to verify the actual page when the target URL is known.

## Current Priorities

Highest-value next work (as of 2026-07-07):

1. **真实LLM API Key 端到端联调验证**：验证完整对话流程（认证 → 画像 → 对话 → GraphRAG → 资源生成）
2. **Neo4j 完整联调**：确保后端与 Neo4j 连接正常，370节点/1067边可正常检索
3. **外网 embedding API 环境复测**：semantic hits 回灌功能需要真实环境验证
4. **E2E 自动化测试 (Playwright)**：建立端到端测试覆盖
5. **演示材料制作**：PPT / 演示视频 / 测试说明文档

## Demo And Submission

Optimize around a 7-minute scenario:

```text
Computer science student learning machine learning, has Python/calculus background, is weak in gradient descent or backpropagation, prefers diagrams/code or exercises, asks a natural-language question, receives graph-grounded resources, completes an exercise, and sees the profile update.
```

The demo should visibly show profile extraction, profile dashboard, graph expansion, GraphRAG citations, multi-agent resources, learning-path recommendation, exercise/evaluation result, and profile/path update.
