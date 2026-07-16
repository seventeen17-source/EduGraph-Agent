<template>
  <div class="page">
    <div class="page-title">
      <div class="page-title-left">
        <div class="page-title-icon">📝</div>
        <div class="page-title-info">
          <h1>练习与评估</h1>
          <div class="muted">选择知识点，加载练习题目，提交后回写学生画像并获取诊断建议</div>
        </div>
      </div>
    </div>

    <ErrorAlert :message="error" />

    <!-- 统一练习搜索 -->
    <el-card class="section-card selector-card" shadow="never">
      <div class="selector-row unified-selector">
        <el-input
          v-model="exerciseQuery"
          placeholder="搜索可练习内容，如 K-Means、反向传播、过拟合"
          clearable
          @keyup.enter="searchExercisePool"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-segmented v-model="sourceFilter" :options="sourceOptions" />
        <el-select v-model="exerciseMode" class="mode-select" placeholder="练习模式">
          <el-option v-for="mode in modeOptions" :key="mode.value" :label="mode.label" :value="mode.value" />
        </el-select>
        <div class="selector-actions">
          <el-button
            type="primary"
            :loading="loadingQuizzes"
            :disabled="!canSearchExercisePool"
            @click="searchExercisePool"
          >
            搜索题目
          </el-button>
          <el-button
            v-if="searchItems.length"
            plain
            @click="loadSearchResults"
          >
            加载全部结果
          </el-button>
          <el-button
            v-if="!submitted && exercises.length"
            plain
            @click="resetSession"
          >
            <el-icon><RefreshLeft /></el-icon> 重置
          </el-button>
        </div>
      </div>
      <div class="mode-hint">{{ currentModeHint }}</div>
      <div v-if="searchItems.length" class="exercise-search-results">
        <button
          v-for="item in searchItems"
          :key="item.id"
          class="exercise-search-item"
          @click="loadSearchItem(item)"
        >
          <div class="search-item-main">
            <strong>{{ localizeText(item.title || '练习题') }}</strong>
            <span>{{ localizeText(item.question) }}</span>
          </div>
          <div class="search-item-meta">
            <el-tag size="small" :type="sourceTagType(item.source_type)">{{ displaySourceLabel(item.source_label || item.source_type, '练习来源') }}</el-tag>
            <el-tag v-if="item.review_type" size="small" type="danger" effect="plain">{{ reviewTypeLabel(item.review_type) }}</el-tag>
            <el-tag size="small" effect="plain">{{ typeLabel(item.type) }}</el-tag>
            <el-rate :model-value="item.difficulty || 3" disabled size="small" show-score />
          </div>
          <div v-if="item.review_reasons?.length" class="review-reasons">
            <span v-for="reason in item.review_reasons.slice(0, 2)" :key="reason">{{ localizeText(reason) }}</span>
          </div>
        </button>
      </div>
      <!-- 快捷知识点 -->
      <div v-if="!exerciseQuery && !exercises.length" class="quick-topics">
        <span class="muted">推荐入口：</span>
        <el-tag
          v-for="topic in quickTopics"
          :key="topic.uid"
          class="quick-tag"
          effect="plain"
          @click="quickSelect(topic.uid)"
        >
          {{ topic.label }}
        </el-tag>
      </div>
    </el-card>

    <!-- Loading -->
    <LoadingSkeleton v-if="loadingQuizzes" :rows="6" />

    <!-- 会话信息栏 -->
    <div v-if="exercises.length && !submitted" class="session-bar">
      <div class="session-info">
        <el-tag type="primary">{{ displayNodeLabel(currentNodeName) }}</el-tag>
        <span class="muted">共 {{ exercises.length }} 题 · 难度分布：
          <el-rate
            :model-value="avgDifficulty"
            disabled
            size="small"
            show-score
          />
        </span>
      </div>
    </div>

    <div class="exercise-layout">
      <div class="exercise-main">
        <ExerciseCard
          :key="sessionKey"
          :exercises="exercises"
          :mode="exerciseMode"
          :submitted="submitted"
          :correct-count="correctCount"
          :correct-nodes="correctNodes"
          :weak-nodes="weakNodes"
          :uid-label-map="uidLabels"
          @submit="submitRoundRecorded"
          @retry="resetSession"
          @view-in-graph="goToGraph"
          @ask-assistant="goAskAssistant"
        />

        <!-- 提交后的操作区 -->
        <div v-if="submitted" class="result-actions">
          <div class="result-card" :class="scoreClass">
            <div class="result-icon">{{ scoreIcon }}</div>
            <div class="result-main">
              <div class="result-score">
                <span class="score-number">{{ animatedCorrect }}<span class="score-divider">/</span>{{ exercises.length }}</span>
                <span class="score-percent">{{ scorePercent }}%</span>
              </div>
              <div class="result-text">{{ scoreText }}</div>
            </div>
            <div class="result-stars">
              <el-rate
                v-model="starRating"
                disabled
                size="large"
                show-score
                score-template="{value}星"
              />
            </div>
          </div>
          <div class="result-buttons">
            <el-button type="primary" @click="resetSession"><el-icon><RefreshLeft /></el-icon> 再做一遍</el-button>
            <el-button @click="goToHistory"><el-icon><Document /></el-icon> 查看练习记录</el-button>
            <el-button @click="goToGraph(weakNodes)"><el-icon><Share /></el-icon> 薄弱知识点</el-button>
            <el-button @click="goAskAssistant('')"><el-icon><ChatDotRound /></el-icon> 请助手分析</el-button>
          </div>
          <div v-if="weakNodes.length" class="result-weak">
            <span class="weak-label">⚠️ 需要加强：</span>
            <el-tag v-for="nid in weakNodes" :key="nid" type="warning" size="small" effect="plain" class="weak-tag" @click="goToGraph([nid])">
              {{ displayNodeLabel(uidLabels[nid] || nid) }}
            </el-tag>
          </div>
        </div>
      </div>

      <EvidencePanel v-if="learningStore.evidencePackage" :evidence="learningStore.evidencePackage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Document, RefreshLeft, Search, Share } from '@element-plus/icons-vue'

