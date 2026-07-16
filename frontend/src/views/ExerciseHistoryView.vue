<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>练习记录</h1>
        <div class="muted">回看每次练习、每道题作答、错题和掌握度变化。</div>
      </div>
      <div class="title-actions">
        <el-button :loading="loading" @click="refresh">刷新</el-button>
        <el-button type="primary" @click="$router.push('/exercise')">继续练习</el-button>
      </div>
    </div>

    <div class="stats-grid">
      <el-card class="stat-card">
        <div class="stat-value">{{ stats?.total_sessions || 0 }}</div>
        <div class="stat-label">练习会话</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-value">{{ stats?.total_attempts || 0 }}</div>
        <div class="stat-label">累计作答</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-value">{{ Math.round((stats?.accuracy || 0) * 100) }}%</div>
        <div class="stat-label">总正确率</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-value">{{ stats?.mistake_count || 0 }}</div>
        <div class="stat-label">错题数</div>
      </el-card>
    </div>

    <el-card class="filter-card" shadow="never">
      <el-input v-model="historyQuery" placeholder="搜索题目、知识点或练习标题" clearable>
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="sourceFilter" placeholder="来源" clearable>
        <el-option label="全部来源" value="" />
        <el-option label="练习页" value="exercise_page" />
        <el-option label="知识中心" value="resource_center" />
        <el-option label="学习助手" value="assistant" />
        <el-option label="学习路径" value="learning_path" />
      </el-select>
      <el-select v-model="typeFilter" placeholder="题型" clearable>
        <el-option label="全部题型" value="" />
        <el-option label="选择题" value="choice" />
        <el-option label="简答题" value="short_answer" />
        <el-option label="编程题" value="coding" />
        <el-option label="案例分析" value="case_analysis" />
      </el-select>
      <el-input v-model="nodeFilter" placeholder="知识点 ID/名称" clearable />
    </el-card>

    <el-tabs v-model="activeTab" class="history-tabs">
      <el-tab-pane label="练习历史" name="sessions">
        <el-empty v-if="!loading && filteredSessions.length === 0" description="暂无练习记录" />
        <div v-else class="session-list">
          <el-card v-for="item in filteredSessions" :key="item.id" class="session-card" shadow="never">
            <div class="session-row">
              <div>
                <div class="session-title">{{ displayTitle(item.title || item.target_node_name || item.target_node_id, '练习记录') }}</div>
                <div class="muted small">
                  {{ formatTime(item.submitted_at) }} · {{ sourceLabel(item.source_type) }} · 用时 {{ formatDuration(item.duration_seconds) }}
                </div>
                <div v-if="sessionMasteryDelta(item).length" class="mastery-delta-row">
                  <el-tag
                    v-for="delta in sessionMasteryDelta(item)"
                    :key="delta.nodeId"
                    size="small"
                    :type="delta.delta >= 0 ? 'success' : 'warning'"
                    effect="plain"
                  >
                    {{ displayNodeLabel(delta.nodeId) }} {{ percentLabel(delta.before) }} → {{ percentLabel(delta.after) }}
                  </el-tag>
                </div>
                <div v-if="item.weak_nodes.length" class="tag-row">
                  <el-tag v-for="node in item.weak_nodes" :key="node" type="warning" size="small">
                    {{ displayNodeLabel(node) }}
                  </el-tag>
                </div>
              </div>
              <div class="session-side">
                <div class="score" :class="scoreClass(item.accuracy)">{{ item.correct_count }}/{{ item.total_count }}</div>
                <el-button size="small" @click="openSession(item.id)">查看详情</el-button>
              </div>
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="错题本" name="mistakes">
        <!-- 错误类型筛选 + 知识点分组 -->
        <div class="mistake-filters">
          <el-radio-group v-model="errorTypeFilter" size="small">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button label="concept_confusion">概念混淆</el-radio-button>
            <el-radio-button label="calculation_error">计算错误</el-radio-button>
            <el-radio-button label="memory_lapse">记忆遗漏</el-radio-button>
            <el-radio-button label="application_failure">应用失误</el-radio-button>
          </el-radio-group>
          <el-select
            v-model="nodeGroupFilter"
            placeholder="按知识点筛选"
            clearable
            filterable
            size="small"
            class="node-group-select"
          >
            <el-option
              v-for="node in availableNodes"
              :key="node.id"
              :label="node.label"
              :value="node.id"
            />
          </el-select>
        </div>

        <el-empty v-if="!loading && filteredMistakes.length === 0" description="暂无错题" />
        <div v-else class="mistake-list">
          <el-card v-for="item in filteredMistakes" :key="item.id" class="mistake-card" shadow="never">
            <div class="mistake-head">
              <strong>{{ displayTitle(item.exercise_title || item.exercise_id, '错题记录') }}</strong>
              <el-tag type="warning" size="small">{{ displayNodeLabel(item.related_node_name || item.related_node_id) }}</el-tag>
              <el-tag v-if="item.error_type" :type="errorTypeTagType(item.error_type)" size="small" effect="dark">
                {{ errorTypeLabel(item.error_type) }}
              </el-tag>
            </div>
            <div class="question-text">{{ displayText(item.exercise_snapshot.question, '题目内容未记录') }}</div>
            <div class="answer-grid">
              <div><span class="muted">你的答案：</span>{{ displayText(item.student_answer.value, '未作答') }}</div>
              <div><span class="muted">正确答案：</span>{{ displayText(item.expected_answer.correct || item.expected_answer.reference_answer, '见解析') }}</div>
            </div>
            <div v-if="item.feedback.explanation" class="feedback-text">{{ displayText(item.feedback.explanation) }}</div>
            <div class="mistake-actions">
              <el-button size="small" @click="askAssistant(item)">让助手讲解</el-button>
              <el-button size="small" type="primary" plain @click="goPractice(item.related_node_id)">重新练习</el-button>
            </div>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="detailOpen" title="练习详情" size="560px">
      <div v-if="selectedSession" class="detail-body">
        <div class="detail-summary">
          <strong>{{ selectedSession.title }}</strong>
          <span>{{ selectedSession.correct_count }}/{{ selectedSession.total_count }} 正确</span>
        </div>
        <div v-if="sessionMasteryDelta(selectedSession).length" class="detail-mastery">
          <div class="small muted">本次练习后的掌握度变化</div>
          <div class="mastery-delta-row">
            <el-tag
              v-for="delta in sessionMasteryDelta(selectedSession)"
              :key="delta.nodeId"
              size="small"
              :type="delta.delta >= 0 ? 'success' : 'warning'"
              effect="plain"
            >
              {{ displayNodeLabel(delta.nodeId) }} {{ percentLabel(delta.before) }} → {{ percentLabel(delta.after) }}
            </el-tag>
          </div>
        </div>
        <div v-for="attempt in selectedSession.attempts" :key="attempt.id" class="attempt-detail" :class="{ wrong: attempt.grading_status === 'graded' && !attempt.is_correct, pending: attempt.grading_status !== 'graded' }">
          <div class="attempt-title">
            <el-tag :type="attemptResultTagType(attempt)" size="small">
              {{ attemptResultLabel(attempt) }}
            </el-tag>
            <el-tag size="small" effect="plain">{{ typeLabel(attempt.exercise_type) }}</el-tag>
            <el-tag size="small" effect="plain">{{ gradingLabel(attempt.grading_method) }}</el-tag>
            <el-tag v-if="attempt.grading_status !== 'graded'" size="small" type="warning" effect="plain">
              {{ gradingStatusLabel(attempt.grading_status) }}
            </el-tag>
            <strong>{{ displayTitle(attempt.exercise_title || attempt.exercise_id, '练习题') }}</strong>
          </div>
          <div class="question-text">{{ displayText(attempt.exercise_snapshot.question) }}</div>
          <div class="answer-grid">
            <div><span class="muted">你的答案：</span>{{ displayText(attempt.student_answer.value, '未作答') }}</div>
            <div><span class="muted">正确答案：</span>{{ displayText(attempt.expected_answer.correct || attempt.expected_answer.reference_answer, '见解析') }}</div>
          </div>
          <div v-if="attempt.feedback.explanation" class="feedback-text">{{ displayText(attempt.feedback.explanation) }}</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

