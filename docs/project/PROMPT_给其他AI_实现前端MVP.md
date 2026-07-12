# EduGraph-Agent 前端 MVP 实现提示词

## 角色

你是一个资深 Vue 3 + TypeScript 全栈前端工程师，正在为 EduGraph-Agent（一个基于知识图谱 + GraphRAG 的个性化学习系统）构建 MVP 演示前端。

你的任务不是做一个完整的产品，而是做一个**可用于 7 分钟比赛演示视频**的最小可行前端。

---

## 一、技术栈（必须使用）

- Vue 3（Composition API + `<script setup lang="ts">`）
- TypeScript
- Vite
- Pinia（状态管理）
- Vue Router 4（路由）
- Element Plus（UI 组件库）
- ECharts（图表，用于知识图谱和雷达图）
- Mermaid（思维导图渲染，前端直接渲染）
- markdown-it + highlight.js（Markdown 渲染 + 代码高亮）
- Axios（HTTP 请求）

不要引入其他未列出的重型依赖。不要用 Tailwind CSS（保持 Element Plus 组件风格统一）。

---

## 二、项目结构

在项目根目录下创建 `frontend/`，标准 Vite + Vue 3 项目结构：

```text
frontend/
  index.html
  vite.config.ts
  tsconfig.json
  package.json
  src/
    main.ts
    App.vue
    router/
      index.ts
    stores/
      profile.ts          # 学生画像状态
      learning.ts         # 学习会话状态
    api/
      client.ts           # Axios 实例 + baseURL 配置
      profile.ts          # 画像 API
      graph.ts            # 图谱 API
      graphrag.ts         # GraphRAG API
      diagnosis.ts        # 诊断 API
      agents.ts           # 资源生成 API
    views/
      LoginView.vue
      ProfileChatView.vue        # 对话式画像构建页
      ProfilePanelView.vue       # 学生画像面板
      KnowledgeGraphView.vue     # 课程知识图谱页
      LearningPathView.vue       # 个性化学习路径页
      ResourceGenerationView.vue # 多智能体资源生成页
      TutorChatView.vue          # 智能辅导页
      ExerciseView.vue           # 练习测试页
      AssessmentView.vue         # 学习效果评估页
      AdminView.vue              # 系统管理页（P2，MVP 可简化）
    components/
      profile/
        ProfileCard.vue           # 8 维画像卡片
        DimensionItem.vue         # 单个维度展示行
        CompletenessBar.vue       # 完整度进度条
        UpdateTimeline.vue        # 更新记录时间线
      graph/
        GraphCanvas.vue           # ECharts 图谱画布
        NodeDetailPanel.vue       # 节点详情侧栏
        PrerequisitePath.vue      # 前置路径展示
      graphrag/
        EvidencePanel.vue         # 证据包展示面板
        SourceCitations.vue       # 引用来源列表
        RankingReasons.vue        # 推荐原因展示
      resources/
        DocumentCard.vue          # 讲解文档卡片
        MindmapCard.vue           # 思维导图卡片
        ExerciseCard.vue          # 练习题卡片
        VideoScriptCard.vue       # 视频脚本卡片
        CodeCaseCard.vue          # 代码案例卡片
        AgentProgressPanel.vue    # 多 Agent 生成进度面板
      common/
        ChatBubble.vue            # 对话气泡
        LoadingSkeleton.vue       # 骨架屏
        ErrorAlert.vue            # 错误提示
        StreamText.vue            # 流式文本渲染
    types/
      profile.ts                  # 画像类型定义
      graph.ts                    # 图谱类型定义
      graphrag.ts                 # GraphRAG 类型定义
      resources.ts                # 资源类型定义
```

---

## 三、页面清单与优先级

### P0（MVP 演示必须，5 页）

| 页面 | 路由 | 说明 |
|---|---|---|
| 对话画像构建 | `/profile/chat` | 自然语言对话收集信息，实时卡片刷新 |
| 学生画像面板 | `/profile/panel` | 8 维画像完整展示 + 更新历史 |
| 课程知识图谱 | `/graph` | ECharts 有向图展示知识点与前置关系 |
| 学习路径 | `/learning-path` | 展示推荐学习序列、节点状态和推荐原因 |
| 多智能体资源生成 | `/resources` | 5 类资源并行生成 + Agent 进度展示 |

### P1（演示增强，3 页）