import EvidencePanel from '@/components/graphrag/EvidencePanel.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import ExerciseCard from '@/components/resources/ExerciseCard.vue'
import { searchExercises } from '@/api/exercises'
import { searchGraphNodes } from '@/api/graph'
import { useLearningStore } from '@/stores/learning'
import { useProfileStore } from '@/stores/profile'
import type { ExerciseSearchItem, ExerciseSourceType } from '@/types/exercises'
import type { GeneratedExercise } from '@/types/resources'
import type { GraphNode } from '@/types/graph'
import { displayNodeLabel, displaySourceLabel, localizeText } from '@/utils/format'

const router = useRouter()
const route = useRoute()
const learningStore = useLearningStore()
const profileStore = useProfileStore()

// 知识点选择
const selectedNodeId = ref('')
const currentNodeName = ref('')
const searchResults = ref<GraphNode[]>([])
const searchingNodes = ref(false)
const exerciseQuery = ref('')
const sourceFilter = ref<ExerciseSourceType>('all')
const searchItems = ref<ExerciseSearchItem[]>([])
const exerciseMode = ref<'practice' | 'test' | 'review' | 'diagnosis'>('practice')

const sourceOptions = [
  { label: '全部', value: 'all' },
  { label: '题库题', value: 'knowledge_base' },
  { label: 'AI生成', value: 'ai_generated' },
  { label: '我的错题', value: 'mistake' },
  { label: '推荐复习', value: 'recommended' },
]

const modeOptions = [
  { label: '自由练习', value: 'practice' },
  { label: '正式测验', value: 'test' },
  { label: '错题复习', value: 'review' },
  { label: '诊断评估', value: 'diagnosis' },
]

const currentModeHint = computed(() => {
  const hints: Record<string, string> = {
    practice: '自由练习：可以查看提示和解析，系统会记录辅助行为。',
    test: '正式测验：提交前隐藏提示和解析，结果会作为更强的掌握度信号。',
    review: '错题复习：适合二次巩固历史错题。',
    diagnosis: '诊断评估：提交前隐藏提示和解析，用于判断当前薄弱点。',
  }
  return hints[exerciseMode.value]
})
const canSearchExercisePool = computed(() => {
  return Boolean(exerciseQuery.value.trim()) || ['recommended', 'mistake'].includes(sourceFilter.value)
})
const searchNodes = async (q: string) => {
  if (!q || q.length < 1) { searchResults.value = []; return }
  searchingNodes.value = true
  try {
    const results = await searchGraphNodes(q, 10)
    searchResults.value = results.filter(n =>
      n.labels?.includes('KnowledgePoint')
    )
  } catch { searchResults.value = [] }
  finally { searchingNodes.value = false }
}

