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

    <el-tabs v-model="activeTab" class="history-tabs">
      <el-tab-pane label="练习历史" name="sessions">
        <el-empty v-if="!loading && sessions.length === 0" description="暂无练习记录" />
        <div v-else class="session-list">
          <el-card v-for="item in sessions" :key="item.id" class="session-card" shadow="never">
            <div class="session-row">
              <div>
                <div class="session-title">{{ item.title || item.target_node_name || uidLabel(item.target_node_id) || '练习记录' }}</div>
                <div class="muted small">
                  {{ formatTime(item.submitted_at) }} · {{ sourceLabel(item.source_type) }} · 用时 {{ formatDuration(item.duration_seconds) }}
                </div>
                <div v-if="item.weak_nodes.length" class="tag-row">
                  <el-tag v-for="node in item.weak_nodes" :key="node" type="warning" size="small">
                    {{ uidLabel(node) || node }}
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
        <el-empty v-if="!loading && mistakes.length === 0" description="暂无错题" />
        <div v-else class="mistake-list">
          <el-card v-for="item in mistakes" :key="item.id" class="mistake-card" shadow="never">
            <div class="mistake-head">
              <strong>{{ item.exercise_title || item.exercise_id }}</strong>
              <el-tag type="warning" size="small">{{ item.related_node_name || uidLabel(item.related_node_id) || item.related_node_id }}</el-tag>
            </div>
            <div class="question-text">{{ item.exercise_snapshot.question || '题目内容未记录' }}</div>
            <div class="answer-grid">
              <div><span class="muted">你的答案：</span>{{ item.student_answer.value || '未作答' }}</div>
              <div><span class="muted">正确答案：</span>{{ item.expected_answer.correct || item.expected_answer.reference_answer || '见解析' }}</div>
            </div>
            <div v-if="item.feedback.explanation" class="feedback-text">{{ item.feedback.explanation }}</div>
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
        <div v-for="attempt in selectedSession.attempts" :key="attempt.id" class="attempt-detail" :class="{ wrong: !attempt.is_correct }">
          <div class="attempt-title">
            <el-tag :type="attempt.is_correct ? 'success' : 'danger'" size="small">
              {{ attempt.is_correct ? '正确' : '错题' }}
            </el-tag>
            <strong>{{ attempt.exercise_title || attempt.exercise_id }}</strong>
          </div>
          <div class="question-text">{{ attempt.exercise_snapshot.question || '' }}</div>
          <div class="answer-grid">
            <div><span class="muted">你的答案：</span>{{ attempt.student_answer.value || '未作答' }}</div>
            <div><span class="muted">正确答案：</span>{{ attempt.expected_answer.correct || attempt.expected_answer.reference_answer || '见解析' }}</div>
          </div>
          <div v-if="attempt.feedback.explanation" class="feedback-text">{{ attempt.feedback.explanation }}</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getExerciseSession, getExerciseStats, listExerciseMistakes, listExerciseSessions } from '@/api/exercises'
import { useAuthStore } from '@/stores/auth'
import type { ExerciseAttemptRecord, ExerciseSessionRecord, ExerciseStatsResponse } from '@/types/exercises'
import { uidLabel } from '@/utils/format'

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
  return labels[source] || source
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

.mistake-head,
.attempt-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
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
}
</style>
