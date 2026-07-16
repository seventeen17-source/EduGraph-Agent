# Tasks

## P0: 核心决策能力

- [ ] Task 1: 资源生成全类型自修复 - 后端
  - [ ] SubTask 1.1: 在 `app/agents/resource_agents.py` 中提取 ExerciseAgent 的自修复链路为通用方法 `_generate_with_repair(self, generate_fn, validate_fn, repair_fn, max_retries=1)`
  - [ ] SubTask 1.2: 为 DocumentAgent 新增 `_validate_document` 方法（标题非空、正文≥200字、段落结构完整）和 `_repair_document` 方法
  - [ ] SubTask 1.3: 为 CodeAgent 新增 `_validate_code` 方法（代码非空、语言标识有效、有解释说明）和 `_repair_code` 方法
  - [ ] SubTask 1.4: 为 VideoScriptAgent 新增 `_validate_video_script` 方法（结构完整、时长≥30秒）和 `_repair_video_script` 方法
  - [ ] SubTask 1.5: 为 MindmapAgent 新增 `_validate_mindmap` 方法（根节点非空、≥3个二级节点、格式有效）和 `_repair_mindmap` 方法
  - [ ] SubTask 1.6: 改造 DocumentAgent/CodeAgent/VideoScriptAgent/MindmapAgent 的 generate 方法，使用 `_generate_with_repair` 链路
  - [ ] SubTask 1.7: 在 `app/agents/service.py` 的 ResourceGenerationService 中新增 `retry_single_type` 方法，支持单独重试某类资源
  - [ ] SubTask 1.8: 在 `app/api/routes/agents.py` 新增 `POST /agents/retry` 端点，接收 resource_id 和 resource_type

- [ ] Task 2: 资源生成自修复 - 前端
  - [ ] SubTask 2.1: 在 `frontend/src/api/agents.ts` 新增 `retryResourceType` 函数
  - [ ] SubTask 2.2: 在 `ResourceGenerationView.vue` 中对失败资源显示失败原因和"重试"按钮
  - [ ] SubTask 2.3: 重试按钮调用 `retryResourceType`，仅更新对应类型的资源

- [ ] Task 3: 学习路径逐节点解释 - 后端
  - [ ] SubTask 3.1: 在 `app/diagnosis/schemas.py` 新增 `RecommendationEvidence` 和 `RecommendationItem` schema（含 recommendation_type/reason/score/evidence 字段）
  - [ ] SubTask 3.2: 在 `app/diagnosis/service.py` 的 `recommend` 方法中，为每个推荐节点计算 recommendation_type
  - [ ] SubTask 3.3: 实现 `_build_reason` 方法，根据 recommendation_type 和证据生成自然语言理由
  - [ ] SubTask 3.4: 实现 `_compute_score` 方法，综合 mastery/weak_points/遗忘曲线/错题计算推荐分数
  - [ ] SubTask 3.5: 实现 `_gather_evidence` 方法，收集每个推荐节点的证据（source/detail/mastery/last_attempt）
  - [ ] SubTask 3.6: 当当前建议为空时，从推荐队列取第一项补入

- [ ] Task 4: 学习路径逐节点解释 - 前端
  - [ ] SubTask 4.1: 在 `frontend/src/types/diagnosis.ts` 新增 `RecommendationItem` 和 `RecommendationEvidence` 类型
  - [ ] SubTask 4.2: 在 `LearningPathView.vue` 中按 recommendation_type 分组展示（当前建议/前置补缺/薄弱补强/遗忘复习/错题关联）
  - [ ] SubTask 4.3: 每个节点卡片显示 reason 文案和 evidence 来源
  - [ ] SubTask 4.4: 移除前端自行计算分组的逻辑，改为直接使用后端返回的 recommendation_type

- [ ] Task 5: 图谱节点决策面板 - 后端
  - [ ] SubTask 5.1: 在 `app/graph/neo4j_store.py` 新增 `get_node_with_mastery` 方法，联合查询节点信息和该学生的 mastery
  - [ ] SubTask 5.2: 在 `app/graph/neo4j_store.py` 新增 `get_edges_with_weight` 方法，返回边权重和解释
  - [ ] SubTask 5.3: 在 `app/api/routes/graph.py` 新增 `GET /graph/node-detail/{uid}` 端点，返回节点详情+掌握度+遗忘风险+前置关系+推荐决策
  - [ ] SubTask 5.4: 在 `app/profile/timeline.py` 的 ForgettingDetector 中新增 `assess_node_risk` 方法，返回风险等级