const baseQuickTopics = [
  { uid: 'ml_backpropagation', label: '反向传播' },
  { uid: 'ml_gradient_descent', label: '梯度下降' },
  { uid: 'ml_kmeans', label: 'K-Means' },
  { uid: 'ml_logistic_regression', label: '逻辑回归' },
  { uid: 'ml_cnn', label: '卷积神经网络' },
  { uid: 'ml_decision_tree', label: '决策树' },
  { uid: 'ml_svm', label: '支持向量机' },
  { uid: 'ml_overfitting_underfitting', label: '过拟合与欠拟合' },
]
const quickTopics = computed(() => {
  const dynamic: Array<{ uid: string; label: string }> = []
  const seen = new Set<string>()
  const add = (uid?: string | null) => {
    if (!uid || seen.has(uid)) return
    seen.add(uid)
    dynamic.push({ uid, label: displayNodeLabel(uid) })
  }
  for (const uid of profileStore.studentProfileInput.weak_points || []) add(uid)
  const mastery = profileStore.profile?.node_mastery || {}
  Object.entries(mastery)
    .filter(([, item]) => (item.mastery_score || 1) < 0.6)
    .sort((a, b) => (a[1].mastery_score || 1) - (b[1].mastery_score || 1))
    .slice(0, 4)
    .forEach(([uid]) => add(uid))
  for (const topic of baseQuickTopics) add(topic.uid)
  return dynamic.slice(0, 8)
})

function quickSelect(uid: string) {
  selectedNodeId.value = uid
  exerciseQuery.value = displayNodeLabel(uid)
  loadQuizzes()
}

function onNodeSelected(uid: string) {
  if (uid) loadQuizzes()
}

// 练习会话状态
const exercises = ref<GeneratedExercise[]>([])
const submitted = ref(false)
const correctCount = ref(0)
const correctNodes = ref<string[]>([])
const weakNodes = ref<string[]>([])
const loadingQuizzes = ref(false)
const sessionKey = ref(0)
const error = ref<string | null>(null)
const sessionStartedAt = ref<string | null>(null)
const lastSessionId = ref('')
const lastSubmittedResults = ref<Array<{ exercise: GeneratedExercise; answer: string; usedHint: boolean; viewedAnswer: boolean }>>([])
const sessionSourceType = ref<string>('exercise_page')
const sessionSourceId = ref('')
const avgDifficulty = computed(() => {
  if (!exercises.value.length) return 3
  return exercises.value.reduce((s, e) => s + (e.difficulty || 3), 0) / exercises.value.length
})

// 节点名映射
const uidLabels = computed(() => {
  const map: Record<string, string> = {}
  for (const node of searchResults.value) {
    map[node.uid] = displayNodeLabel(node.properties?.name || node.uid)
  }
  for (const t of quickTopics.value) map[t.uid] = t.label
  for (const item of searchItems.value) {
    if (item.related_node_id) map[item.related_node_id] = displayNodeLabel(item.related_node_name || item.related_node_id)
  }
  return map
})

async function searchExercisePool() {
  const q = exerciseQuery.value.trim()
  if (!q && !['recommended', 'mistake'].includes(sourceFilter.value)) return
  loadingQuizzes.value = true
  error.value = null
  try {
    if (!profileStore.profile) await profileStore.initFromAuth()
    const response = await searchExercises({
      query: q,
      student_id: profileStore.studentId,
      source_type: sourceFilter.value,
      limit: 30,
      student_profile: profileStore.studentProfileInput,
    })
    searchItems.value = response.items
    if (!response.items.length) {
      ElMessage.warning('没有找到匹配的练习题，可以换个关键词或让助手生成。')
    } else {
      ElMessage.success(`找到 ${response.items.length} 条可练习内容`)
    }
  } catch (e: any) {
    error.value = e.displayMessage || e.message || '练习搜索失败'
  } finally {
    loadingQuizzes.value = false
  }
}

function loadSearchResults() {
  if (!searchItems.value.length) return
  loadSearchItems(searchItems.value)
}

function loadSearchItem(item: ExerciseSearchItem) {
  loadSearchItems([item])
}

