export function percent(value?: number | null) {
  return Math.round((value || 0) * 100)
}

export function formatDate(value?: string | null) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间未知'
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function relativeTime(value?: string | null) {
  if (!value) return '暂无记录'
  const date = new Date(value)
  const diff = Date.now() - date.getTime()
  if (Number.isNaN(diff)) return '时间未知'
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  return `${Math.floor(diff / day)} 天前`
}

export function sourceTagType(source?: string) {
  if (!source) return 'info'
  if (source.includes('llm')) return 'primary'
  if (source.includes('dialogue')) return 'primary'
  if (source.includes('exercise')) return 'success'
  if (source.includes('manual')) return 'warning'
  return 'info'
}

export function sourceLabel(source?: string) {
  if (!source) return '待采集'
  if (source.includes('llm')) return '大模型抽取'
  if (source.includes('dialogue')) return '对话采集'
  if (source.includes('exercise')) return '练习诊断'
  if (source.includes('manual')) return '手动修正'
  if (source.includes('system')) return '系统计算'
  if (source.includes('learning_progress')) return '学习进度'
  return source
}

export function nodeName(node?: { properties?: Record<string, any>; uid?: string } | null) {
  const uid = node?.uid
  return displayNodeLabel(node?.properties?.name || node?.properties?.title || uid, '未选择知识点')
}

export function difficultyStars(value?: number) {
  return '★'.repeat(value || 0) + '☆'.repeat(Math.max(0, 5 - (value || 0)))
}

const RELATION_LABELS: Record<string, string> = {
  PREREQUISITE: '前置知识',
  RELATED: '相关知识',
  EXTENDS: '进阶延伸',
  CONTRASTS: '对比辨析',
  SUPPORTS: '资料支撑',
  ASSESSES: '测评关系',
  PRACTICES: '练习关系'
}

const RESOURCE_LABELS: Record<string, string> = {
  document: '讲解文档',
  diagram: '图解',
  mindmap: '思维导图',
  exercise: '练习题',
  video_script: '视频脚本',
  code_case: '代码案例',
  image: '图片',
  code: '代码'
}

const LEVEL_LABELS: Record<string, string> = {
  weak: '薄弱',
  basic: '基础',
  intermediate: '进阶',
  advanced: '熟练',
  beginner: '入门',
  easy: '简单',
  medium: '中等',
  hard: '较难',
  short: '短时学习',
  normal: '常规学习',
  long: '长时学习',
  auto: '系统推荐',
  balanced: '均衡',
  low_confidence: '低置信度',
  filled: '已完善',
  missing: '待完善',
  inferred: '推断'
}

const SESSION_STATUS_LABELS: Record<string, string> = {
  building: '构建中',
  completed: '已完成'
}

const NODE_TYPE_LABELS: Record<string, string> = {
  method: '方法',
  concept: '概念',
  model: '模型',
  algorithm: '算法',
  metric: '指标',
  course: '课程',
  chapter: '章节',
  exercise: '练习'
}

const ROLE_LABELS: Record<string, string> = {
  entry: '入门',
  core: '核心',
  bridge: '承上启下',
  advanced: '进阶',
  support: '支撑',
  extension: '拓展'
}

const AGENT_STATUS_LABELS: Record<string, string> = {
  waiting: '等待中',
  running: '生成中',
  done: '已完成',
  failed: '失败',
  skipped: '已跳过'
}

const AGENT_LABELS: Record<string, string> = {
  RetrievalAgent: '证据检索智能体',
  DocumentAgent: '讲解文档智能体',
  MindmapAgent: '思维导图智能体',
  ExerciseAgent: '练习生成智能体',
  VideoScriptAgent: '视频脚本智能体',
  CodeAgent: '代码案例智能体',
  QualityAgent: '质量校验智能体'
}

const NODE_UID_LABELS: Record<string, string> = {
  ml_activation_function: '激活函数',
  ml_attention_mechanism: '注意力机制',
  ml_backpropagation: '反向传播',
  ml_basic_terms: '机器学习基本术语',
  ml_batchnorm: '批量归一化',
  ml_bayesian_classifier: '贝叶斯分类器',
  ml_bayesian_network: '贝叶斯网',
  ml_bias_variance: '偏差与方差',
  ml_calculus_optimization_basic: '微积分与优化基础',
  ml_clustering: '聚类',
  ml_cnn: '卷积神经网络',
  ml_course: '机器学习课程',
  ml_dataset_split: '训练集/验证集/测试集',
  ml_decision_tree: '决策树',
  ml_dimensionality_reduction: '降维',
  ml_dropout: '随机失活',
  ml_ensemble_learning: '集成学习',
  ml_evaluation_methods: '模型评估方法',
  ml_feature_selection: '特征选择',
  ml_generalization: '泛化能力',
  ml_gradient_descent: '梯度下降',
  ml_gradient_optimization_basic: '梯度与最优化',
  ml_kmeans: 'K均值聚类',
  ml_linear_algebra_basic: '线性代数基础',
  ml_linear_discriminant_analysis: '线性判别分析',
  ml_linear_regression: '线性回归',
  ml_logistic_regression: '逻辑回归',
  ml_loss_function: '损失函数',
  ml_lstm: '长短期记忆网络',
  ml_markov_network: '马尔可夫网',
  ml_mdp: '马尔可夫决策过程',
  ml_metric_learning: '度量学习',
  ml_multilayer_neural_network: '多层神经网络',
  ml_overfitting_underfitting: '过拟合与欠拟合',
  ml_pac_learning: '概率近似正确学习',
  ml_perceptron: '感知机',
  ml_performance_metrics: '性能度量',
  ml_probability_statistics_basic: '概率论与统计基础',
  ml_q_learning: 'Q学习',
  ml_random_forest: '随机森林',
  ml_regularization: '正则化',
  ml_reinforcement_learning: '强化学习',
  ml_rnn: '循环神经网络',
  ml_rule_learning: '规则学习',
  ml_semi_supervised_learning: '半监督学习',
  ml_sgd_minibatch: '小批量随机梯度下降',
  ml_sparse_learning: '稀疏学习',
  ml_supervised_unsupervised: '有监督与无监督',
  ml_svm: '支持向量机',
  ml_transformer: 'Transformer模型',
  ml_vc_dimension: 'VC维',
}

