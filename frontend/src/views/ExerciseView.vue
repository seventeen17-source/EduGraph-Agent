<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>练习与评估</h1>
        <div class="muted">选择知识点，加载练习题目，提交后回写学生画像并获取诊断建议</div>
      </div>
    </div>

    <ErrorAlert :message="error" />

    <!-- 知识点选择器 -->
    <el-card class="section-card selector-card" shadow="never">
      <div class="selector-row">
        <div class="selector-main">
          <span class="selector-label">选择知识点：</span>
          <el-select
            v-model="selectedNodeId"
            filterable
            remote
            :remote-method="searchNodes"
            :loading="searchingNodes"
            placeholder="输入知识点名称搜索，如 K-Means、反向传播"
            style="flex: 1; min-width: 300px"
            clearable
            @change="onNodeSelected"
          >
            <el-option
              v-for="node in searchResults"
              :key="node.uid"
              :label="`${node.properties?.name || node.uid} (ch${node.properties?.chapter_id?.slice(2) || '?'})`"
              :value="node.uid"
            >
              <div class="search-option">
                <span class="option-name">{{ node.properties?.name || node.uid }}</span>
                <el-tag size="small" effect="plain">{{ node.properties?.chapter_id || '' }}</el-tag>
                <el-rate
                  :model-value="node.properties?.difficulty || 3"
                  disabled
                  size="small"
                  show-score
                />
              </div>
            </el-option>
          </el-select>
        </div>
        <div class="selector-actions">
          <el-button
            type="primary"
            :loading="loadingQuizzes"
            :disabled="!selectedNodeId"
            @click="loadQuizzes"
          >
            <el-icon><Search /></el-icon> 加载题目
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
      <!-- 快捷知识点 -->
      <div v-if="!selectedNodeId && !exercises.length" class="quick-topics">
        <span class="muted">常用知识点：</span>
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
        <el-tag type="primary">{{ currentNodeName }}</el-tag>
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
          <div class="result-summary">
            <span class="result-score" :class="scoreClass">{{ correctCount }}/{{ exercises.length }}</span>
            <span class="result-text">{{ scoreText }}</span>
          </div>
          <div class="result-buttons">
            <el-button type="primary" @click="resetSession"><el-icon><RefreshLeft /></el-icon> 再做一遍</el-button>
            <el-button @click="goToHistory"><el-icon><Document /></el-icon> 查看练习记录</el-button>
            <el-button @click="goToGraph(weakNodes)"><el-icon><Share /></el-icon> 薄弱知识点</el-button>
            <el-button @click="goAskAssistant('')"><el-icon><ChatDotRound /></el-icon> 请助手分析</el-button>
          </div>
          <div v-if="weakNodes.length" class="result-weak">
            <span class="muted">需要加强：</span>
            <el-tag v-for="nid in weakNodes" :key="nid" type="warning" size="small" effect="plain" style="margin-left: 6px; cursor: pointer" @click="goToGraph([nid])">
              {{ uidLabels[nid] || nid }}
            </el-tag>
          </div>
        </div>
      </div>

      <EvidencePanel v-if="learningStore.evidencePackage" :evidence="learningStore.evidencePackage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Document, RefreshLeft, Search, Share } from '@element-plus/icons-vue'

import EvidencePanel from '@/components/graphrag/EvidencePanel.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import ExerciseCard from '@/components/resources/ExerciseCard.vue'
import { searchGraphNodes } from '@/api/graph'
import { useLearningStore } from '@/stores/learning'
import { useProfileStore } from '@/stores/profile'
import type { GeneratedExercise } from '@/types/resources'
import type { GraphNode } from '@/types/graph'
import { uidLabel } from '@/utils/format'

const router = useRouter()
const learningStore = useLearningStore()
const profileStore = useProfileStore()

// 知识点选择
const selectedNodeId = ref('')
const currentNodeName = ref('')
const searchResults = ref<GraphNode[]>([])
const searchingNodes = ref(false)
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

const quickTopics = [
  { uid: 'ml_backpropagation', label: '反向传播' },
  { uid: 'ml_gradient_descent', label: '梯度下降' },
  { uid: 'ml_kmeans', label: 'K-Means' },
  { uid: 'ml_logistic_regression', label: '逻辑回归' },
  { uid: 'ml_cnn', label: '卷积神经网络' },
  { uid: 'ml_decision_tree', label: '决策树' },
  { uid: 'ml_svm', label: '支持向量机' },
  { uid: 'ml_overfitting_underfitting', label: '过拟合与欠拟合' },
]