function loadSearchItems(items: ExerciseSearchItem[]) {
  exercises.value = items.map(searchItemToExercise)
  const first = items[0]
  selectedNodeId.value = first?.related_node_id || ''
  currentNodeName.value = displayNodeLabel(first?.related_node_name || first?.related_node_id || exerciseQuery.value, '练习')
  submitted.value = false
  correctCount.value = 0
  correctNodes.value = []
  weakNodes.value = []
  lastSubmittedResults.value = []
  sessionStartedAt.value = new Date().toISOString()
  lastSessionId.value = ''
  sessionSourceType.value = first?.source_type || 'exercise_page'
  sessionSourceId.value = first?.source_id || selectedNodeId.value
  sessionKey.value++
}

function searchItemToExercise(item: ExerciseSearchItem): GeneratedExercise {
  return {
    title: item.title || '练习题',
    type: item.type || 'choice',
    related_node_id: item.related_node_id,
    difficulty: item.difficulty || 3,
    question: item.question,
    options: item.options || [],
    answer: item.answer || {},
    adaptive_feedback: item.adaptive_feedback || {},
    source_uids: item.source_uids || [],
  }
}

async function loadQuizzes() {
  if (!selectedNodeId.value) return
  loadingQuizzes.value = true
  error.value = null
  try {
    if (!profileStore.profile) await profileStore.initFromAuth()
    await learningStore.loadEvidence(selectedNodeId.value, profileStore.studentProfileInput, profileStore.studentId)

    const evidence = learningStore.evidencePackage
    if (!evidence) { error.value = '未获取到证据包'; return }

    exercises.value = (evidence.exercises || []).map(node => ({
      title: displaySourceLabel(node.properties?.title || node.uid, '练习题'),
      type: node.properties?.type || 'choice',
      related_node_id: node.properties?.related_node_id || evidence.resolved_uid || selectedNodeId.value,
      difficulty: node.properties?.difficulty || 3,
      question: node.properties?.question || '',
      options: parseMaybeJson(node.properties?.options, []),
      answer: parseMaybeJson(node.properties?.answer, {}),
      adaptive_feedback: parseMaybeJson(node.properties?.adaptive_feedback, {}),
      source_uids: node.properties?.source_ids || []
    }))

    currentNodeName.value = displayNodeLabel(evidence.center_node?.properties?.name || selectedNodeId.value)
    submitted.value = false
    correctCount.value = 0
    correctNodes.value = []
    weakNodes.value = []
    lastSubmittedResults.value = []
    sessionStartedAt.value = new Date().toISOString()
    lastSessionId.value = ''
    sessionSourceType.value = 'exercise_page'
    sessionSourceId.value = selectedNodeId.value
    sessionKey.value++

    if (!exercises.value.length) {
      ElMessage.warning(`「${currentNodeName.value}」暂无配套练习题，请尝试其他知识点`)
    } else {
      ElMessage.success(`已加载 ${exercises.value.length} 道「${currentNodeName.value}」练习题`)
    }
  } catch (e: any) {
    error.value = e.displayMessage || e.message || '题目加载失败'
  } finally {
    loadingQuizzes.value = false
  }
}

async function loadResourceExercises(resourceId: string) {
  loadingQuizzes.value = true
  error.value = null
  try {
    if (!profileStore.profile) await profileStore.initFromAuth()
    const record = await learningStore.loadResourceRecord(resourceId)
    const fallbackNode = record.resolved_uid || learningStore.currentNodeId
    selectedNodeId.value = fallbackNode
    currentNodeName.value = displayNodeLabel(record.center_node_name || fallbackNode, '资源练习')
    exercises.value = (record.resources.exercises || []).map((exercise, index) => ({
      ...exercise,
      title: exercise.title || `资源练习题 ${index + 1}`,
      related_node_id: exercise.related_node_id || fallbackNode,
      source_uids: exercise.source_uids || [],
    }))
    submitted.value = false
    correctCount.value = 0
    correctNodes.value = []
    weakNodes.value = []
    lastSubmittedResults.value = []
    sessionStartedAt.value = new Date().toISOString()
    lastSessionId.value = ''
    sessionSourceType.value = 'resource_center'
    sessionSourceId.value = record.id
    sessionKey.value++
    if (!exercises.value.length) {
      ElMessage.warning('这条知识中心资源没有可作答的练习题')
    } else {
      ElMessage.success(`已从知识中心加载 ${exercises.value.length} 道「${currentNodeName.value}」练习题`)
    }
  } catch (e: any) {
    error.value = e.displayMessage || e.message || '知识中心题目加载失败'
  } finally {
    loadingQuizzes.value = false
  }
}