- [ ] Task 6: 图谱节点决策面板 - 前端
  - [ ] SubTask 6.1: 在 `frontend/src/api/graph.ts` 新增 `getNodeDetail` 函数
  - [ ] SubTask 6.2: 在 `frontend/src/types/graph.ts` 新增 `NodeDetail` 类型（含 mastery/weak_status/forgetting_risk/recommendation/prerequisites/next_nodes）
  - [ ] SubTask 6.3: 改造 `KnowledgeGraphView.vue` 节点详情面板，展示掌握度/薄弱状态/遗忘风险/推荐决策
  - [ ] SubTask 6.4: 在节点详情面板添加快捷入口按钮（生成资源/去练习/问助手/加入学习路径）
  - [ ] SubTask 6.5: 边显示权重和解释信息

## P1: 证据链与闭环

- [x] Task 7: 画像证据链 - 后端
  - [x] SubTask 7.1: 在 `app/profile/models.py` 的 MasteryEvidence 模型中确保有 source/detail/created_at 字段
  - [x] SubTask 7.2: 在 `app/profile/service.py` 的 `apply_exercise_result` 方法中，每次更新 mastery 时同时写入 MasteryEvidence 记录
  - [x] SubTask 7.3: 在 `app/profile/service.py` 的 weak_points 更新逻辑中，记录 weak_point 的来源证据
  - [x] SubTask 7.4: 在 `app/api/routes/profile.py` 新增 `GET /profile/{student_id}/evidence/{node_id}` 端点，返回某知识点的证据列表
  - [x] SubTask 7.5: 在遗忘检测触发时，写入 source=forgetting_detection 的 MasteryEvidence

- [x] Task 8: 画像证据链 - 前端
  - [x] SubTask 8.1: 在 `frontend/src/api/profile.ts` 新增 `getNodeEvidence` 函数
  - [x] SubTask 8.2: 在 `frontend/src/types/profile.ts` 新增 `MasteryEvidence` 类型
  - [x] SubTask 8.3: 在 `ProfilePanelView.vue` 的 weak_points 区域，每个薄弱点添加"为什么"展开按钮
  - [x] SubTask 8.4: 展开后显示证据列表（来源/详情/时间），按时间倒序

- [x] Task 9: 错题按错误类型聚合 - 后端
  - [x] SubTask 9.1: 在 `app/exercises/models.py` 的 ExerciseAttempt 模型新增 `error_type` 字段（String, nullable）
  - [x] SubTask 9.2: 在 `app/exercises/service.py` 新增 `_classify_error_type` 方法，根据题目类型、学生答案、正确答案判断错误类型
  - [x] SubTask 9.3: 在 `submit_session` 中，对答错的题目调用 `_classify_error_type` 并保存 error_type
  - [x] SubTask 9.4: 在 `app/exercises/repository.py` 的 `list_mistakes` 方法中支持 `error_type` 筛选参数
  - [x] SubTask 9.5: 在 `app/api/routes/exercises.py` 的错题列表端点添加 `error_type` 查询参数

- [x] Task 10: 错题按错误类型聚合 - 前端
  - [x] SubTask 10.1: 在 `frontend/src/types/exercises.ts` 新增 `ErrorType` 类型
  - [x] SubTask 10.2: 在 `ExerciseHistoryView.vue` 错题本中添加错误类型筛选 Tab
  - [x] SubTask 10.3: 每道错题显示错误类型标签和知识点
  - [x] SubTask 10.4: 支持按知识点分组展示错题

- [x] Task 11: 知识中心资源使用状态
  - [x] SubTask 11.1: 在 `app/agents/repository.py` 的 `list_generations` 方法中，关联查询资源是否已练习和练习正确率
  - [x] SubTask 11.2: 在 `app/agents/schemas.py` 的 `ResourceCenterItem` 中新增 `related_nodes`/`is_practiced`/`practice_accuracy`/`source` 字段
  - [x] SubTask 11.3: 在 `app/api/routes/agents.py` 的资源中心列表端点添加 `filter_by_weak_points` 参数
  - [x] SubTask 11.4: 在 `KnowledgeCenterView.vue` 资源卡片中显示关联知识点、质量分、练习状态
  - [x] SubTask 11.5: 在 `KnowledgeCenterView.vue` 添加"按薄弱点筛选"开关

