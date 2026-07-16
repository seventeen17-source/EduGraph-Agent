<template>
  <div class="page">
    <div class="page-title">
      <div class="page-title-left">
        <div class="page-title-icon">📈</div>
        <div class="page-title-info">
          <h1>学习成长</h1>
          <div class="muted">回顾学习历程，了解自己的节奏，发现下一步方向。</div>
        </div>
      </div>
    </div>

    <!-- ===== 周报/月报区域 ===== -->
    <el-card class="report-card" shadow="never">
      <template #header>
        <div class="report-header">
          <div class="report-title">
            <span class="report-icon">📋</span>
            <span>学习{{ reportPeriodLabel }}</span>
            <el-tag v-if="report" size="small" type="info" effect="plain">
              {{ report.period_label }}
            </el-tag>
          </div>
          <el-radio-group v-model="reportDays" size="small" @change="loadReport">
            <el-radio-button :value="7">周报</el-radio-button>
            <el-radio-button :value="30">月报</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <div v-if="reportLoading" class="loading-placeholder">
        <LoadingSkeleton :rows="4" />
      </div>
      <ErrorAlert v-else-if="reportError" :message="reportError" :retry="loadReport" />
      <template v-else-if="report">
        <!-- 总结 -->
        <div class="report-summary">{{ localizeText(report.summary) }}</div>

        <!-- 统计卡片 -->
        <div class="report-stats-grid">
          <div class="report-stat-card">
            <div class="report-stat-value">{{ report.exercise_stats.total_attempts }}</div>
            <div class="report-stat-label">练习题数</div>
          </div>
          <div class="report-stat-card">
            <div class="report-stat-value">{{ Math.round(report.exercise_stats.accuracy * 100) }}%</div>
            <div class="report-stat-label">正确率</div>
          </div>
          <div class="report-stat-card">
            <div class="report-stat-value">{{ report.exercise_stats.active_days }}</div>
            <div class="report-stat-label">活跃天数</div>
          </div>
          <div class="report-stat-card">
            <div class="report-stat-value">{{ report.exercise_stats.practiced_nodes }}</div>
            <div class="report-stat-label">覆盖知识点</div>
          </div>
          <div class="report-stat-card mastered">
            <div class="report-stat-value">{{ report.mastery_changes.total_mastered }}</div>
            <div class="report-stat-label">已掌握</div>
          </div>
          <div class="report-stat-card strong">
            <div class="report-stat-value">{{ report.mastery_changes.total_strong }}</div>
            <div class="report-stat-label">熟练掌握</div>
          </div>
        </div>

        <!-- 掌握度变化 -->
        <div v-if="report.mastery_changes.new_mastered.length || report.mastery_changes.needs_attention.length" class="report-section">
          <div class="report-section-title">📊 掌握度变化</div>
          <div class="mastery-change-grid">
            <div v-if="report.mastery_changes.new_mastered.length" class="mastery-change-col">
              <div class="mastery-change-head positive">✅ 新增掌握</div>
              <div class="mastery-change-list">
                <div
                  v-for="item in report.mastery_changes.new_mastered"
                  :key="item.node_id"
                  class="mastery-change-item positive"
                  @click="goToNode(item.node_id)"
                >
                  <span class="mastery-name">{{ displayNodeLabel(item.node_name || item.node_id) }}</span>
                  <span class="mastery-score">{{ Math.round(item.mastery_score * 100) }}%</span>
                </div>
              </div>
            </div>
            <div v-if="report.mastery_changes.needs_attention.length" class="mastery-change-col">
              <div class="mastery-change-head warning">⚠️ 需要关注</div>
              <div class="mastery-change-list">
                <div
                  v-for="item in report.mastery_changes.needs_attention"
                  :key="item.node_id"
                  class="mastery-change-item warning"
                  @click="goToNode(item.node_id)"
                >
                  <span class="mastery-name">{{ displayNodeLabel(item.node_name || item.node_id) }}</span>
                  <span class="mastery-score">{{ Math.round(item.mastery_score * 100) }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 遗忘预警 -->
        <div v-if="report.forgetting_warnings.length" class="report-section">
          <div class="report-section-title">🔁 遗忘预警</div>
          <div class="forgetting-list">
            <div
              v-for="node in report.forgetting_warnings"
              :key="node.node_id"
              class="forgetting-item"
              :class="node.urgency"
              @click="goToExercise(node.node_id)"
            >
              <div class="forgetting-info">
                <span class="forgetting-name">{{ displayNodeLabel(node.node_name || node.node_id) }}</span>
                <span class="forgetting-desc">
                  已 {{ node.days_since_review }} 天未复习 · 估算遗忘率 {{ Math.round(node.estimated_forgetting_rate * 100) }}%
                </span>
              </div>
              <el-tag size="small" :type="forgettingTagType(node.urgency)" effect="plain">
                {{ forgettingLabel(node.urgency) }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 推荐下一步 -->
        <div v-if="report.recommendations.length" class="report-section">
          <div class="report-section-title">🎯 推荐下一步</div>
          <div class="recommendation-list">
            <div
              v-for="rec in report.recommendations"
              :key="rec.node_id"
              class="recommendation-item"
              @click="goToNode(rec.node_id)"
            >
              <div class="rec-icon" :class="rec.urgency">{{ recommendationIcon(rec.urgency) }}</div>
              <div class="rec-content">
                <div class="rec-head">
                  <strong>{{ displayNodeLabel(rec.node_name || rec.node_id) }}</strong>
                  <el-tag size="small" :type="urgencyTagType(rec.urgency)" effect="plain">
                    {{ urgencyLabel(rec.urgency) }}
                  </el-tag>
                </div>
                <p class="rec-reason">{{ localizeText(rec.reason) }}</p>
              </div>
              <div class="rec-arrow">→</div>
            </div>
          </div>
        </div>
      </template>
      <el-empty v-else description="暂无报告数据" />
    </el-card>

    <!-- ===== 成长时间轴 ===== -->
    <div v-if="loading" class="loading-placeholder">
      <LoadingSkeleton :rows="6" />
    </div>

    <ErrorAlert v-else-if="error" :message="error" :retry="load" />

    <LearningTimeline
      v-else-if="data"
      :months="data.months"
      :stats="data.stats"
      :forgetting-soon="data.forgetting_soon"
      @go-to-node="goToNode"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import ErrorAlert from '@/components/common/ErrorAlert.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import LearningTimeline from '@/components/profile/LearningTimeline.vue'
import { getLearningReport, getLearningTimeline } from '@/api/profile'
import { useAuthStore } from '@/stores/auth'
import { useProfileStore } from '@/stores/profile'
import type { TimelineResponse, WeeklyReportResponse } from '@/types/profile'
import { displayNodeLabel, localizeText } from '@/utils/format'

const router = useRouter()
const authStore = useAuthStore()
const profileStore = useProfileStore()
const data = ref<TimelineResponse | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// 周报/月报
const report = ref<WeeklyReportResponse | null>(null)
const reportLoading = ref(false)
const reportError = ref<string | null>(null)
const reportDays = ref<number>(7)
const reportPeriodLabel = computed(() => (reportDays.value <= 7 ? '周报' : '月报'))

async function ensureStudentId(): Promise<string | null> {
  const sid = authStore.studentId || profileStore.studentId
  if (!sid) {
    error.value = '未登录'
    return null
  }
  if (!profileStore.profile && authStore.studentId) {
    profileStore.studentId = authStore.studentId
    profileStore.displayName = authStore.displayName
    await profileStore.loadCurrentStudent().catch(() => {})
  }
  return sid
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const sid = await ensureStudentId()
    if (!sid) return
    data.value = await getLearningTimeline(sid)
  } catch (err: any) {
    error.value = err?.message || '加载时间轴失败'
  } finally {
    loading.value = false
  }
}

async function loadReport() {
  reportLoading.value = true
  reportError.value = null
  try {
    const sid = await ensureStudentId()
    if (!sid) return
    report.value = await getLearningReport(sid, reportDays.value)
  } catch (err: any) {
    reportError.value = err?.message || '加载报告失败'
  } finally {
    reportLoading.value = false
  }
}

function goToNode(nodeId: string | null) {
  if (!nodeId) return
  router.push({ path: '/graph', query: { node_id: nodeId } })
}

function goToExercise(nodeId: string | null) {
  if (!nodeId) return
  router.push({ path: '/exercise', query: { node_id: nodeId } })
}

function forgettingLabel(urgency: string): string {
  const labels: Record<string, string> = { high: '紧急', medium: '中等', low: '轻微' }
  return labels[urgency] || urgency
}

function forgettingTagType(urgency: string): 'danger' | 'warning' | 'info' {
  if (urgency === 'high') return 'danger'
  if (urgency === 'medium') return 'warning'
  return 'info'
}

function urgencyLabel(urgency: string): string {
  const labels: Record<string, string> = { high: '高优先', medium: '中优先', low: '低优先' }
  return labels[urgency] || urgency
}

function urgencyTagType(urgency: string): 'danger' | 'warning' | 'info' {
  if (urgency === 'high') return 'danger'
  if (urgency === 'medium') return 'warning'
  return 'info'
}

function recommendationIcon(urgency: string): string {
  if (urgency === 'high') return '🔥'
  if (urgency === 'medium') return '⭐'
  return '📌'
}

onMounted(() => {
  load()
  loadReport()
})
</script>

<style scoped>
/* ===== 周报卡片 ===== */
.report-card {
  margin-bottom: 20px;
  border: 1px solid #e2e8f0;
}

.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.report-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}