| 页面 | 路由 | 说明 |
|---|---|---|
| 智能辅导 | `/tutor` | 即时答疑 + 图解/代码/类比切换 |
| 练习测试 | `/exercise` | 作答 + 提交 + 答案解析 |
| 学习效果评估 | `/assessment` | 掌握度雷达图 + 错题归因 |

### P2（MVP 可简化）

| 页面 | 路由 | 说明 |
|---|---|---|
| 登录页 | `/login` | 演示学生入口，可直接预设跳转 |
| 系统管理 | `/admin` | 模型配置、知识库导入，演示时可不展示 |

---

## 四、API 接口列表（后端已实现，直接调用）

后端基地址：`http://127.0.0.1:8000`

### 4.1 画像 API（`/api/profile`）

```typescript
// POST /api/profile/init — 画像初始化（首轮对话）
// 输入: { student_id: string, display_name?: string, message: string }
// 输出: ProfileChatResponse { reply, session_status, current_round, profile, completeness, updated_dimensions, missing_dimensions }

// POST /api/profile/chat — 后续对话
// 输入: { student_id: string, display_name?: string, message: string }
// 输出: ProfileChatResponse（同上）

// GET /api/profile/{student_id} — 获取完整画像
// 输出: StudentProfile

// GET /api/profile/{student_id}/dashboard — 获取仪表盘摘要
// 输出: ProfileDashboardResponse

// GET /api/profile/{student_id}/history — 获取更新记录时间线
// 输出: ProfileUpdateRecord[]

// PATCH /api/profile/{student_id} — 手动修改画像某维度
// 输入: { dimension: string, value: any }
// 输出: StudentProfile

// POST /api/profile/events/exercise-result — 答题后更新画像
// 输入: { student_id, exercise_id, is_correct, ... }
// 输出: ProfileEventResponse

// POST /api/profile/events/learning-progress — 学习进度更新
// 输入: { student_id, completed_node_ids?, in_progress_node_ids?, ... }
// 输出: ProfileEventResponse
```

### 4.2 图谱 API（`/api/graph`）

```typescript
// GET /api/graph/node/{uid} — 查单个知识点
// 输出: GraphNode { uid, labels, properties }

// GET /api/graph/subgraph/{uid} — 查子图
// Query: ?depth=1&include_resources=true
// 输出: SubgraphResult { nodes, edges, paths }
```

### 4.3 GraphRAG API（`/api/graphrag`）

```typescript
// GET /api/graphrag/evidence?uid=ml_gradient_descent — 按 uid 获取证据包
// 输出: EvidencePackage

// POST /api/graphrag/query — 自然语言提问
// 输入: {
//   query: string,
//   student_profile?: { weak_points: string[], preferences: string[], goal?: string, mastery?: Record<string,number> },
//   top_k?: number
// }
// 输出: EvidencePackage {
//   query, resolved_uid, center_node,
//   prerequisites: GraphPath[], related_nodes: GraphPath[],
//   exercises: GraphNode[], document_chunks: GraphNode[],
//   code_cases: GraphNode[], misconceptions: GraphNode[],
//   graph_paths: GraphPath[], sources: GraphNode[],
//   ranking_reason: string[], student_profile_adaptation: object,
//   uncertainty: string[], missing_evidence: string[]
// }
```

### 4.4 诊断 API（`/api/diagnosis`）

```typescript
// POST /api/diagnosis/recommend — 根据画像推荐学习重点
// 输入: { student_profile: StudentProfileInput, top_k?: number }
// 输出: DiagnosisRecommendResponse
```

### 4.5 资源生成 API（`/api/agents`）

```typescript
// POST /api/agents/generate-resources — 多智能体并行生成 5 类资源
// 输入: {
//   node_id: string,
//   student_profile?: StudentProfileInput,
//   resource_types?: string[]  // 默认全部 5 类
// }
// 输出: ResourceGenerateResponse {
//   node_id, resources: ResourceItem[],
//   evidence_package?: EvidencePackage
// }
// 注意：这是一个异步任务，可能返回需要轮询的状态
```

### 4.6 健康检查

```typescript
// GET /health
// 输出: { status: "ok", neo4j: "ok" }
```

---

## 五、核心类型定义

### 5.1 StudentProfile（画像，用于类型参考）

