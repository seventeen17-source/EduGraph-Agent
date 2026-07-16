# 练习与评估系统重构 Spec

## Why

当前系统中"练习与评估"页面只能搜到题库题（GraphRAG evidence），搜不到 AI 生成的题；AI 备课台保留 demo 默认 query 和全选资源类型；助手生成题后只提供"查看资源"按钮；练习和评估模式未区分；简答题/代码题用字符串精确匹配评分；新用户体验混有 demo 痕迹。这些问题导致练习闭环断裂、用户体验混乱、画像数据不准确。

## What Changes

### P0（必须先做）

- **统一练习来源池**：练习页搜索不再只搜知识点，而是搜"可练习内容"，整合题库题、AI生成题、历史错题、推荐复习题
- **AI备课台移除默认内容**：移除默认 query "神经网络训练时…"，资源类型改为"生成模式"选择（快速讲解/做题巩固/图解理解/编程实践/全套学习包）
- **助手生成题后主按钮改为"立即开始作答"**：当生成资源含 exercises 时，消息卡片优先显示"开始作答"按钮，不内联展示全部题干
- **区分练习模式和评估模式**：新增模式选择（自由练习/正式测验/错题复习/诊断评估），测验模式提交前禁止查看解析，数据层记录 mode/used_hint/viewed_answer
- **简答题/代码题评分迁移到后端**：按题型区分评分（choice: 规则, short_answer: LLM+rubric, coding: 测试用例+LLM, case_analysis: rubric 分项），前端只负责提交答案
- **清理新用户 demo 数据**：新注册用户不显示示例雷达图、demo 路径、伪造图表，fallback 内容不伪装成真实个性化结果

### P1（完成后继续）

- **全局搜索**：新增全局搜索能力，返回知识点/文档/FAQ/题目/错题/代码案例等，按类型分组
- **知识中心全文搜索**：不只搜标题和 query，还搜资源正文、题干、代码、知识点
- **练习记录显示画像变化**：显示 mastery_before/mastery_after，支持按知识点/来源/题型/时间筛选
- **学习路径改为推荐队列**：弱化线性编号，改为"当前建议/前置知识/薄弱点复习/可拓展/已掌握"，每个节点显示推荐理由
- **开发者/学生信息分层**：学生侧不显示 mode=llm、fallback_used 等调试字段，管理员可查看完整 trace

## Impact

- Affected code:
  - 后端: `app/exercises/`（models/schemas/service/routes）、`app/agents/`（models/service/resource_agents）、`app/assistant/tools.py`、`app/api/routes/`、`app/core/config.py`
  - 前端: `views/ExerciseView.vue`、`views/ResourceGenerationView.vue`、`views/AssistantView.vue`、`views/ExerciseHistoryView.vue`、`views/LearningPathView.vue`、`stores/learning.ts`、`stores/profile.ts`、`api/exercises.ts`、`components/resources/ExerciseCard.vue`

---

## ADDED Requirements

### Requirement: 统一练习来源池

系统 SHALL 提供统一的练习题目搜索接口，整合多种来源的练习题。

#### 来源类型

| 来源 | 数据源 | source_type 标识 |
|------|--------|-----------------|
| 题库题 | Neo4j / GraphRAG evidence exercises | `knowledge_base` |
| AI生成题 | GeneratedResourceRecord.resources.exercises | `ai_generated` |
| 历史错题 | ExerciseAttempt where is_correct=false | `mistake` |
| 推荐复习题 | 根据 weak_points + 遗忘曲线生成 | `recommended` |

#### Scenario: 学生搜索 K-Means 时返回多来源题目

- **WHEN** 学生在练习页搜索 "K-Means"
- **THEN** 系统返回题库中的 K-Means 题 + 之前 AI 生成过的 K-Means 题 + 做错过的 K-Means 相关题
- **AND** 每条结果标注来源（题库题 / AI生成 / 错题 / 推荐）

#### Scenario: 从搜索结果进入作答

- **WHEN** 学生从搜索结果选择题目并开始作答
- **THEN** 提交后保存练习记录、错题和画像更新，与正常练习流程一致

### Requirement: 练习模式选择

系统 SHALL 提供四种练习模式，不同模式下 UI 行为和数据记录不同。

| 模式 | 可看提示 | 可看解析 | 记录用时 | mastery 权重 |
|------|---------|---------|---------|-------------|
| 自由练习 | 是 | 是 | 是 | 正常 |
| 正式测验 | 否 | 提交后 | 是 | 1.5x |
| 错题复习 | 是 | 提交后 | 是 | 0.8x |
| 诊断评估 | 否 | 提交后 | 是 | 1.2x |

#### Scenario: 测验模式提交前不能查看解析

- **WHEN** 学生选择"正式测验"模式
- **THEN** 提交前解析/答案区域被隐藏
- **AND** 提交时记录 mode=test、time_spent_seconds、used_hint=false

#### Scenario: 练习模式看提示后答对

- **WHEN** 学生在"自由练习"模式中查看了提示后答对
- **THEN** 记录 used_hint=true、viewed_answer=false
- **AND** 画像更新时区分"独立答对"和"看提示后答对"