import { getExerciseSession, getExerciseStats, listExerciseMistakes, listExerciseSessions } from '@/api/exercises'
import { useAuthStore } from '@/stores/auth'
import type { ErrorType, ExerciseAttemptRecord, ExerciseSessionRecord, ExerciseStatsResponse } from '@/types/exercises'
import { displayNodeLabel, displaySourceLabel, localizeText } from '@/utils/format'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(false)
const activeTab = ref('sessions')
const stats = ref<ExerciseStatsResponse | null>(null)
const sessions = ref<ExerciseSessionRecord[]>([])
const mistakes = ref<ExerciseAttemptRecord[]>([])
const selectedSession = ref<ExerciseSessionRecord | null>(null)
const detailOpen = ref(false)
const historyQuery = ref('')
const sourceFilter = ref('')
const typeFilter = ref('')
const nodeFilter = ref('')
const errorTypeFilter = ref('')
const nodeGroupFilter = ref('')

const filteredSessions = computed(() => {
  return sessions.value.filter((item) => {
    const q = normalize(historyQuery.value)
    const nodeQ = normalize(nodeFilter.value)
    const text = normalize([
      item.title,
      item.target_node_id,
      item.target_node_name,
      item.weak_nodes.join(' '),
    ].join(' '))
    if (q && !text.includes(q)) return false
    if (sourceFilter.value && item.source_type !== sourceFilter.value) return false
    if (nodeQ && !text.includes(nodeQ)) return false
    return true
  })
})