```typescript
interface StudentProfile {
  student_id: string
  created_at: string
  updated_at: string
  completeness: number  // 0-1
  background: {
    major: string       // 如 "计算机科学与技术"
    grade: number | null
    school_type: string // "undergraduate" | "postgraduate"
    course_foundation: string[]
    source: string
    confidence: number
    last_updated: string | null
  }
  learning_goal: {
    goal_type: string[]
    description: string
    target_course: string
    expected_hours_per_week: number | null
    source: string
    confidence: number
    last_updated: string | null
  }
  knowledge_base: {
    known_topics: { topic: string; level: string; evidence: string }[]
    unknown_topics: string[]
    source: string
    confidence: number
    last_updated: string | null
  }
  progress: {
    current_chapter_id: string | null
    completed_node_ids: string[]
    in_progress_node_ids: string[]
    completion_rate: number
    last_active_at: string | null
    source: string
    confidence: number
  }
  cognitive_style: {
    primary: string
    secondary: string
    style_ranking: string[]
    source: string
    confidence: number
    last_updated: string | null
  }
  weak_points: {
    self_reported: { topic: string; node_id: string | null; description: string }[]
    diagnosed: { node_id: string; error_rate: number; total_attempts: number; last_wrong_at: string | null }[]
    source: string
    confidence: number
    last_updated: string | null
  }
  preferences: {
    resource_ranking: string[]
    session_length: string
    difficulty_preference: string
    source: string
    confidence: number
    last_updated: string | null
  }
  ability_state: {
    programming: string
    mathematics: string
    reading_papers: string
    application: string
    source: string
    confidence: number
    last_updated: string | null
  }
  update_history: ProfileUpdateRecord[]
}

interface ProfileUpdateRecord {
  timestamp: string
  trigger: string
  trigger_detail: string
  updated_fields: string[]
  summary: string
}
```

### 5.2 GraphRAG 相关类型

```typescript
interface GraphNode {
  uid: string
  labels: string[]
  properties: Record<string, any>
}

interface GraphPath {
  nodes: GraphNode[]
  relationships: {
    type: string
    source_uid: string
    target_uid: string
    properties: Record<string, any>
  }[]
}

interface EvidencePackage {
  query: string
  resolved_uid: string | null
  center_node: GraphNode | null
  query_type: string
  evidence_score: number  // 0-1，证据包质量评分
  relation_summary: string[]
  recommended_next_actions: string[]
  prerequisites: GraphPath[]
  related_nodes: GraphPath[]
  exercises: GraphNode[]
  document_chunks: GraphNode[]  // 文档内容通过此字段返回，非 "documents"
  code_cases: GraphNode[]
  misconceptions: GraphNode[]
  graph_paths: GraphPath[]
  sources: GraphNode[]
  ranking_reason: string[]
  student_profile_adaptation: Record<string, any>
  uncertainty: string[]
  missing_evidence: string[]
  // 质量字段
  coverage_stats: {
    exercises_count: number
    document_chunks_count: number
    code_cases_count: number
    misconceptions_count: number
    prerequisites_count: number
    related_nodes_count: number
    sources_count: number
  }
  evidence_completeness: {
    has_document: boolean
    has_code_case: boolean
    has_exercises: boolean
    has_misconceptions: boolean
    completeness_score: number  // 0-1
    missing_categories: string[]
  }
  resource_diversity: number  // 0-1
  relevance_score: number  // 0-1
}
```

---

## 六、各页面详细设计要求

### 6.1 对话画像构建页（`/profile/chat`）P0

#### 页面布局

左侧 70%：对话区
右侧 30%：实时画像卡片侧栏

#### 对话区

- 顶部：预设演示学生入口按钮（"使用演示学生"），点击后自动填入预设学生 ID，发送首条消息
- 中部：对话消息列表（系统消息左对齐蓝底、用户消息右对齐灰底）
- 底部：输入框 + 发送按钮 + "已完成"按钮（点击后跳转到画像面板）
- 每轮对话后，消息列表自动滚动到底部
- 系统消息中的追问文本用稍大字号和轻微强调样式

#### 实时画像卡片侧栏

- 显示 `completeness` 进度条（0-100%）
- 8 个维度按已填充/未填充分组显示
- 已填充维度：显示维度名 + 简短摘要 + source 标签 + confidence 百分比
- 未填充维度：灰度显示，标注"待完善"
- 本轮新更新的维度用淡蓝色边框闪烁一次（CSS animation）
- 底部显示"当前轮次 N/6"

#### 预设演示学生

点击"使用演示学生"自动发起首轮对话：

```json
{
  "student_id": "demo_student_001",
  "display_name": "张同学",
  "message": "我是计算机专业大二的，学过 Python 和高数，想学机器学习来完成课程项目。我对梯度下降和神经网络训练不太理解，平时比较喜欢看代码和图解。"
}
```

#### 数据流