function parseMaybeJson<T>(value: any, fallback: T): T {
  if (!value) return fallback
  if (typeof value !== 'string') return value
  try { return JSON.parse(value) } catch { return fallback }
}

function submitRound(results: Array<{ exercise: GeneratedExercise; answer: string }>) {
  // 逐题判断正误
  let correct = 0
  const rightNodes: string[] = []
  const wrongNodes: string[] = []
  const nodeIds = new Set<string>()

  results.forEach(({ exercise, answer }) => {
    const ans = String(answer || '').trim()
    const expected = String(exercise.answer?.correct || '')
    nodeIds.add(exercise.related_node_id)
    if (ans && expected && ans === expected) {
      correct++
      rightNodes.push(exercise.related_node_id)
    } else {
      wrongNodes.push(exercise.related_node_id)
    }
  })

  correctCount.value = correct
  correctNodes.value = [...new Set(rightNodes)]
  weakNodes.value = [...new Set(wrongNodes)]
  submitted.value = true

  // 回写画像
  profileStore.recordExerciseRound({
    round_id: `exercise_${Date.now()}`,
    attempts: results.map(({ exercise, answer }) => {
      const ans = String(answer || '').trim()
      const expected = String(exercise.answer?.correct || '')
      return {
        exercise_id: exercise.title,
        node_ids: [exercise.related_node_id],
        is_correct: Boolean(ans && expected && ans === expected),
        difficulty: exercise.difficulty
      }
    })
  })

  const pct = Math.round((correctCount.value / Math.max(results.length, 1)) * 100)
  if (pct >= 80) {
    ElMessage.success(`🎉 正确率 ${pct}%，表现优异！画像已更新`)
  } else if (pct >= 50) {
    ElMessage.warning(`正确率 ${pct}%，建议复习薄弱知识点`)
  } else {
    ElMessage.error(`正确率 ${pct}%，需要重点复习相关知识点`)
  }
}

async function submitRoundRecorded(results: Array<{ exercise: GeneratedExercise; answer: string; usedHint: boolean; viewedAnswer: boolean }>) {
  try {
    lastSubmittedResults.value = results.map((item) => ({ ...item }))
    const roundId = `exercise_${Date.now()}`
    const submittedAt = Date.now()
    const startedAt = sessionStartedAt.value ? new Date(sessionStartedAt.value).getTime() : submittedAt
    const durationSeconds = Math.max(0, Math.round((submittedAt - startedAt) / 1000))
    const response = await profileStore.recordExerciseSession({
      round_id: roundId,
      source_type: sessionSourceType.value,
      source_id: sessionSourceId.value || selectedNodeId.value,
      target_node_id: selectedNodeId.value,
      target_node_name: currentNodeName.value,
      title: `${currentNodeName.value || '知识点'}练习`,
      mode: exerciseMode.value,
      duration_seconds: durationSeconds,
      started_at: sessionStartedAt.value,
      attempts: results.map(({ exercise, answer }, index) => {
        const ans = String(answer || '').trim()
        const expected = String(exercise.answer?.correct || '')
        const frontendCanGrade = exercise.type === 'choice'
        const isCorrect = frontendCanGrade ? Boolean(ans && expected && ans === expected) : null
        return {
          exercise_id: exercise.title || `exercise_${index + 1}`,
          exercise_title: exercise.title,
          exercise_type: exercise.type,
          related_node_id: exercise.related_node_id,
          related_node_name: displayNodeLabel(uidLabels.value[exercise.related_node_id] || exercise.related_node_id),
          exercise_snapshot: { ...exercise, index: index + 1 },
          student_answer: { value: ans },
          expected_answer: exercise.answer || {},
          is_correct: isCorrect,
          score: isCorrect === null ? null : (isCorrect ? 1 : 0),
          difficulty: exercise.difficulty,
          cognitive_level: 'understand',
          used_hint: Boolean(results[index].usedHint),
          time_spent_seconds: 0,
          feedback: {
            explanation: exercise.answer?.explanation || '',
            adaptive_feedback: exercise.adaptive_feedback || {},
          },
          misconception_tags: [],
          source_uids: exercise.source_uids || [],
          mode: exerciseMode.value,
          viewed_answer: Boolean(results[index].viewedAnswer),
          grading_method: frontendCanGrade ? 'rule' : null,
        }
      })
    })
    lastSessionId.value = response.session.id
    correctCount.value = response.session.correct_count
    correctNodes.value = response.session.attempts.filter(a => a.is_correct).map(a => a.related_node_id)
    weakNodes.value = response.session.weak_nodes
    response.session.attempts.forEach((attempt, index) => {
      const exercise = exercises.value[index]
      if (!exercise) return
      exercise.answer = {
        ...(exercise.answer || {}),
        __is_correct: attempt.is_correct,
        __score: attempt.score,
        __grading_method: attempt.grading_method,
        __grading_status: attempt.grading_status,
        __grading_confidence: attempt.grading_confidence,
        __profile_update_allowed: attempt.profile_update_allowed,
        __grading: attempt.feedback?.grading || null,
        explanation: attempt.feedback?.explanation || attempt.feedback?.feedback || exercise.answer?.explanation || '',
      }
      exercise.adaptive_feedback = {
        ...(exercise.adaptive_feedback || {}),
        default: attempt.feedback?.feedback || attempt.feedback?.explanation || exercise.adaptive_feedback?.default,
      }
    })
    submitted.value = true
  } catch (e: any) {
    ElMessage.error(e.displayMessage || e.message || '练习记录保存失败')
    return
  }

  const pct = Math.round((correctCount.value / Math.max(results.length, 1)) * 100)
  if (pct >= 80) {
    ElMessage.success(`正确率 ${pct}%，表现很好，练习记录已保存。`)
  } else if (pct >= 50) {
    ElMessage.warning(`正确率 ${pct}%，练习记录已保存，建议复习薄弱知识点。`)
  } else {
    ElMessage.error(`正确率 ${pct}%，练习记录已保存，需要重点复习相关知识点。`)
  }
}

