# 系统智能化增强 Spec

## Why

当前系统经过多轮迭代，基础功能已完善，但各模块缺乏"决策解释"和"自修复"能力：资源生成 Agent 中仅 ExerciseAgent 有完整的生成-校验-修复链路；学习路径推荐不返回逐节点理由；知识图谱节点详情缺乏个性化决策信息；画像 weak_points 无来源追溯；反馈闭环不可见；成长时间轴事件不可追溯。这些缺失导致系统"知其然不知其所以然"，用户信任度低。

## What Changes

### P0（必须先做）

- **资源生成全类型自修复**：DocumentAgent、CodeAgent、VideoScriptAgent 加入"生成-校验-LLM 修复-再校验"链路，失败时保留原因，支持单独重试某类资源
- **学习路径逐节点解释后端化**：后端返回每个推荐节点的 `reason`/`type`/`score`/`evidence`，推荐类型细分为薄弱补强/前置补缺/目标相关/遗忘复习/错题关联，当前建议为空时用推荐队列第一项补上
- **图谱节点详情改成个性化学习决策面板**：节点显示掌握度/薄弱状态/遗忘风险，边增加权重和解释，节点详情显示"为什么推荐/不推荐学这个"，支持从节点直接进入资源/练习/助手/学习路径

### P1（完成后继续）

- **画像证据链**：每个 weak_point/mastery 记录来源（自述/练习/反馈/遗忘检测），前端显示"为什么系统这样判断"
- **错题按错误类型聚合**：错题本按知识点和错误类型分组（概念混淆/计算错误/记忆遗漏/应用失误）
- **知识中心资源使用状态**：显示资源关联知识点、质量分、是否已练习、是否有帮助，支持按薄弱点筛选
- **练习评估统一质量校验**：AI 生成题和题库题质量标准统一，编程题至少做 AST 检查
- **反馈闭环可见性**：反馈后展示系统如何调整，负反馈触发重新解释/补例子/降难度/生成练习
- **成长时间轴可追溯**：时间轴事件关联练习/资源/反馈/画像更新，遗忘预警直接跳转推荐复习
- **学习助手作为系统总入口**：用户请求生成资源/讲错题/改画像/规划路线时，助手明确触发对应动作并告诉用户"已完成什么、下一步去哪"

### P2（增强体验）

- **周报/月报**：自动生成学习总结
- **多目标学习路径**：支持同时追踪多个学习目标
- **业务可观测性**：更完整的运行时指标和追踪

## Impact

- Affected specs: `refactor-exercise-assessment`（练习搜索池和评分迁移部分有交叉，需协调）
- Affected code:
  - 后端: `app/agents/resource_agents.py`（全 Agent 自修复链路）、`app/agents/service.py`（单独重试）、`app/diagnosis/service.py`（逐节点解释）、`app/diagnosis/schemas.py`（推荐结果增强）、`app/graph/neo4j_store.py`（边权重查询）、`app/profile/models.py`（MasteryEvidence 增强）、`app/profile/service.py`（证据链）、`app/profile/timeline.py`（事件关联）、`app/assistant/feedback_analyzer.py`（反馈闭环）、`app/exercises/service.py`（错题聚合）
  - 前端: `views/LearningPathView.vue`（推荐理由展示）、`views/KnowledgeGraphView.vue`（决策面板）、`views/ProfilePanelView.vue`（证据链展示）、`views/KnowledgeCenterView.vue`（资源状态）、`views/ExerciseHistoryView.vue`（错题聚合）、`views/LearningGrowthView.vue`（时间轴追溯）、`views/AssistantView.vue`（动作触发）

---

## ADDED Requirements

### Requirement: 资源生成全类型自修复

系统 SHALL 为所有 5 种资源 Agent（Document/Mindmap/Exercise/Code/VideoScript）提供统一的"生成-校验-LLM 修复-再校验"链路。

#### 自修复链路步骤

1. **生成**：调用 LLM 生成资源
2. **校验**：检查资源结构完整性和内容质量
3. **LLM 修复**：如果校验失败，将失败原因和原始资源传入 LLM 进行修复
4. **再校验**：对修复后的资源再次校验
5. **降级**：如果修复后仍失败，标记为失败并保留原因

#### 质量校验标准

| 资源类型 | 校验项 |
|---------|--------|
| Document | 标题非空、正文 ≥200 字、段落结构完整 |
| Mindmap | 根节点非空、至少 3 个二级节点、Markdown 格式有效 |
| Exercise | 题目数 ≥ 要求、每题有题干+选项+答案、选项 ≥2 个 |
| Code | 代码非空、语言标识有效、有解释说明 |
| VideoScript | 脚本结构完整（场景/旁白/时长）、时长 ≥30 秒 |