const PROFILE_FIELD_LABELS: Record<string, string> = {
  background: '专业背景',
  learning_goal: '学习目标',
  knowledge_base: '知识基础',
  progress: '学习进度',
  cognitive_style: '认知风格',
  weak_points: '薄弱点',
  preferences: '学习偏好',
  ability_state: '能力水平',
  node_mastery: '知识点掌握度'
}

const PROFILE_TRIGGER_LABELS: Record<string, string> = {
  init_dialogue: '画像初始化',
  update_dialogue: '对话补充',
  exercise_result: '练习诊断',
  learning_progress: '学习进度',
  manual_patch: '手动修正',
  system_recompute: '系统重算'
}

const CHAPTER_LABELS: Record<string, string> = {
  ch01: '第 1 章 机器学习导论',
  ch02: '第 2 章 数学与优化基础',
  ch03: '第 3 章 线性模型与优化',
  ch04: '第 4 章 监督学习算法',
  ch05: '第 5 章 无监督学习与表示',
  ch06: '第 6 章 神经网络与深度学习',
  ch07: '第 7 章 学习理论',
  ch08: '第 8 章 半监督学习',
  ch09: '第 9 章 概率图模型',
  ch10: '第 10 章 规则学习',
  ch11: '第 11 章 强化学习'
}

const GENERAL_LABELS: Record<string, string> = {
  weak_points: '薄弱点',
  document_chunks: '文档证据',
  code_cases: '代码案例',
  misconceptions: '常见误区',
  center_node: '中心知识点',
  resolved_center_node: '已定位的中心知识点',
  center_node_not_found: '未找到中心知识点',
  no_matching_knowledge_point: '未匹配到知识点',
  multiple_candidates: '存在多个候选知识点',
  empty_query: '查询内容为空',
  llm_profile_extractor: '大模型画像抽取',
  llm_rubric: '智能逐点评分',
  llm_code_rubric: '智能代码评分',
  llm_error: '大模型服务异常',
  dialogue_rule: '对话规则抽取',
  exercise_page: '练习页',
  generated_resource: '生成资源',
  resource_center: '知识中心',
  learning_path: '学习路径',
  fallback_used: '使用降级方案',
  source_uids: '证据来源',
  resolved_uid: '定位知识点',
  grounded: '证据支撑',
  repair_actions: '修复动作',
  fallback: '降级检索',
  exact: '精确匹配',
  none: '未匹配',
  self_reported: '学生自述',
  mastery: '掌握度计算',
  GraphRAG: '图谱增强检索',
  Agent: '智能体',
  DocumentChunk: '文档证据',
  MiniBatch: '小批量',
  'Mini-batch': '小批量',
  UID: '编号',
  uid: '编号'
}

const INTERNAL_ID_PREFIX_LABELS: Record<string, string> = {
  ml: '相关知识点',
  faq: 'FAQ 证据',
  chunk: '文档证据',
  code: '代码案例',
  ex: '练习题',
  assess: '测评证据',
  source: '课程来源',
  book: '教材来源',
  mem: '学习记忆',
  session: '练习记录',
  attempt: '作答记录'
}

const INTERNAL_ID_RE = /\b(?:ml|faq|chunk|code|ex|assess|source|book|mem|session|attempt)_[A-Za-z0-9_-]+\b/g

export function isInternalId(value?: string | null) {
  if (!value) return false
  const text = String(value).trim()
  if (NODE_UID_LABELS[text]) return true
  return /^(?:ml|faq|chunk|code|ex|assess|source|book|mem|session|attempt)_[A-Za-z0-9_-]+$/.test(text)
}

export function internalIdLabel(value?: string | null, fallback = '相关内容') {
  if (!value) return fallback
  const text = String(value).trim()
  if (NODE_UID_LABELS[text]) return NODE_UID_LABELS[text]
  const prefix = text.split('_')[0]
  return INTERNAL_ID_PREFIX_LABELS[prefix] || fallback
}