function typeLabel(type: string) {
  const labels: Record<string, string> = {
    choice: '选择题',
    short_answer: '简答题',
    coding: '编程题',
    case_analysis: '案例分析',
  }
  return labels[type] || displaySourceLabel(type, '题型')
}

function sourceTagType(source: string) {
  const tags: Record<string, string> = {
    knowledge_base: 'primary',
    ai_generated: 'success',
    mistake: 'warning',
    recommended: 'danger',
  }
  return tags[source] || 'info'
}

function reviewTypeLabel(type: string) {
  const labels: Record<string, string> = {
    mistake_retry: '错题复做',
    weak_point_review: '薄弱点',
    forgetting_review: '遗忘预警',
    prereq_repair: '前置补缺',
    query_review: '主题复习',
  }
  return labels[type] || '推荐'
}

function resetSession() {
  exercises.value = []
  submitted.value = false
  correctCount.value = 0
  correctNodes.value = []
  weakNodes.value = []
  lastSubmittedResults.value = []
  sessionKey.value++
}

function goToGraph(nodeIds: string[]) {
  const uid = nodeIds[0] || selectedNodeId.value
  router.push({ path: '/graph', query: { node_id: uid } })
}

function goToHistory() {
  router.push({
    path: '/exercise-history',
    query: lastSessionId.value ? { session_id: lastSessionId.value } : undefined,
  })
}

const scoreClass = computed(() => {
  if (exercises.value.length === 0) return ''
  const rate = correctCount.value / exercises.value.length
  if (rate >= 0.8) return 'good'
  if (rate >= 0.5) return 'ok'
  return 'bad'
})

const scoreText = computed(() => {
  if (exercises.value.length === 0) return ''
  const rate = correctCount.value / exercises.value.length
  if (rate >= 0.8) return '掌握得不错！继续保持'
  if (rate >= 0.5) return '还有提升空间，建议复习薄弱知识点'
  return '需要重点复习，建议查看学习资料并请教助手'
})

const scoreIcon = computed(() => {
  if (exercises.value.length === 0) return ''
  const rate = correctCount.value / exercises.value.length
  if (rate >= 0.8) return '🎉'
  if (rate >= 0.5) return '💪'
  return '📚'
})

const starRating = computed(() => {
  if (exercises.value.length === 0) return 0
  const rate = correctCount.value / exercises.value.length
  if (rate >= 0.95) return 5
  if (rate >= 0.8) return 4
  if (rate >= 0.6) return 3
  if (rate >= 0.4) return 2
  return 1
})

const scorePercent = computed(() => {
  if (exercises.value.length === 0) return 0
  return Math.round((correctCount.value / exercises.value.length) * 100)
})

const animatedCorrect = ref(0)