#### Scenario: DocumentAgent 生成失败后自修复

- **WHEN** DocumentAgent 生成的文档正文不足 200 字
- **THEN** 系统调用 LLM 修复，传入"正文内容过短，请扩展到至少 200 字"
- **AND** 修复后再次校验，通过则返回，不通过则标记失败并保留原因

#### Scenario: 单独重试某类资源

- **WHEN** 资源生成结果中 Code 类型失败
- **THEN** 前端显示失败原因和"重试"按钮
- **AND** 点击重试后仅重新生成 Code 类型，不影响其他已成功的资源

### Requirement: 学习路径逐节点解释

系统 SHALL 为每个推荐学习节点提供结构化的推荐理由。

#### 推荐节点数据结构

```python
{
    "node_id": "ml_kmeans",
    "node_name": "K-Means 聚类",
    "recommendation_type": "weak_point",  # weak_point/prerequisite/goal_related/forgetting_review/mistake_related
    "reason": "你在最近的练习中 K-Means 相关题目正确率仅 40%，建议优先巩固",
    "score": 0.85,  # 推荐优先级分数 0-1
    "evidence": {
        "source": "exercise_result",
        "detail": "最近 3 次 K-Means 练习中答错 2 次",
        "mastery": 0.4,
        "last_attempt": "2026-07-10"
    }
}
```

#### 推荐类型

| 类型 | 触发条件 | reason 模板 |
|------|---------|------------|
| `weak_point` | 画像 weak_points 中命中 | "你在最近的练习中{node}正确率仅{rate}%，建议优先巩固" |
| `prerequisite` | 图谱前置依赖未掌握 | "学习{next_node}前需要先掌握{node}" |
| `goal_related` | 与学习目标相关 | "这与你的学习目标'{goal}'直接相关" |
| `forgetting_review` | 遗忘曲线预警 | "你上次学习{node}已超过{days}天，建议复习以防遗忘" |
| `mistake_related` | 最近错题关联 | "你最近做错的{mistake_node}题目涉及{node}知识点" |

#### Scenario: 当前建议为空时补上

- **WHEN** 学生没有进行中的节点，当前建议列表为空
- **THEN** 系统从推荐队列中取第一项补入"当前建议"
- **AND** 该节点显示推荐理由和类型

### Requirement: 图谱节点个性化决策面板

系统 SHALL 在知识图谱节点详情中展示个性化学习决策信息。

#### 节点详情面板内容

| 区域 | 信息 |
|------|------|
| 基本信息 | 节点名称、类型、章节、难度 |
| 掌握度状态 | 当前 mastery 值、趋势（上升/下降/稳定）、上次练习时间 |
| 薄弱状态 | 是否在 weak_points 中、薄弱原因 |
| 遗忘风险 | 遗忘曲线预测、建议复习时间 |
| 推荐决策 | "推荐现在学"/"建议先学前置"/"已掌握可跳过"，附理由 |
| 前置关系 | 前置节点列表（含权重和解释）、后续节点列表 |
| 快捷入口 | 生成资源 / 去练习 / 问助手 / 加入学习路径 |

#### Scenario: 节点显示遗忘风险

- **WHEN** 学生某节点上次练习超过 7 天且 mastery 下降趋势
- **THEN** 节点详情显示"遗忘风险：高"
- **AND** 显示"建议复习"按钮，点击跳转到练习页

#### Scenario: 从节点直接进入练习

- **WHEN** 学生在图谱节点详情点击"去练习"
- **THEN** 跳转到 `/exercise?node_id={uid}`
- **AND** 练习页加载该节点的题目

### Requirement: 画像证据链

系统 SHALL 为每个 weak_point 和 node_mastery 记录提供来源证据。

#### 证据来源类型

| source | 说明 |
|--------|------|
| `self_report` | 学生自述（画像对话） |
| `exercise` | 练习结果 |
| `feedback` | 用户反馈 |
| `forgetting_detection` | 遗忘检测 |
| `diagnosis` | 诊断评估 |

#### Scenario: 前端显示"为什么系统这样判断"

- **WHEN** 学生在画像面板查看某个 weak_point "K-Means"
- **THEN** 显示证据来源："练习结果：最近 3 次 K-Means 练习中答错 2 次（2026-07-10）"
- **AND** 如果有多个来源，按时间倒序全部展示

### Requirement: 错题按错误类型聚合