### Requirement: 后端按题型评分

系统 SHALL 在后端按题型区分评分，前端不再自行判断所有题型对错。

| 题型 | 评分方式 | grading_method |
|------|---------|---------------|
| choice | 规则匹配（字符串/索引比较） | `rule` |
| short_answer | LLM + rubric 评分 | `llm_rubric` |
| coding | 运行测试用例 + LLM 解释 | `code_execution` |
| case_analysis | rubric 分项评分 | `rubric` |

#### Scenario: 简答题同义表达不误判

- **WHEN** 学生简答题答案语义正确但措辞不同
- **THEN** LLM 评分识别为正确，score=1.0
- **AND** 保存 grading_method=llm_rubric 和评分理由

#### Scenario: 代码题结构化评分

- **WHEN** 学生提交代码题答案
- **THEN** 系统运行测试用例并给出结构化评分（correctness/score/feedback）
- **AND** 保存 grading_method=code_execution

### Requirement: AI备课台初始状态为空

系统 SHALL 在用户直接打开 AI 备课台时显示空状态和引导，不预设默认 query。

#### 预填场景

仅以下场景预填 query：
- 从知识图谱点击"生成资源"进入（带 node_id query 参数）
- 从助手动作卡片进入
- 从知识中心点击"基于该问题再生成"
- 从学习路径某节点进入

#### 生成模式选择

| 模式 | 默认选中资源类型 |
|------|----------------|
| 快速讲解 | document |
| 做题巩固 | exercise |
| 图解理解 | mindmap |
| 编程实践 | code_case |
| 全套学习包 | 全部（需用户明确选择） |

#### Scenario: 直接打开 AI 备课台

- **WHEN** 用户直接访问 /resources（无 query 参数）
- **THEN** 输入框为空，页面展示引导文案
- **AND** 资源类型默认不全选

### Requirement: 助手生成题后显示"开始作答"按钮

系统 SHALL 在助手生成含 exercises 的资源后，在消息卡片中优先显示"立即开始作答"按钮。

#### 按钮优先级

1. **立即开始作答**（主按钮，当 resources 含 exercises 时显示）
2. 查看资源详情
3. 重新生成题目
4. 加入复习计划

#### Scenario: 生成题后不内联展示

- **WHEN** 用户对助手说"帮我生成 10 道 K-Means 选择题"
- **THEN** 助手回复简洁说明"已生成 10 道 K-Means 选择题，已保存到知识中心。你可以直接开始作答。"
- **AND** 聊天气泡不展开全部题干和选项
- **AND** 消息卡片显示"开始作答"按钮
- **AND** 点击后进入练习页并加载本次生成的题

### Requirement: 清理新用户 demo 数据

系统 SHALL 区分普通用户和演示用户，普通新用户不显示 demo/fallback 假数据。

#### Scenario: 新用户进入评估页

- **WHEN** 没有画像数据的新注册用户进入评估页
- **THEN** 不显示示例雷达图
- **AND** 显示引导文案"完成一次练习后这里会显示你的掌握度画像"

#### Scenario: 新用户进入学习路径

- **WHEN** 没有学习路径的新用户进入学习路径页
- **THEN** 不自动展示 demo 路径
- **AND** 显示"设置学习目标"或"做一次诊断评估"引导

---

## MODIFIED Requirements

### Requirement: ExerciseAttempt 数据模型增强

ExerciseAttempt 模型新增以下字段以支持模式区分和评分增强：

| 字段 | 类型 | 说明 |
|------|------|------|
| mode | String(40) | 练习模式：practice/test/review/diagnosis |
| viewed_answer | Boolean | 是否在提交前查看过解析 |
| grading_method | String(40) | 评分方式：rule/llm_rubric/code_execution/rubric |

### Requirement: 练习页搜索 UI 改造

练习页从"知识点选择器"改为"统一搜索 + 来源筛选"：
- 搜索框：输入关键词搜索可练习内容
- 来源筛选 Tab：全部 / 题库题 / AI生成 / 我的错题 / 推荐复习
- 搜索结果：每条题目显示来源标签、题型、难度
- 选中后加载到练习区开始作答

### Requirement: 前端评分逻辑迁移

前端 ExerciseCard 组件不再自行判断 short_answer/coding/case_analysis 题型对错：
- choice 题：前端可即时反馈
- 其他题型：提交答案到后端，由后端评分后返回结果
- 前端展示后端返回的 score/feedback/grading_method

---

## REMOVED Requirements

### Requirement: AI备课台默认 query

**Reason**: demo 遗留的默认问题"神经网络训练时那个从后往前算梯度的过程是什么"会让用户觉得系统在乱生成
**Migration**: 移除默认值，改为空输入框 + 引导文案

### Requirement: AI备课台默认全选资源类型

**Reason**: 用户还没表达需求就全选 5 种资源类型，生成大量不需要的内容
**Migration**: 改为"生成模式"选择器，默认不选中任何类型

### Requirement: 前端字符串精确匹配评分

**Reason**: 简答题/代码题/案例题用字符串比较会误判，影响画像准确性
**Migration**: 评分逻辑迁移到后端，按题型区分评分方式