const availableNodes = computed(() => {
  const nodeMap = new Map<string, { id: string; label: string }>()
  for (const item of mistakes.value) {
    const id = item.related_node_id
    if (!id || nodeMap.has(id)) continue
    const label = displayNodeLabel(item.related_node_name || id)
    nodeMap.set(id, { id, label })
  }
  return [...nodeMap.values()]
})

const filteredMistakes = computed(() => {
  return mistakes.value.filter((item) => {
    const q = normalize(historyQuery.value)
    const nodeQ = normalize(nodeFilter.value)
    const text = normalize([
      item.exercise_title,
      item.exercise_id,
      item.related_node_id,
      item.related_node_name,
      item.exercise_snapshot?.question,
    ].join(' '))
    if (q && !text.includes(q)) return false
    if (typeFilter.value && item.exercise_type !== typeFilter.value) return false
    if (nodeQ && !text.includes(nodeQ)) return false
    // 错误类型筛选
    if (errorTypeFilter.value && item.error_type !== errorTypeFilter.value) return false
    // 知识点分组筛选
    if (nodeGroupFilter.value && item.related_node_id !== nodeGroupFilter.value) return false
    return true
  })
})

async function refresh() {
  const studentId = authStore.studentId
  if (!studentId) return
  loading.value = true
  try {
    const [statsRes, sessionsRes, mistakesRes] = await Promise.all([
      getExerciseStats(studentId),
      listExerciseSessions(studentId, { limit: 50 }),
      listExerciseMistakes(studentId, { limit: 100 }),
    ])
    stats.value = statsRes
    sessions.value = sessionsRes.items
    mistakes.value = mistakesRes.items
  } catch (error: any) {
    ElMessage.error(error.displayMessage || error.message || '练习记录加载失败')
  } finally {
    loading.value = false
  }
}

async function openSession(sessionId: string) {
  if (!authStore.studentId) return
  try {
    selectedSession.value = await getExerciseSession(authStore.studentId, sessionId)
    detailOpen.value = true
  } catch (error: any) {
    ElMessage.error(error.displayMessage || error.message || '练习详情加载失败')
  }
}

function goPractice(nodeId: string) {
  router.push({ path: '/exercise', query: { node_id: nodeId } })
}

function askAssistant(item: ExerciseAttemptRecord) {
  sessionStorage.setItem(
    'assistant_prefill',
    `请讲解我这道错题：${item.exercise_snapshot.question || item.exercise_title}。我的答案是 ${item.student_answer.value || '未作答'}，正确答案是 ${item.expected_answer.correct || item.expected_answer.reference_answer || '见解析'}。`
  )
  router.push('/assistant')
}

function sourceLabel(source: string) {
  const labels: Record<string, string> = {
    exercise_page: '练习页',
    generated_resource: '生成资源',
    resource_center: '知识中心',
    assistant: '学习助手',
    learning_path: '学习路径',
  }
  return labels[source] || displaySourceLabel(source, '未知来源')
}

function typeLabel(type: string) {
  const labels: Record<string, string> = {
    choice: '选择题',
    short_answer: '简答题',
    coding: '编程题',
    case_analysis: '案例分析',
  }
  return labels[type] || displaySourceLabel(type, '未知题型')
}

function errorTypeLabel(errorType: ErrorType) {
  const labels: Record<string, string> = {
    concept_confusion: '概念混淆',
    calculation_error: '计算错误',
    memory_lapse: '记忆遗漏',
    application_failure: '应用失误',
  }
  return labels[errorType || ''] || '未知错误'
}

function errorTypeTagType(errorType: ErrorType): '' | 'success' | 'warning' | 'info' | 'danger' {
  const types: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    concept_confusion: 'danger',
    calculation_error: 'warning',
    memory_lapse: 'info',
    application_failure: '',
  }
  return types[errorType || ''] || 'info'
}

function gradingLabel(method: string) {
  const labels: Record<string, string> = {
    rule: '规则评分',
    llm_rubric: '智能逐点评分',
    llm_code_rubric: '智能代码评分',
    manual_review: '人工复核',
    unsupported: '暂不支持',
    rubric: '量规评分',
  }
  return labels[method] || displaySourceLabel(method, '评分')
}