1. 首轮：`POST /api/profile/init` → 收到 `ProfileChatResponse` → 更新画像侧栏 → 如果 `session_status === "building"` 且 > 0.75 则提示可完成
2. 后续轮：`POST /api/profile/chat` → 同上
3. 每轮结束后用 `GET /api/profile/{student_id}` 刷新画像侧栏
4. 点击"已完成"：跳转 `/profile/panel`

---

### 6.2 学生画像面板（`/profile/panel`）P0

#### 页面布局

上方：画像完整度进度条 + 最后更新时间
中部：8 维画像卡片（2 列网格，每列 4 个维度卡片）
下方：更新记录时间线

#### 8 维画像卡片

每张卡片包含：
- 维度名称（加粗）
- 维度图标（根据维度类型用不同 Element Plus icon）
- 各子字段的键值对展示
- 来源标签（`<el-tag>`，type 按 source 类型：dialogue=蓝色, exercise=绿色, system=灰色）
- 置信度进度条（`<el-progress>`）
- 如果有 `last_updated`，显示"XX 前更新"
- 右侧有一个小铅笔图标，点击后弹出 `el-dialog` 可编辑该维度

#### 更新记录时间线

使用 `el-timeline` 组件：
- 每条记录显示 `timestamp`（相对时间，如"3 分钟前"）
- `summary` 文本
- `trigger` 标签
- `updated_fields` 以小标签形式展示

#### 底部操作区

- "开始学习"按钮 → 弹窗选择或输入一个知识点，跳转到图谱页或资源生成页
- "继续对话"按钮 → 跳回画像构建页，可继续补充画像

#### 数据流

1. 页面加载：`GET /api/profile/{student_id}` + `GET /api/profile/{student_id}/history`
2. 点击编辑：`PATCH /api/profile/{student_id}`

---

### 6.3 课程知识图谱页（`/graph`）P0

#### 页面布局

左侧 70%：ECharts 有向图主画布
右侧 30%：节点详情侧栏

#### ECharts 有向图

- 使用 ECharts graph 类型或力导向布局
- 节点用不同颜色表示类型：课程的 KnowledgePoint 节点用 `node_type` 或 `role_in_path` 决定颜色
  - entry: 灰色
  - core: 蓝色
  - bridge: 绿色
  - advanced: 橙色
  - extension: 浅灰
- 边用不同颜色和线型表示关系类型：
  - PREREQUISITE: 蓝色实线箭头
  - RELATED: 灰色虚线
  - EXTENDS: 绿色实线箭头
  - CONTRASTS: 橙色点线
- 鼠标悬停节点：显示 tooltip（名称、难度、摘要）
- 点击节点：高亮该节点及其 1 跳邻居，右侧侧栏显示详情
- 支持缩放和拖拽
- 初始展示 P0 主线节点的子图（通过 `GET /api/graph/subgraph/{uid}?depth=1` 逐步加载）

#### 节点详情侧栏

显示选中节点的：
- name（大字标题）
- summary
- difficulty（星级）
- node_type + role_in_path 标签
- keywords
- prerequisites（列表，每个可点击跳转）
- related（列表，每个可点击跳转）
- "查看学习路径"按钮 → 跳转到学习路径页
- "生成学习资源"按钮 → 跳转到资源生成页
- "去提问"按钮 → 跳转到智能辅导页

#### 数据流

1. 页面加载：`GET /api/graph/subgraph/ml_gradient_descent?depth=1`（默认展示主线节点）
2. 点击节点：`GET /api/graph/node/{uid}` + `GET /api/graph/subgraph/{uid}?depth=1`

---

### 6.4 学习路径页（`/learning-path`）P0

#### 页面布局

上方：路径有向图（水平或垂直布局）
下方：推荐节点列表 + 推荐原因

#### 路径展示

- 用 ECharts 或自定义 SVG 展示从基础到目标的知识点路径
- 节点状态用颜色区分：
  - 已完成：绿色
  - 当前：蓝色高亮 + 边框动画
  - 薄弱：橙色（从画像 `weak_points` 读取）
  - 待学习：灰色
  - 锁定（前置未完成）：深灰 + 锁图标
- 节点之间用箭头连线
- 点击节点查看推荐资源和推荐原因

#### 推荐节点列表

- 卡片式列表，每张卡片包含：
  - 知识点名称 + 难度星级
  - 推荐原因文本（从 GraphRAG `ranking_reason` 读取）
  - `recommended_resource_types` 标签
  - "开始学习"按钮 → 跳转到资源生成页
  - "跳过"按钮 → 标记为跳过（调 `POST /api/profile/events/learning-progress`）