.report-icon {
  font-size: 20px;
}

.report-summary {
  padding: 12px 16px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #f0fdf4 100%);
  border-radius: 8px;
  color: #1e293b;
  font-size: 14px;
  line-height: 1.7;
  border-left: 4px solid #3b82f6;
}

.report-stats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.report-stat-card {
  background: #f8fafc;
  border-radius: 8px;
  padding: 16px 8px;
  text-align: center;
  border: 1px solid #f1f5f9;
}

.report-stat-card.mastered {
  background: #ecfdf5;
  border-color: #d1fae5;
}

.report-stat-card.strong {
  background: #eff6ff;
  border-color: #dbeafe;
}

.report-stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #4f46e5;
  line-height: 1.2;
}

.report-stat-card.mastered .report-stat-value {
  color: #10b981;
}

.report-stat-card.strong .report-stat-value {
  color: #3b82f6;
}

.report-stat-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.report-section {
  margin-bottom: 20px;
}

.report-section:last-child {
  margin-bottom: 0;
}

.report-section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f1f5f9;
}

/* 掌握度变化 */
.mastery-change-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.mastery-change-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mastery-change-head {
  font-size: 13px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
}

.mastery-change-head.positive {
  background: #ecfdf5;
  color: #15803d;
}

.mastery-change-head.warning {
  background: #fef3c7;
  color: #b45309;
}

