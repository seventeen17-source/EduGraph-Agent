# Tasks

## P0: 核心闭环修复

- [ ] Task 1: 统一练习来源池 - 后端搜索接口
  - [ ] SubTask 1.1: 在 `app/exercises/service.py` 新增 `search_exercises` 方法，整合题库题（GraphRAG evidence）、AI生成题（GeneratedResourceRecord）、历史错题（ExerciseAttempt where is_correct=false）
  - [ ] SubTask 1.2: 在 `app/exercises/schemas.py` 新增 `ExerciseSearchRequest` 和 `ExerciseSearchResponse` schema，包含 source_type 标签
  - [ ] SubTask 1.3: 在 `app/api/routes/exercises.py` 新增 `POST /exercises/search` 端点
  - [ ] SubTask 1.4: 在 `app/exercises/repository.py` 新增 `search_ai_generated_exercises` 方法，从 GeneratedResourceRecord 中搜索练习题
  - [ ] SubTask 1.5: 在 `app/exercises/repository.py` 新增 `search_mistake_exercises` 方法，从 ExerciseAttempt 中搜索错题

- [ ] Task 2: 统一练习来源池 - 前端搜索 UI
  - [ ] SubTask 2.1: 在 `frontend/src/api/exercises.ts` 新增 `searchExercises` 函数
  - [ ] SubTask 2.2: 在 `frontend/src/types/exercises.ts` 新增 `ExerciseSearchItem` 和 `ExerciseSearchResponse` 类型
  - [ ] SubTask 2.3: 改造 `ExerciseView.vue` 顶部区域：从知识点选择器改为搜索框 + 来源筛选 Tab（全部/题库题/AI生成/我的错题/推荐复习）
  - [ ] SubTask 2.4: 搜索结果列表显示来源标签、题型、难度，点击后加载到练习区
  - [ ] SubTask 2.5: 保留从 URL 参数（resource_id/node_id）预加载的能力

- [ ] Task 3: AI备课台移除默认内容
  - [ ] SubTask 3.1: 在 `ResourceGenerationView.vue` 移除默认 query `'神经网络训练时那个从后往前算梯度的过程是什么'`，改为空字符串
  - [ ] SubTask 3.2: 将资源类型 `selectedTypes` 默认值从全选改为空数组
  - [ ] SubTask 3.3: 新增"生成模式"选择器（快速讲解/做题巩固/图解理解/编程实践/全套学习包），选择模式后自动选中对应资源类型
  - [ ] SubTask 3.4: 当 query 为空且无 route query 参数时，显示引导文案而非默认问题
  - [ ] SubTask 3.5: `resetGeneration` 方法中 `selectedTypes` 不再全选，改为空数组

- [ ] Task 4: 助手生成题后显示"开始作答"按钮
  - [ ] SubTask 4.1: 在 `AssistantView.vue` 的 `bubble-resource-link` 区域，当 `msg.resource_has_exercises` 为 true 时，优先显示"立即开始作答"按钮
  - [ ] SubTask 4.2: 后端 `app/assistant/tools.py` 的 `_resource_reply` 方法中，在回复元数据中添加 `resource_has_exercises` 标志
  - [ ] SubTask 4.3: "开始作答"按钮点击后跳转到 `/exercise?resource_id=xxx`
  - [ ] SubTask 4.4: 保留"查看资源"按钮作为次要操作
  - [ ] SubTask 4.5: 助手生成题后的回复文案改为简洁说明，不内联展示全部题干