#### 数据流

1. 页面加载：`POST /api/diagnosis/recommend`（传入当前画像）→ 获取推荐节点列表
2. 关联图谱数据：对每个推荐节点调 `GET /api/graph/node/{uid}`
3. 跳过节点：`POST /api/profile/events/learning-progress`

---

### 6.5 多智能体资源生成页（`/resources`）P0

#### 页面布局

上方：知识点选择区
中部：Agent 进度面板（5 个 Agent 并行状态）
下方：5 类资源卡片区（Tab 或 垂直排列）

#### 知识点选择区

- 搜索下拉框：输入关键词搜索知识点 → `GET /api/graph/node/{uid}` 或从画像的 `weak_points` 预填
- "生成全部 5 类资源"按钮
- 或单独勾选要生成的资源类型

#### Agent 进度面板

- 5 个 Agent 卡片并排显示：Document / Mindmap / Exercise / VideoScript / Code
- 每张卡片显示当前状态：
  - 等待中（灰色）
  - 检索中（蓝色 loading）
  - 生成中（蓝色 loading + 流式进度文字）
  - 校验中（黄色）
  - 已完成（绿色 ✓）
- 完成后卡片自动展开预览缩略
- 使用 `el-steps` 或自定义步骤条展示整体进度

#### 5 类资源卡片区

**讲解文档卡片**：
- Markdown 渲染区（`markdown-it`）
- 引用来源折叠面板（`el-collapse`，来自 `sources`）

**思维导图卡片**：
- Mermaid 渲染区
- 全屏展开按钮（`el-dialog`）

**练习题卡片**：
- 题目 + 选项/输入框
- 提交按钮 → `POST /api/profile/events/exercise-result`
- 答案解析区（提交后展开）
- "不懂这题"按钮 → 跳转到智能辅导页

**视频脚本卡片**：
- 分镜列表（`el-timeline`），每条含场景描述 + 旁白文案 + 时长

**代码案例卡片**：
- 代码高亮块（`highlight.js`）
- 复制按钮（`el-button` + `navigator.clipboard`）
- 实验任务列表

#### 数据流

1. 选择知识点 + 资源类型 → `POST /api/agents/generate-resources`
2. 轮询或 SSE 接收各 Agent 状态和结果（根据实际 API 返回方式调整）
3. 练习题提交：`POST /api/profile/events/exercise-result`

---

### 6.6 智能辅导页（`/tutor`）P1

#### 页面布局

左侧 60%：对话/回答区
右侧 40%：证据溯源面板

#### 对话区

- 输入框（支持多行）
- 发送后显示 loading，然后流式渲染回答
- 回答下方有形式切换按钮组：图解说明 / 代码示例 / 类比解释 / 练习题推荐
- 点击切换后加载对应形式的回答

#### 证据溯源面板

- 显示本次回答引用的 `document_chunks`
- 显示 `sources` 列表
- 显示 `ranking_reason`
- 如果 `uncertainty` 非空，显示黄色警告

#### 数据流

1. 发送问题：`POST /api/graphrag/query`（传入当前画像）
2. 渲染 Evidence Package
3. 如果要生成答疑内容（文字/图解/代码/类比），需要前端调用另一个生成接口或让后端返回

---

### 6.7 练习测试页（`/exercise`）P1

#### 页面布局

- 题目列表（单选/多选/简答/编程）
- 提交按钮
- 答案解析区

#### 数据流

1. 加载题目：`GET /api/graphrag/evidence?uid=xxx` → 从 `exercises` 字段获取
2. 提交：`POST /api/profile/events/exercise-result`
3. 查看解析：复用 Evidence Package 中的 `document_chunks` + `misconceptions`

---

### 6.8 学习效果评估页（`/assessment`）P1

#### 页面布局

- ECharts 雷达图：知识点掌握度
- 错题知识点分布饼图
- 学习路径完成率卡片
- 下一步建议列表

#### 数据流

1. `GET /api/profile/{student_id}/dashboard`
2. `GET /api/profile/{student_id}` → 从 `weak_points.diagnosed` 计算错题分布

---

## 七、路由设计

```typescript
const routes = [
  { path: '/', redirect: '/profile/chat' },
  { path: '/profile/chat', component: ProfileChatView },
  { path: '/profile/panel', component: ProfilePanelView },
  { path: '/graph', component: KnowledgeGraphView },
  { path: '/learning-path', component: LearningPathView },
  { path: '/resources', component: ResourceGenerationView },
  { path: '/tutor', component: TutorChatView },
  { path: '/exercise', component: ExerciseView },
  { path: '/assessment', component: AssessmentView },
]
```