function quickSelect(uid: string) {
  selectedNodeId.value = uid
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
const avgDifficulty = computed(() => {
  if (!exercises.value.length) return 3
  return exercises.value.reduce((s, e) => s + (e.difficulty || 3), 0) / exercises.value.length
})

// 节点名映射
const uidLabels = computed(() => {
  const map: Record<string, string> = {}
  for (const node of searchResults.value) {
    map[node.uid] = node.properties?.name || uidLabel(node.uid)
  }
  for (const t of quickTopics) map[t.uid] = t.label
  return map
})

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
      title: node.properties?.title || uidLabel(node.uid) || '练习题',
      type: node.properties?.type || 'choice',
      related_node_id: node.properties?.related_node_id || evidence.resolved_uid || selectedNodeId.value,
      difficulty: node.properties?.difficulty || 3,
      question: node.properties?.question || '',
      options: parseMaybeJson(node.properties?.options, []),
      answer: parseMaybeJson(node.properties?.answer, {}),
      adaptive_feedback: parseMaybeJson(node.properties?.adaptive_feedback, {}),
      source_uids: node.properties?.source_ids || []
    }))

    currentNodeName.value = evidence.center_node?.properties?.name || uidLabel(selectedNodeId.value) || selectedNodeId.value
    submitted.value = false
    correctCount.value = 0
    correctNodes.value = []
    weakNodes.value = []
    sessionStartedAt.value = new Date().toISOString()
    lastSessionId.value = ''
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

  const pct = Math.round(correct / results.length * 100)
  if (pct >= 80) {
    ElMessage.success(`🎉 正确率 ${pct}%，表现优异！画像已更新`)
  } else if (pct >= 50) {
    ElMessage.warning(`正确率 ${pct}%，建议复习薄弱知识点`)
  } else {
    ElMessage.error(`正确率 ${pct}%，需要重点复习相关知识点`)
  }
}

async function submitRoundRecorded(results: Array<{ exercise: GeneratedExercise; answer: string }>) {
  let correct = 0
  const rightNodes: string[] = []
  const wrongNodes: string[] = []

  results.forEach(({ exercise, answer }) => {
    const ans = String(answer || '').trim()
    const expected = String(exercise.answer?.correct || '')
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

  try {
    const roundId = `exercise_${Date.now()}`
    const submittedAt = Date.now()
    const startedAt = sessionStartedAt.value ? new Date(sessionStartedAt.value).getTime() : submittedAt
    const durationSeconds = Math.max(0, Math.round((submittedAt - startedAt) / 1000))
    const response = await profileStore.recordExerciseSession({
      round_id: roundId,
      source_type: 'exercise_page',
      source_id: selectedNodeId.value,
      target_node_id: selectedNodeId.value,
      target_node_name: currentNodeName.value,
      title: `${currentNodeName.value || '知识点'}练习`,
      duration_seconds: durationSeconds,
      started_at: sessionStartedAt.value,
      attempts: results.map(({ exercise, answer }, index) => {
        const ans = String(answer || '').trim()
        const expected = String(exercise.answer?.correct || '')
        const isCorrect = Boolean(ans && expected && ans === expected)
        return {
          exercise_id: exercise.title || `exercise_${index + 1}`,
          exercise_title: exercise.title,
          exercise_type: exercise.type,
          related_node_id: exercise.related_node_id,
          related_node_name: uidLabels.value[exercise.related_node_id] || exercise.related_node_id,
          exercise_snapshot: { ...exercise, index: index + 1 },
          student_answer: { value: ans },
          expected_answer: exercise.answer || {},
          is_correct: isCorrect,
          score: isCorrect ? 1 : 0,
          difficulty: exercise.difficulty,
          cognitive_level: 'understand',
          used_hint: false,
          time_spent_seconds: 0,
          feedback: {
            explanation: exercise.answer?.explanation || '',
            adaptive_feedback: exercise.adaptive_feedback || {},
          },
          misconception_tags: [],
          source_uids: exercise.source_uids || [],
        }
      })
    })
    lastSessionId.value = response.session.id
  } catch (e: any) {
    ElMessage.error(e.displayMessage || e.message || '练习记录保存失败')
    return
  }

  const pct = Math.round(correct / results.length * 100)
  if (pct >= 80) {
    ElMessage.success(`正确率 ${pct}%，表现很好，练习记录已保存。`)
  } else if (pct >= 50) {
    ElMessage.warning(`正确率 ${pct}%，练习记录已保存，建议复习薄弱知识点。`)
  } else {
    ElMessage.error(`正确率 ${pct}%，练习记录已保存，需要重点复习相关知识点。`)
  }
}

function resetSession() {
  exercises.value = []
  submitted.value = false
  correctCount.value = 0
  correctNodes.value = []
  weakNodes.value = []
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

function goAskAssistant(_target: string | GeneratedExercise) {
  router.push({ path: '/assistant' })
  sessionStorage.setItem('assistant_prefill',
    `我刚刚做了「${currentNodeName.value}」的练习题（${correctCount.value}/${exercises.value.length}正确），请帮我分析错题原因`)
}

// 页面初始化：从 URL 参数预填知识点
onMounted(async () => {
  const queryNode = router.currentRoute.value.query?.node_id
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
          currentNodeName.value = kp.properties?.name || kp.uid
          loadQuizzes()
          return
        }
      } catch {}
      // 无法解析，忽略
      return
    }
    selectedNodeId.value = q
    // 尝试获取显示名
    try {
      const results = await searchGraphNodes(q, 1)
      if (results.length > 0) {
        currentNodeName.value = results[0].properties?.name || q
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
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.result-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.result-score {
  font-size: 36px;
  font-weight: 700;
  padding: 8px 16px;
  border-radius: 12px;
}

.result-score.good { background: #f0fdf4; color: #16a34a; }
.result-score.ok  { background: #fef3c7; color: #d97706; }
.result-score.bad { background: #fef2f2; color: #dc2626; }

.result-text {
  font-size: 15px;
  color: #475569;
}

.result-buttons {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.result-weak {
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 13px;
}
</style>