export function relationLabel(type?: string) {
  return type ? RELATION_LABELS[type] || type : '关系'
}

export function resourceLabel(type?: string) {
  return type ? RESOURCE_LABELS[type] || type : '资源'
}

export function levelLabel(level?: string) {
  return level ? LEVEL_LABELS[level] || level : '未判断'
}

export function nodeTypeLabel(type?: string) {
  return type ? NODE_TYPE_LABELS[type] || type : '知识点'
}

export function roleLabel(role?: string) {
  return role ? ROLE_LABELS[role] || role : '支撑'
}

export function agentStatusLabel(status?: string) {
  return status ? AGENT_STATUS_LABELS[status] || status : '等待中'
}

export function agentLabel(agent?: string) {
  return agent ? AGENT_LABELS[agent] || localizeText(agent) : ''
}

export function sessionStatusLabel(status?: string) {
  return status ? SESSION_STATUS_LABELS[status] || status : '构建中'
}

export function uidLabel(uid?: string | null) {
  return uid ? NODE_UID_LABELS[uid] || '' : ''
}

export function chapterLabel(chapter?: string | null) {
  return chapter ? CHAPTER_LABELS[chapter] || localizeText(chapter) : ''
}

export function pathLabel(sourceUid?: string, targetUid?: string) {
  return `${displayNodeLabel(sourceUid)} → ${displayNodeLabel(targetUid)}`
}

export function profileFieldLabel(field?: string) {
  return field ? PROFILE_FIELD_LABELS[field] || field : ''
}

export function profileTriggerLabel(trigger?: string) {
  return trigger ? PROFILE_TRIGGER_LABELS[trigger] || trigger : ''
}

export function profileSummaryLabel(summary?: string) {
  if (!summary) return ''
  let text = localizeText(summary)
  Object.entries(PROFILE_FIELD_LABELS).forEach(([key, value]) => {
    text = text.split(key).join(value)
  })
  Object.entries(PROFILE_TRIGGER_LABELS).forEach(([key, value]) => {
    text = text.split(key).join(value)
  })
  return text
}

export function displayNodeLabel(value?: string | null, fallback = '相关知识点') {
  if (!value) return fallback
  const text = String(value).trim()
  const localized = localizeText(text).trim()
  if (!localized) return fallback
  return isInternalId(localized) ? internalIdLabel(localized, fallback) : localized
}

export function displaySourceLabel(value?: string | null, fallback = '课程证据') {
  if (!value) return fallback
  const text = String(value).trim()
  const localized = localizeText(text).trim()
  if (!localized) return fallback
  return isInternalId(localized) ? internalIdLabel(localized, fallback) : localized
}

export function localizeText(value?: string | null) {
  if (!value) return ''
  let text = String(value)
  text = text
    .replace(/\n?\*\*下一步建议\*\*：已生成\s*0\s*类资源[^。\n]*(?:。)?/g, '')
    .replace(/去练习（\/exercise\?resource_id=[^）]*）/g, '去练习')
    .replace(/去练习\(\/exercise\?resource_id=[^)]*\)/g, '去练习')
    .replace(/去练习类似题目（\/exercise\?node_id=[^）]*）/g, '去练习类似题目')
    .replace(/去练习类似题目\(\/exercise\?node_id=[^)]*\)/g, '去练习类似题目')
    .replace(/查看资源（\/knowledge-center）/g, '查看资源')
    .replace(/查看资源\(\/knowledge-center\)/g, '查看资源')
    .replace(/查看画像（\/profile\/panel）/g, '查看画像')
    .replace(/查看画像\(\/profile\/panel\)/g, '查看画像')
    .replace(/查看路径（\/learning-path）/g, '查看路径')
    .replace(/查看路径\(\/learning-path\)/g, '查看路径')
    .replace(/\/exercise\?resource_id=[^\s)）]+/g, '练习入口')
    .replace(/\/exercise\?node_id=[^\s)）]+/g, '练习入口')
    .replace(/\/knowledge-center/g, '知识中心')
    .replace(/\/profile\/panel/g, '画像面板')
    .replace(/\/learning-path/g, '学习路径')
  const entries = [
    RELATION_LABELS,
    RESOURCE_LABELS,
    LEVEL_LABELS,
    AGENT_LABELS,
    NODE_UID_LABELS,
    PROFILE_FIELD_LABELS,
    PROFILE_TRIGGER_LABELS,
    CHAPTER_LABELS,
    GENERAL_LABELS
  ]
    .flatMap((dict) => Object.entries(dict))
    .sort(([a], [b]) => b.length - a.length)
  entries.forEach(([key, label]) => {
    text = text.split(key).join(label)
  })
  text = text.replace(INTERNAL_ID_RE, (match) => internalIdLabel(match))
  return text
}

export function localizeList(values?: Array<string | null | undefined> | null) {
  return (values || []).filter(Boolean).map((value) => localizeText(value || ''))
}