导航栏（左侧或顶部）用 Element Plus `el-menu`，路由模式为 `router`。

---

## 八、Pinia Store 设计

### profileStore

```typescript
// stores/profile.ts
interface ProfileState {
  studentId: string | null
  displayName: string
  profile: StudentProfile | null
  completeness: number
  sessionStatus: string
  currentRound: number
  missingDimensions: string[]
  history: ProfileUpdateRecord[]
  loading: boolean
  error: string | null
}
```

### learningStore

```typescript
// stores/learning.ts
interface LearningState {
  currentChapter: string | null
  currentNode: GraphNode | null
  evidencePackage: EvidencePackage | null
  generatedResources: ResourceItem[]
  agentStatuses: Record<string, string>
}
```

---

## 九、演示主线页面顺序

比赛 7 分钟视频按以下顺序切换页面，不要跳页：

```text
1. /profile/chat     对话画像构建（1 分钟）
2. /profile/panel     画像卡片展示（30 秒）
3. /graph             图谱定位前置知识（1 分钟）
4. /learning-path     个性化学习路径（45 秒）
5. /resources         5 类资源生成（1.5 分钟）
6. /exercise          练习作答（45 秒）
7. /assessment        学习评估雷达图（45 秒）
8. /profile/panel     画像更新对比（30 秒）
```

导航栏中所有 P0/P1 页面都应该可见，方便演示时手动跳转。

---

## 十、全局样式要求

- 主色调：蓝色系（`#409EFF` Element Plus 默认蓝）
- 背景色：白色（内容区）+ 浅灰（`#f5f7fa` 侧栏）
- 字体：系统默认无衬线，代码块用 `Consolas` / `Fira Code`
- 内容区最大宽度 1400px，居中
- 卡片圆角 8px，轻微阴影
- 页面切换有简单的 fade 过渡（`<transition name="fade">`）
- 所有加载状态必须用骨架屏，不能只有转圈 spinner
- 错误状态显示 `el-alert` 组件，含"重试"按钮
- Agent 生成中不可只有 loading，必须有各 Agent 独立状态展示

---

## 十一、当前注意与约束

1. **后端 API 全部可用**，通过 Axios baseURL `http://127.0.0.1:8000` 访问，不需要 mock
2. **演示学生 ID 固定为 `demo_student_001`**，前端预设该学生数据
3. **5 类资源生成是异步的**，前端需要做好 loading 和状态轮询
4. **图谱页面初始展示 `ml_gradient_descent` 的子图**（这是演示核心节点）
5. **不要引入额外的重型依赖**（如 D3.js、AntV G6），用 ECharts + Element Plus 就够了
6. **所有日期时间字段展示为相对时间**（"3 分钟前""1 小时前"），使用简单的格式化函数
7. **画像卡片中的 `confidence` 字段**：前端展示为进度条或百分比标签
8. **`source` 字段**：前端根据 source 值渲染不同颜色的标签

---

## 十二、你输出的内容

请先输出：

1. 项目的 `package.json` 和 `vite.config.ts`
2. 路由配置 `router/index.ts`
3. Pinia store 完整实现（`stores/profile.ts`、`stores/learning.ts`）
4. Axios API 层完整实现（`api/client.ts` + 各模块 api 文件）
5. TypeScript 类型定义（`types/` 下所有文件）
6. P0 页面的 Vue 组件完整实现：
   - `views/ProfileChatView.vue`
   - `views/ProfilePanelView.vue`
   - `views/KnowledgeGraphView.vue`
   - `views/LearningPathView.vue`
   - `views/ResourceGenerationView.vue`
7. 核心子组件：
   - `components/profile/ProfileCard.vue`
   - `components/graph/GraphCanvas.vue`
   - `components/graphrag/EvidencePanel.vue`
   - `components/resources/AgentProgressPanel.vue`
8. `App.vue` 和 `main.ts`

不需要一次性输出所有页面。先输出 P0 页面，`npm run dev` 能跑起来作为一个完整的演示链路后，再继续。

---

## 十三、输出格式要求

- 用中文注释
- 每个文件标注清晰的文件路径
- Vue 组件用 `<script setup lang="ts">`
- API 调用统一通过 Pinia store 或 api 模块，不要在组件里直接写 `axios.get`