.mastery-change-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mastery-change-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
}

.mastery-change-item:hover {
  background: #f1f5f9;
}

.mastery-change-item.positive {
  background: #f0fdf4;
}

.mastery-change-item.warning {
  background: #fffbeb;
}

.mastery-name {
  color: #334155;
}

.mastery-score {
  font-weight: 600;
  color: #64748b;
}

/* 遗忘预警 */
.forgetting-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.forgetting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  border-left: 3px solid #94a3b8;
  background: #f8fafc;
  transition: all 0.2s;
}

.forgetting-item:hover {
  background: #f1f5f9;
  transform: translateX(2px);
}

.forgetting-item.high {
  border-left-color: #ef4444;
  background: #fef2f2;
}

.forgetting-item.medium {
  border-left-color: #f59e0b;
  background: #fffbeb;
}

.forgetting-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.forgetting-name {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
}

.forgetting-desc {
  font-size: 12px;
  color: #64748b;
}

/* 推荐下一步 */
.recommendation-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recommendation-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid #e2e8f0;
  background: #fff;
  transition: all 0.2s;
}

.recommendation-item:hover {
  border-color: #818cf8;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.1);
  transform: translateX(4px);
}

.rec-icon {
  font-size: 22px;
  flex-shrink: 0;
}

.rec-content {
  flex: 1;
  min-width: 0;
}

.rec-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.rec-head strong {
  font-size: 14px;
  color: #1e293b;
}

.rec-reason {
  font-size: 13px;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
}

.rec-arrow {
  font-size: 18px;
  color: #cbd5e1;
  flex-shrink: 0;
}

.loading-placeholder {
  padding: 20px 0;
}

@media (max-width: 900px) {
  .report-stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .mastery-change-grid {
    grid-template-columns: 1fr;
  }
}
</style>