watch(correctCount, (newVal) => {
  const start = animatedCorrect.value
  const startTime = performance.now()
  function update(currentTime: number) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / 800, 1)
    const easeOut = 1 - Math.pow(1 - progress, 3)
    animatedCorrect.value = Math.round(start + (newVal - start) * easeOut)
    if (progress < 1) {
      requestAnimationFrame(update)
    }
  }
  requestAnimationFrame(update)
})

function goAskAssistant(target: string | GeneratedExercise) {
  sessionStorage.setItem('assistant_prefill', buildAssistantExercisePrompt(target))
  router.push({ path: '/assistant' })
}

function buildAssistantExercisePrompt(target: string | GeneratedExercise) {
  if (typeof target !== 'string') {
    return buildSingleExercisePrompt(target)
  }
  const wrongResults = lastSubmittedResults.value.filter(({ exercise }) => exercise.answer?.__is_correct === false)
  const weakText = weakNodes.value.length
    ? weakNodes.value.map((uid) => displayNodeLabel(uidLabels.value[uid] || uid)).join('、')
    : '暂无明确薄弱知识点'
  const wrongPreview = wrongResults.slice(0, 3).map(({ exercise, answer }, index) => {
    const correct = exercise.answer?.correct || exercise.answer?.reference_answer || ''
    return [
      `错题${index + 1}：${localizeText(exercise.title || '')}`,
      `知识点：${displayNodeLabel(exercise.related_node_id || selectedNodeId.value)}`,
      `题干：${localizeText(exercise.question || '')}`,
      `我的答案：${answer || '未作答'}`,
      `参考答案：${formatCompactAnswer(correct)}`,
    ].join('\n')
  }).join('\n\n')
  return [
    '请学习助手分析我刚刚这一轮练习。',
    '',
    '【练习求助上下文】',
    `练习主题：${currentNodeName.value || '当前练习'}`,
    `知识点：${displayNodeLabel(selectedNodeId.value || weakNodes.value[0] || '')}`,
    `练习模式：${exerciseMode.value}`,
    `得分：${correctCount.value}/${exercises.value.length}`,
    `薄弱知识点：${weakText}`,
    wrongPreview ? `\n${wrongPreview}` : '本轮没有明确错题，请帮我总结可以继续巩固的方向。',
    '',
    '请你按“错因 -> 对应知识点 -> 复习建议 -> 下一步练习”的结构给我反馈，不要重新出题。'
  ].join('\n')
}

function buildSingleExercisePrompt(exercise: GeneratedExercise) {
  const submitted = lastSubmittedResults.value.find(({ exercise: item }) =>
    item === exercise || (item.title === exercise.title && item.question === exercise.question)
  )
  const options = (exercise.options || [])
    .map((option) => `${option.label}. ${localizeText(option.text || '')}`)
    .join('\n')
  const correct = exercise.answer?.correct || exercise.answer?.reference_answer || ''
  const explanation = exercise.answer?.explanation || exercise.adaptive_feedback?.default || ''
  const verdict = typeof exercise.answer?.__is_correct === 'boolean'
    ? (exercise.answer.__is_correct ? '正确' : '错误')
    : '未判定'
  return [
    '请学习助手讲解这道题，重点分析我的作答。',
    '',
    '【练习求助上下文】',
    `练习主题：${currentNodeName.value || '当前练习'}`,
    `知识点：${displayNodeLabel(exercise.related_node_id || selectedNodeId.value)}`,
    `题目标题：${localizeText(exercise.title || '')}`,
    `题型：${typeLabel(exercise.type || '')}`,
    `难度：${exercise.difficulty || 3}`,
    `题干：${localizeText(exercise.question || '')}`,
    options ? `选项：\n${options}` : '',
    `学生作答：${submitted?.answer || '未记录'}`,
    `参考答案：${formatCompactAnswer(correct)}`,
    `判定：${verdict}`,
    explanation ? `现有解析：${localizeText(explanation)}` : '',
    '',
    '请你说明：我为什么会错或哪里还可以加强；这题考查哪个核心概念；下一次遇到同类题应该怎么判断。'
  ].filter(Boolean).join('\n')
}

function formatCompactAnswer(value: any) {
  if (value === undefined || value === null || value === '') return '暂无'
  if (typeof value === 'string') return localizeText(value)
  return JSON.stringify(value)
}