function gradingStatusLabel(status: string) {
  const labels: Record<string, string> = {
    graded: '已评分',
    pending_review: '待复核',
    unsupported: '暂不支持自动评分',
    failed: '评分失败',
  }
  return labels[status] || displaySourceLabel(status, '未评分')
}

function attemptResultLabel(attempt: ExerciseAttemptRecord) {
  if (attempt.grading_status !== 'graded') return gradingStatusLabel(attempt.grading_status)
  return attempt.is_correct ? '正确' : '错题'
}

function attemptResultTagType(attempt: ExerciseAttemptRecord) {
  if (attempt.grading_status !== 'graded') return 'warning'
  return attempt.is_correct ? 'success' : 'danger'
}

function normalize(value: string) {
  return String(value || '').trim().toLowerCase().replace(/[-_\s]/g, '')
}

function percentLabel(value: number) {
  return `${Math.round((value || 0) * 100)}%`
}

function displayText(value?: unknown, fallback = '') {
  const text = value == null ? '' : String(value)
  return localizeText(text) || fallback
}

function displayTitle(value?: unknown, fallback = '练习记录') {
  const text = displayText(value)
  return text && text !== displaySourceLabel(text, '') ? text : displaySourceLabel(text, fallback)
}

function sessionMasteryDelta(item: ExerciseSessionRecord) {
  const nodeIds = new Set([...Object.keys(item.mastery_before || {}), ...Object.keys(item.mastery_after || {})])
  return [...nodeIds]
    .map((nodeId) => {
      const before = item.mastery_before?.[nodeId] ?? 0
      const after = item.mastery_after?.[nodeId] ?? before
      return { nodeId, before, after, delta: after - before }
    })
    .filter((item) => Math.abs(item.delta) > 0.0001)
}

function scoreClass(accuracy: number) {
  if (accuracy >= 0.8) return 'good'
  if (accuracy >= 0.5) return 'ok'
  return 'bad'
}

function formatDuration(seconds: number) {
  if (!seconds) return '未记录'
  if (seconds < 60) return `${seconds} 秒`
  return `${Math.round(seconds / 60)} 分钟`
}

function formatTime(value: string) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(async () => {
  await refresh()
  const sessionId = route.query.session_id
  if (typeof sessionId === 'string' && sessionId) {
    await openSession(sessionId)
  }
})
</script>

<style scoped>
.title-actions {
  display: flex;
  gap: 10px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 30px;
  font-weight: 700;
  color: #4f46e5;
}

.stat-label {
  margin-top: 4px;
  font-size: 13px;
  color: #64748b;
}

.history-tabs {
  margin-top: 8px;
}

.filter-card {
  margin-bottom: 16px;
}

.filter-card :deep(.el-card__body) {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 140px 140px minmax(160px, 220px);
  gap: 10px;
  align-items: center;
}

.session-list,
.mistake-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.session-card,
.mistake-card {
  border-radius: 8px;
}

.session-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.session-title {
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 4px;
}

.session-side {
  display: flex;
  align-items: center;
  gap: 12px;
}

.score {
  min-width: 72px;
  font-size: 22px;
  font-weight: 700;
  text-align: right;
}

.score.good { color: #059669; }
.score.ok { color: #d97706; }
.score.bad { color: #dc2626; }

.small {
  font-size: 12px;
}

.tag-row {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.mastery-delta-row {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.mistake-head,
.attempt-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.mistake-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.node-group-select {
  width: 220px;
}

.question-text {
  color: #334155;
  line-height: 1.6;
  margin: 8px 0;
}

.answer-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  border-radius: 6px;
  font-size: 13px;
}

.feedback-text {
  margin-top: 8px;
  padding: 8px 10px;
  background: #f0fdf4;
  color: #166534;
  border-radius: 6px;
  line-height: 1.6;
  font-size: 13px;
}

.mistake-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.detail-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 12px;
}

.detail-mastery {
  margin-bottom: 12px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
}

.attempt-detail {
  padding: 12px 0;
  border-bottom: 1px solid #e2e8f0;
}

.attempt-detail.wrong {
  background: #fff7ed;
  margin: 0 -8px;
  padding: 12px 8px;
  border-radius: 8px;
}

.attempt-detail.pending {
  background: #fffbeb;
  margin: 0 -8px;
  padding: 12px 8px;
  border-radius: 8px;
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .session-row,
  .session-side {
    align-items: flex-start;
    flex-direction: column;
  }

  .answer-grid {
    grid-template-columns: 1fr;
  }

  .filter-card :deep(.el-card__body) {
    grid-template-columns: 1fr;
  }
}
</style>