- [x] Task 12: 反馈闭环可见性
  - [x] SubTask 12.1: 在 `app/assistant/feedback_analyzer.py` 中新增 `trigger_feedback_action` 方法，根据反馈类型触发对应动作
  - [x] SubTask 12.2: 在 `app/assistant/service.py` 中，收到负反馈后调用 `trigger_feedback_action`，生成新回复或资源
  - [x] SubTask 12.3: 在 `app/assistant/models.py` 的 AssistantFeedback 模型新增 `action_taken` 和 `action_result` 字段
  - [x] SubTask 12.4: 在 `AssistantView.vue` 中反馈后显示系统响应（"已根据你的反馈重新解释"）
  - [x] SubTask 12.5: 在反馈面板显示历史反馈和系统响应

- [x] Task 13: 成长时间轴可追溯
  - [x] SubTask 13.1: 在 `app/profile/timeline.py` 的 TimelineBuilder 中，为每个事件添加 `related_id` 和 `related_type` 字段
  - [x] SubTask 13.2: 在 `app/profile/schemas.py` 的 TimelineEvent 中新增 `related_id`/`related_type`/`action_url` 字段
  - [x] SubTask 13.3: 遗忘预警事件添加 `action_url` 指向练习页
  - [x] SubTask 13.4: 在 `LearningTimeline.vue` 中为每个事件添加跳转链接
  - [x] SubTask 13.5: 遗忘预警事件显示"去复习"按钮

- [x] Task 14: 学习助手作为系统总入口
  - [x] SubTask 14.1: 在 `app/assistant/tools.py` 中增强动作触发逻辑，生成资源/讲错题/改画像/规划路线时明确返回"已完成什么、下一步去哪"
  - [x] SubTask 14.2: 在 `AssistantView.vue` 中动作卡片显示"下一步建议"区域
  - [x] SubTask 14.3: 助手回复中包含可操作的跳转按钮（去练习/去查看资源/去设置画像）

## P2: 增强体验

- [x] Task 15: 周报/月报
  - [x] SubTask 15.1: 在 `app/profile/service.py` 新增 `generate_weekly_report` 方法
  - [x] SubTask 15.2: 在 `app/api/routes/profile.py` 新增 `GET /profile/{student_id}/report` 端点
  - [x] SubTask 15.3: 在 `LearningGrowthView.vue` 中添加周报/月报展示区域

- [x] Task 16: 多目标学习路径
  - [x] SubTask 16.1: 在 `app/profile/models.py` 的 StudentProfileRecord 中支持多个 learning_goal
  - [x] SubTask 16.2: 在 `app/diagnosis/service.py` 中支持按不同目标分别推荐
  - [x] SubTask 16.3: 在 `LearningPathView.vue` 中支持目标切换

- [x] Task 17: 业务可观测性
  - [x] SubTask 17.1: 在 `app/core/logging.py` 中添加关键业务指标日志（资源生成成功率/评分耗时/推荐点击率）
  - [x] SubTask 17.2: 在 `app/api/routes/admin.py` 新增 `GET /admin/metrics` 端点
  - [x] SubTask 17.3: 在 `AdminView.vue` 中展示业务指标面板

# Task Dependencies

- Task 2 depends on Task 1（前端重试 UI 依赖后端重试接口）
- Task 4 depends on Task 3（前端推荐理由展示依赖后端推荐增强）
- Task 6 depends on Task 5（前端决策面板依赖后端节点详情接口）
- Task 8 depends on Task 7（前端证据展示依赖后端证据接口）
- Task 10 depends on Task 9（前端错题聚合依赖后端错误类型）
- Task 1-6（P0）可部分并行：Task 1+2、Task 3+4、Task 5+6 三组可并行
- Task 7-14（P1）可在 P0 完成后并行启动
- Task 15-17（P2）最后执行