系统 SHALL 在错题本中按知识点和错误类型分组展示。

#### 错误类型

| 类型 | 识别逻辑 |
|------|---------|
| `concept_confusion` | 答案选择了相邻概念（如选了"回归"而正确是"分类"） |
| `calculation_error` | 计算题答案步骤对但结果错 |
| `memory_lapse` | 知识点之前答对过但这次答错 |
| `application_failure` | 概念知道但无法应用到具体问题 |

#### Scenario: 错题本按错误类型筛选

- **WHEN** 学生在错题本选择"概念混淆"筛选
- **THEN** 只显示识别为 concept_confusion 类型的错题
- **AND** 每道题显示错误类型标签和知识点

### Requirement: 知识中心资源使用状态

系统 SHALL 在知识中心资源列表中显示资源的使用状态和关联信息。

#### 资源卡片增强信息

| 字段 | 说明 |
|------|------|
| 关联知识点 | 资源对应的图谱节点 |
| 质量分 | 生成时的 quality_score |
| 是否已练习 | 该资源的练习题是否被作答过 |
| 练习正确率 | 如果已练习，显示正确率 |
| 来源 | 助手生成 / 备课台生成 / 学习路径生成 |

#### Scenario: 按薄弱点筛选资源

- **WHEN** 学生在知识中心选择"按薄弱点筛选"
- **THEN** 只显示关联了学生当前 weak_points 的资源
- **AND** 每个资源显示关联的薄弱点标签

### Requirement: 反馈闭环可见性

系统 SHALL 在用户提交反馈后展示系统如何调整。

#### 反馈触发动作

| 反馈类型 | 系统动作 |
|---------|---------|
| "没看懂" | 重新生成更简单的解释 + 补充例子 |
| "太难了" | 降难度重新生成资源或推荐前置知识 |
| "有错误" | 标记资源待审核 + 重新生成 |
| "太简单了" | 推荐更高难度内容 |
| "想练习" | 生成相关练习题 |

#### Scenario: 负反馈触发重新解释

- **WHEN** 学生对某条助手回复点击"没看懂"
- **THEN** 助手重新生成更简单的解释
- **AND** 消息显示"已根据你的反馈重新解释，降低了理解难度"

### Requirement: 成长时间轴可追溯

系统 SHALL 在成长时间轴中关联练习、资源、反馈和画像更新事件。

#### 时间轴事件类型

| 类型 | 关联 |
|------|------|
| `exercise_session` | 关联练习会话 ID，可跳转查看详情 |
| `resource_generated` | 关联资源记录 ID，可跳转知识中心 |
| `feedback_submitted` | 关联反馈 ID，显示反馈内容和系统响应 |
| `profile_updated` | 关联画像更新事件 ID，显示变更字段 |
| `forgetting_alert` | 关联遗忘预警，可跳转推荐复习 |

#### Scenario: 遗忘预警跳转复习

- **WHEN** 学生在时间轴看到遗忘预警事件
- **THEN** 事件卡片显示"K-Means 知识点可能遗忘，建议复习"
- **AND** 点击"去复习"跳转到练习页加载相关题目

---

## MODIFIED Requirements

### Requirement: DiagnosisService 推荐结果增强

DiagnosisService.recommend 方法返回的每个节点新增以下字段：
- `recommendation_type`: 推荐类型（weak_point/prerequisite/goal_related/forgetting_review/mistake_related）
- `reason`: 推荐理由文案
- `score`: 推荐优先级分数（0-1）
- `evidence`: 证据对象（source/detail/mastery/last_attempt）

### Requirement: 资源生成服务支持单独重试

ResourceGenerationService 新增 `retry_single_type(query, resource_type, ...)` 方法，仅重新生成指定类型的资源，保留其他已成功的资源。

### Requirement: 图谱 API 返回边权重和解释

`GET /api/graph/subgraph/{uid}` 返回的边数据新增 `weight` 和 `explanation` 字段：
- `weight`: 前置依赖强度（0-1）
- `explanation`: "A 是 B 的前置知识，因为掌握 A 是理解 B 的基础"

### Requirement: 错题列表 API 支持错误类型筛选

`GET /api/exercises/mistakes/{student_id}` 新增 `error_type` 查询参数，支持按错误类型筛选。

---

## REMOVED Requirements

### Requirement: 前端自行计算推荐分组

**Reason**: 当前前端 LearningPathView.vue 自行将推荐节点分为"当前建议/需要加强/推荐队列"，逻辑应迁移到后端
**Migration**: 后端返回 recommendation_type 字段，前端直接按 type 分组展示