- [ ] Task 5: 练习模式选择
  - [ ] SubTask 5.1: 在 `ExerciseAttempt` 模型新增 `mode`（String, default='practice'）、`viewed_answer`（Boolean, default=False）、`grading_method`（String, default='rule'）字段
  - [ ] SubTask 5.2: 在 `ExerciseSessionSubmitRequest` schema 新增 `mode` 字段
  - [ ] SubTask 5.3: 在 `ExerciseAttemptSubmit` schema 新增 `mode`、`viewed_answer`、`grading_method` 字段
  - [ ] SubTask 5.4: 在 `ExerciseView.vue` 新增模式选择器（自由练习/正式测验/错题复习/诊断评估）
  - [ ] SubTask 5.5: 在 `ExerciseCard.vue` 根据模式控制解析/答案显示：测验模式和诊断评估模式提交前隐藏解析
  - [ ] SubTask 5.6: 在 `ExerciseCard.vue` 记录 `used_hint` 和 `viewed_answer` 状态
  - [ ] SubTask 5.7: 在 `ExerciseView.vue` 提交时传递 `mode` 字段到后端

- [ ] Task 6: 后端按题型评分
  - [ ] SubTask 6.1: 在 `app/exercises/service.py` 新增 `grade_attempt` 方法，按 exercise_type 分发评分
  - [ ] SubTask 6.2: 实现 choice 题型规则评分（已有 `_answer_is_correct` 逻辑迁移）
  - [ ] SubTask 6.3: 实现 short_answer 题型 LLM + rubric 评分
  - [ ] SubTask 6.4: 实现 coding 题型结构化评分（先做 LLM 评分，测试用例执行作为后续增强）
  - [ ] SubTask 6.5: 在 `ExerciseSessionSubmitRequest` 中支持 `is_correct=null` 和 `score=null`，后端自动评分
  - [ ] SubTask 6.6: 前端 `ExerciseView.vue` 提交时，非 choice 题型不传 `is_correct`，由后端评分
  - [ ] SubTask 6.7: 前端展示后端返回的 `score`、`feedback`、`grading_method`

- [ ] Task 7: 清理新用户 demo 数据
  - [ ] SubTask 7.1: 在 `AssessmentView.vue` 当无画像数据时不显示示例雷达图，显示引导文案
  - [ ] SubTask 7.2: 在 `LearningPathView.vue` 当无学习路径时不展示 demo 路径，显示引导
  - [ ] SubTask 7.3: 在 `LearningTimeline.vue` 当无练习记录时不显示伪造图表，显示空状态
  - [ ] SubTask 7.4: 检查 `ProfilePanelView.vue` 无画像数据时的空状态处理

## P1: 体验增强

- [ ] Task 8: 知识中心全文搜索
  - [ ] SubTask 8.1: 后端新增 `GET /resources/search?q=xxx` 端点，搜索资源正文、题干、代码
  - [ ] SubTask 8.2: 前端 `KnowledgeCenterView.vue` 搜索框支持全文搜索

- [ ] Task 9: 练习记录显示画像变化
  - [ ] SubTask 9.1: 在 `ExerciseHistoryView.vue` 会话详情中显示 mastery_before/mastery_after 对比
  - [ ] SubTask 9.2: 支持按知识点、来源、题型、时间筛选练习记录

- [ ] Task 10: 学习路径改为推荐队列
  - [ ] SubTask 10.1: 在 `LearningPathView.vue` 将"完整路径"改为分类推荐（当前建议/前置知识/薄弱点复习/可拓展/已掌握）
  - [ ] SubTask 10.2: 每个推荐节点显示推荐理由
  - [ ] SubTask 10.3: 移除"下一章节""完整学习路径"等强线性表达

- [ ] Task 11: 开发者/学生信息分层
  - [ ] SubTask 11.1: 在前端创建 `devMode` composable，控制调试信息显示
  - [ ] SubTask 11.2: 学生侧隐藏 mode=llm、fallback_used、repair_attempts、evidence_score 等字段
  - [ ] SubTask 11.3: fallback 结果对学生以自然语言提示

# Task Dependencies

- Task 2 depends on Task 1（前端搜索 UI 依赖后端搜索接口）
- Task 6 depends on Task 5（评分迁移依赖模式字段新增）
- Task 7 可与 Task 1-6 并行
- Task 8-11 可与 P0 并行启动，但验收在 P0 完成后
