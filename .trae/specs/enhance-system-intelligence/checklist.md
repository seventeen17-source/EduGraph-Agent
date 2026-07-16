# Checklist

## P0: 资源生成全类型自修复

- [ ] DocumentAgent 有 _validate_document 和 _repair_document 方法
- [ ] CodeAgent 有 _validate_code 和 _repair_code 方法
- [ ] VideoScriptAgent 有 _validate_video_script 和 _repair_video_script 方法
- [ ] MindmapAgent 有 _validate_mindmap 和 _repair_mindmap 方法
- [ ] 所有 Agent 使用统一的 _generate_with_repair 链路
- [ ] 失败资源保留失败原因
- [ ] 后端 `POST /agents/retry` 端点支持单独重试某类资源
- [ ] 前端失败资源显示原因和"重试"按钮
- [ ] 点击重试后仅更新对应类型资源

## P0: 学习路径逐节点解释

- [ ] 后端推荐结果每个节点包含 recommendation_type 字段
- [ ] 后端推荐结果每个节点包含 reason 文案
- [ ] 后端推荐结果每个节点包含 score 分数
- [ ] 后端推荐结果每个节点包含 evidence 证据对象
- [ ] 推荐类型细分为 weak_point/prerequisite/goal_related/forgetting_review/mistake_related
- [ ] 当前建议为空时用推荐队列第一项补上
- [ ] 前端按 recommendation_type 分组展示
- [ ] 每个节点卡片显示推荐理由
- [ ] 前端不再自行计算分组

## P0: 图谱节点决策面板

- [ ] 节点详情显示当前 mastery 值和趋势
- [ ] 节点详情显示薄弱状态和原因
- [ ] 节点详情显示遗忘风险等级
- [ ] 节点详情显示推荐决策（推荐学/先学前置/可跳过）及理由
- [ ] 前置节点列表显示权重和解释
- [ ] 节点详情有快捷入口：生成资源/去练习/问助手/加入学习路径
- [ ] 点击"去练习"跳转到 /exercise?node_id={uid}
- [ ] 边显示权重和解释信息

## P1: 画像证据链

- [x] MasteryEvidence 模型有 source/detail/created_at 字段
- [x] 练习更新 mastery 时写入 MasteryEvidence 记录
- [x] weak_points 更新时记录来源证据
- [x] 遗忘检测触发时写入 source=forgetting_detection 证据
- [x] 后端有 `GET /profile/{student_id}/evidence/{node_id}` 端点
- [x] 前端画像面板 weak_points 有"为什么"展开按钮
- [x] 展开后显示证据列表（来源/详情/时间）

## P1: 错题按错误类型聚合

- [x] ExerciseAttempt 模型有 error_type 字段
- [x] 后端 _classify_error_type 方法能识别 4 种错误类型
- [x] 答错题目保存 error_type
- [x] 错题列表 API 支持 error_type 筛选
- [x] 前端错题本有错误类型筛选 Tab
- [x] 每道错题显示错误类型标签
- [x] 支持按知识点分组展示

## P1: 知识中心资源使用状态

- [x] 资源列表返回 related_nodes（关联知识点）
- [x] 资源列表返回 is_practiced（是否已练习）
- [x] 资源列表返回 practice_accuracy（练习正确率）
- [x] 资源列表返回 source（生成来源）
- [x] 前端资源卡片显示关联知识点标签
- [x] 前端资源卡片显示质量分和练习状态
- [x] 支持"按薄弱点筛选"资源

## P1: 反馈闭环可见性

- [x] 后端 trigger_feedback_action 方法根据反馈类型触发动作
- [x] 负反馈触发重新解释/补例子/降难度
- [x] AssistantFeedback 模型有 action_taken 和 action_result 字段
- [x] 前端反馈后显示系统响应
- [x] 反馈面板显示历史反馈和系统响应

## P1: 成长时间轴可追溯

- [x] 时间轴事件包含 related_id 和 related_type
- [x] 练习事件关联练习会话 ID，可跳转
- [x] 资源生成事件关联资源记录 ID，可跳转
- [x] 反馈事件关联反馈 ID
- [x] 画像更新事件关联更新事件 ID
- [x] 遗忘预警事件有"去复习"按钮
- [x] 点击"去复习"跳转到练习页

## P1: 学习助手作为系统总入口

- [x] 助手生成资源后回复包含"已完成什么、下一步去哪"
- [x] 助手讲错题后回复包含下一步建议
- [x] 助手改画像后回复包含确认信息
- [x] 助手规划路线后回复包含跳转入口
- [x] 前端动作卡片显示"下一步建议"区域
- [x] 助手回复包含可操作跳转按钮

## P2: 增强体验

- [x] 后端能生成周报/月报
- [x] 前端学习成长页面有周报/月报展示
- [x] 支持多个学习目标
- [x] 学习路径页面支持目标切换
- [x] 关键业务指标有日志记录
- [x] 管理员面板展示业务指标