// 页面初始化：从 URL 参数预填知识点
onMounted(async () => {
  const queryResourceId = route.query?.resource_id
  if (queryResourceId && typeof queryResourceId === 'string') {
    await loadResourceExercises(queryResourceId)
    return
  }

  const queryNode = route.query?.node_id
  if (queryNode && typeof queryNode === 'string') {
    const q = queryNode.trim()
    // 过滤非知识点 ID（如练习题 ID `ex_ch03_gd_003`）
    if (q.startsWith('ex_') || q.startsWith('faq_') || q.startsWith('code_')) {
      // 不是知识点 ID，尝试搜索匹配的知识点
      try {
        const results = await searchGraphNodes(q.replace(/^ex_|^faq_|^code_/, '').replace(/_/g, ' '), 5)
        const kp = results.find(n => n.labels?.includes('KnowledgePoint'))
        if (kp) {
          selectedNodeId.value = kp.uid
          currentNodeName.value = displayNodeLabel(kp.properties?.name || kp.uid)
          loadQuizzes()
          return
        }
      } catch {}
      // 无法解析，忽略
      return
    }
    selectedNodeId.value = q
    exerciseQuery.value = displayNodeLabel(q)
    // 尝试获取显示名
    try {
      const results = await searchGraphNodes(q, 1)
      if (results.length > 0) {
        currentNodeName.value = displayNodeLabel(results[0].properties?.name || q)
      }
    } catch {}
    loadQuizzes()
  }
})
</script>

<style scoped>
.selector-card {
  margin-bottom: 16px;
}

.selector-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.unified-selector {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) auto 150px auto;
  align-items: center;
  gap: 12px;
}

.mode-select {
  width: 150px;
}

.mode-hint {
  margin-top: 10px;
  color: #64748b;
  font-size: 13px;
}

.exercise-search-results {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.exercise-search-item {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  padding: 12px 14px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  text-align: left;
  cursor: pointer;
}

.exercise-search-item:hover {
  border-color: #6366f1;
  background: #f8fafc;
}

.search-item-main {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.search-item-main span {
  color: #64748b;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.review-reasons {
  grid-column: 1 / -1;
  display: grid;
  gap: 4px;
  margin-top: 2px;
  color: #92400e;
  font-size: 12px;
  line-height: 1.5;
}

.review-reasons span {
  padding-left: 10px;
  border-left: 2px solid #f59e0b;
}

.selector-main {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 280px;
}

.selector-label {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}

.selector-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.search-option {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.option-name { flex: 1; }

.quick-topics {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.quick-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.quick-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(79, 70, 229, 0.2);
}

.session-bar {
  margin-bottom: 16px;
  padding: 12px 20px;
  background: #f8fafc;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.session-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.exercise-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
  align-items: start;
}

@media (max-width: 900px) {
  .exercise-layout { grid-template-columns: 1fr; }
}

.exercise-main {
  min-width: 0;
}

/* 提交后操作区 */
.result-actions {
  margin-top: 20px;
}

.result-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 24px;
  border-radius: 16px;
  margin-bottom: 20px;
  animation: resultIn 0.5s ease-out;
}

@keyframes resultIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.result-card.good {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.result-card.ok {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.result-card.bad {
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.result-icon {
  font-size: 56px;
  animation: bounce 1s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.result-main {
  flex: 1;
}

.result-score {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.score-number {
  font-size: 48px;
  font-weight: 700;
}

.score-divider {
  font-size: 32px;
  opacity: 0.5;
}

.score-percent {
  font-size: 24px;
  font-weight: 600;
  opacity: 0.8;
}

.result-card.good .score-number,
.result-card.good .score-percent {
  color: #16a34a;
}

.result-card.ok .score-number,
.result-card.ok .score-percent {
  color: #d97706;
}

.result-card.bad .score-number,
.result-card.bad .score-percent {
  color: #dc2626;
}

.result-text {
  font-size: 15px;
  color: #475569;
  margin-top: 4px;
}

.result-stars {
  margin-left: auto;
}

.result-buttons {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.result-weak {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #fffbeb;
  border-radius: 10px;
  border: 1px solid rgba(245, 158, 11, 0.2);
  flex-wrap: wrap;
}

.weak-label {
  font-size: 13px;
  color: #92400e;
  font-weight: 500;
}

.weak-tag {
  cursor: pointer;
  transition: all 0.2s ease;
}

.weak-tag:hover {
  transform: translateY(-1px);
}
</style>
