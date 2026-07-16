<template>
  <div class="timeline-container">
    <!-- 空状态：无练习记录 -->
    <div v-if="!hasData" class="timeline-empty">
      <el-empty description="还没有学习记录。开始你的第一次练习吧！">
        <el-button type="primary" @click="router.push('/exercise')">去做练习</el-button>
      </el-empty>
    </div>

    <template v-else>
    <!-- 统计面板 -->
    <div class="stats-row">
      <div class="stat-card" style="--stat-color: #6366f1;">
        <div class="stat-icon">📅</div>
        <div class="stat-content">
          <div class="stat-value">{{ animatedStats.totalActiveDays }}</div>
          <div class="stat-label">累计学习天数</div>
        </div>
      </div>
      <div class="stat-card" style="--stat-color: #10b981;">
        <div class="stat-icon">🔥</div>
        <div class="stat-content">
          <div class="stat-value">{{ animatedStats.currentStreak }}<span class="stat-unit">天</span></div>
          <div class="stat-label">当前连续</div>
        </div>
      </div>
      <div class="stat-card" style="--stat-color: #8b5cf6;">
        <div class="stat-icon">💡</div>
        <div class="stat-content">
          <div class="stat-value">{{ animatedStats.masteredConcepts }}<span v-if="stats.strong_concepts" class="stat-sub"> / {{ stats.strong_concepts }} 精通</span></div>
          <div class="stat-label">掌握概念</div>
        </div>
      </div>
      <div class="stat-card" style="--stat-color: #f59e0b;">
        <div class="stat-icon">✅</div>
        <div class="stat-content">
          <div class="stat-value">{{ animatedStats.totalExercises }}</div>
          <div class="stat-label">练习完成</div>
        </div>
      </div>
      <div class="stat-card" style="--stat-color: #ec4899;">
        <div class="stat-icon">💬</div>
        <div class="stat-content">
          <div class="stat-value">{{ animatedStats.totalFeedback }}<span class="stat-unit">次</span></div>
          <div class="stat-label">学习反馈</div>
        </div>
      </div>
    </div>

    <!-- 本周 vs 上周趋势 -->
    <div v-if="stats.this_week_days > 0 || stats.last_week_days > 0" class="trend-bar">
      <div class="trend-left">
        <span class="trend-label">学习节奏</span>
        <span class="trend-value">
          本周 {{ stats.this_week_days }} 天
          <template v-if="stats.last_week_days > 0">
            · 上周 {{ stats.last_week_days }} 天
            <span v-if="stats.week_trend === 'up'" class="trend-up">↑ 上升</span>
            <span v-else-if="stats.week_trend === 'down'" class="trend-down">↓ 下降</span>
            <span v-else class="trend-stable">→ 持平</span>
          </template>
        </span>
      </div>
      <div class="trend-chart">
        <div class="chart-bar">
          <div class="bar-item" :style="{ height: (stats.last_week_days / 7 * 100) + '%' }">
            <span class="bar-label">上周</span>
          </div>
          <div class="bar-item current" :style="{ height: (stats.this_week_days / 7 * 100) + '%' }">
            <span class="bar-label">本周</span>
          </div>
        </div>
        <div class="chart-scale">
          <span>7</span>
          <span>4</span>
          <span>1</span>
        </div>
      </div>
    </div>

    <!-- 遗忘预警 -->
    <div v-if="forgettingSoon.length" class="forgetting-bar">
      <div class="forgetting-header">
        <div class="forgetting-icon">🔔</div>
        <div class="forgetting-title-area">
          <span class="forgetting-title">建议复习</span>
          <span class="forgetting-subtitle">以下知识点已超过遗忘阈值，建议近期复习</span>
        </div>
        <span class="forgetting-count">{{ forgettingSoon.length }} 项</span>
      </div>
      <div class="forgetting-list">
        <div
          v-for="fn in forgettingSoon"
          :key="fn.node_id"
          class="forgetting-item"
          :class="fn.urgency"
        >
          <div class="forgetting-info">
            <span class="forgetting-name">{{ displayNodeLabel(fn.node_name || fn.node_id) }}</span>
            <div class="forgetting-progress">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: percent(fn.mastery_score) + '%' }"
                  :class="fn.urgency"
                />
              </div>
              <span class="progress-text">掌握度 {{ percent(fn.mastery_score) }}%</span>
            </div>
            <span class="forgetting-detail">
              {{ fn.days_since_review }} 天前复习 ·
              预计遗忘 {{ percent(fn.estimated_forgetting_rate) }}%
            </span>
          </div>
          <div class="forgetting-actions">
            <span class="urgency-badge" :class="fn.urgency">
              {{ fn.urgency === 'high' ? '紧急' : fn.urgency === 'medium' ? '一般' : '轻微' }}
            </span>
            <el-button size="small" type="primary" plain @click="handleReviewClick(fn)">
              去复习
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 日历热力图 -->
    <div class="calendar-heatmap">
      <div class="heatmap-header">
        <span class="heatmap-title">学习日历</span>
        <span class="heatmap-months">
          <span
            v-for="m in months"
            :key="m.month"
            class="month-label"
            :class="{ active: expandedMonth === m.month }"
            @click="expandedMonth = expandedMonth === m.month ? null : m.month"
          >
            {{ m.month_label }}
          </span>
        </span>
      </div>

      <div
        v-for="m in months"
        :key="m.month"
        class="month-block"
        :class="{ expanded: expandedMonth === m.month }"
      >
        <!-- 月摘要（折叠态） -->
        <div class="month-summary" @click="expandedMonth = expandedMonth === m.month ? null : m.month">
          <div class="month-bar-container">
            <div
              v-for="w in m.weeks"
              :key="w.week_start"
              class="week-preview"
            >
              <div
                v-for="d in w.days"
                :key="d.date"
                class="day-cell"
                :class="scoreClass(d.active_score)"
                :title="`${d.date} · ${d.active_score}/6 活跃度`"
              >
                <div v-if="d.events.length > 0" class="day-dot" />
              </div>
            </div>
          </div>
          <div class="month-info">
            <span class="month-name">{{ m.month_label }}</span>
            <span class="month-stats">
              {{ m.active_days }} 天活跃 ·
              +{{ m.new_concepts }} 概念 ·
              {{ m.exercises_done }} 练习
            </span>
          </div>
        </div>

        <!-- 展开：按周的事件列表 -->
        <div v-if="expandedMonth === m.month" class="month-detail">
          <div v-for="w in m.weeks" :key="w.week_start" class="week-section">
            <div class="week-label">{{ w.week_label }} · {{ w.active_days }}/7 天</div>
            <div
              v-for="d in w.days"
              :key="d.date"
              class="day-section"
            >
              <template v-if="d.events.length">
                <div class="day-header">
                  <span class="day-date">{{ formatDay(d.date) }}</span>
                  <span class="day-score">活跃度 {{ d.active_score }}/6</span>
                </div>
                <div class="day-events">
                  <div
                    v-for="e in d.events"
                    :key="`${e.date}-${e.type}-${e.title}`"
                    class="timeline-event"
                    :class="[e.type, { 'has-link': e.action_url }]"
                    @click="handleEventClick(e)"
                  >
                    <span class="event-icon">{{ e.icon }}</span>
                    <div class="event-body">
                      <span class="event-title">{{ localizeText(e.title) }}</span>
                      <span v-if="e.description" class="event-desc">{{ localizeText(e.description) }}</span>
                      <span v-if="e.time" class="event-time">{{ e.time }}</span>
                    </div>
                    <span v-if="e.score_after !== null" class="event-score">
                      {{ percent(e.score_after ?? 0) }}%
                    </span>
                    <span v-if="e.action_url" class="event-link-icon">→</span>
                  </div>
                </div>
              </template>
              <div v-else class="day-empty">
                <span class="day-date muted">{{ formatDay(d.date) }}</span>
                <span class="muted">—— 没有学习记录 ——</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：决策面板 -->
    <div class="decision-panel">
      <div class="decision-header">
        <div class="decision-icon">🤖</div>
        <div class="decision-title-area">
          <div class="decision-title">AI 学习建议</div>
          <div class="decision-subtitle">基于你的学习规律分析</div>
        </div>
      </div>

      <div class="decision-grid">
        <div v-if="stats.current_streak >= 3" class="decision-card positive">
          <div class="decision-card-icon">🔥</div>
          <div class="decision-card-content">
            <div class="decision-card-title">连续学习达成</div>
            <div class="decision-card-text">
              你已经连续学习 {{ stats.current_streak }} 天。连续学习有助于形成稳定的知识结构。
            </div>
          </div>
          <div class="decision-card-action">
            <el-button size="small" type="primary" plain>继续保持</el-button>
          </div>
        </div>

        <div v-if="stats.week_trend === 'down' && stats.last_week_days > 0" class="decision-card neutral">
          <div class="decision-card-icon">📉</div>
          <div class="decision-card-content">
            <div class="decision-card-title">学习节奏调整</div>
            <div class="decision-card-text">
              本周学习天数比上周少。研究表明间隔学习不影响长期效果，但连续超过 7 天不复习可能导致 30% 的知识遗忘。
            </div>
          </div>
          <div class="decision-card-action">
            <el-button size="small" type="warning" plain>查看建议</el-button>
          </div>
        </div>

        <div v-if="forgettingSoon.length >= 3" class="decision-card warning">
          <div class="decision-card-icon">⚠️</div>
          <div class="decision-card-content">
            <div class="decision-card-title">复习提醒</div>
            <div class="decision-card-text">
              你有 {{ forgettingSoon.length }} 个知识点超过遗忘阈值。建议今天安排 15-20 分钟复习其中 1-2 个。
            </div>
          </div>
          <div class="decision-card-action">
            <el-button size="small" type="danger" plain @click="scrollToForgettingBar">
              立即复习
            </el-button>
          </div>
        </div>

        <div v-if="stats.total_active_days <= 3" class="decision-card info">
          <div class="decision-card-icon">🌱</div>
          <div class="decision-card-content">
            <div class="decision-card-title">起步阶段</div>
            <div class="decision-card-text">
              你正在学习的起步阶段。前 7 天是建立学习节奏的关键期，每天学一点比集中突击更有效。
            </div>
          </div>
          <div class="decision-card-action">
            <el-button size="small" type="info" plain>开始学习</el-button>
          </div>
        </div>

        <div v-if="stats.total_active_days >= 30" class="decision-card positive">
          <div class="decision-card-icon">🏅</div>
          <div class="decision-card-content">
            <div class="decision-card-title">学习习惯养成</div>
            <div class="decision-card-text">
              你已经累计学习 {{ stats.total_active_days }} 天，形成了一个稳定的学习习惯。
            </div>
          </div>
          <div class="decision-card-action">
            <el-button size="small" type="success" plain>继续挑战</el-button>
          </div>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { ForgettingNode, LearningStats, MonthlySummary, TimelineEvent } from '@/types/profile'
import { displayNodeLabel, localizeText, percent } from '@/utils/format'

const props = defineProps<{
  months: MonthlySummary[]
  stats: LearningStats
  forgettingSoon: ForgettingNode[]
}>()

const emit = defineEmits<{
  goToNode: [nodeId: string | null]
}>()

const router = useRouter()
const expandedMonth = ref<string | null>(null)

function handleReviewClick(fn: ForgettingNode) {
  if (fn.action_url) {
    router.push(fn.action_url)
  } else {
    emit('goToNode', fn.node_id)
  }
}

function handleEventClick(e: TimelineEvent) {
  if (e.action_url) {
    router.push(e.action_url)
  } else {
    emit('goToNode', e.node_id)
  }
}

// 判断是否有练习记录（避免新用户看到全为 0 的统计卡片和空热力图）
const hasData = computed(() => {
  return (
    props.stats.total_active_days > 0 ||
    props.stats.total_exercises > 0 ||
    props.months.length > 0
  )
})

const animatedStats = ref({
  totalActiveDays: 0,
  currentStreak: 0,
  masteredConcepts: 0,
  totalExercises: 0,
  totalFeedback: 0
})

function animateValue(key: keyof typeof animatedStats.value, end: number, duration = 1500) {
  const start = animatedStats.value[key]
  const startTime = performance.now()
  function update(currentTime: number) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const easeOut = 1 - Math.pow(1 - progress, 3)
    animatedStats.value[key] = Math.round(start + (end - start) * easeOut)
    if (progress < 1) {
      requestAnimationFrame(update)
    }
  }
  requestAnimationFrame(update)
}

onMounted(() => {
  setTimeout(() => {
    animateValue('totalActiveDays', props.stats.total_active_days)
    animateValue('currentStreak', props.stats.current_streak)
    animateValue('masteredConcepts', props.stats.mastered_concepts)
    animateValue('totalExercises', props.stats.total_exercises)
    animateValue('totalFeedback', props.stats.total_feedback)
  }, 300)
})

watch(() => props.stats, (newStats) => {
  animateValue('totalActiveDays', newStats.total_active_days)
  animateValue('currentStreak', newStats.current_streak)
  animateValue('masteredConcepts', newStats.mastered_concepts)
  animateValue('totalExercises', newStats.total_exercises)
  animateValue('totalFeedback', newStats.total_feedback)
}, { deep: true })

if (props.months.length > 0 && !expandedMonth.value) {
  expandedMonth.value = props.months[0].month
}

function scoreClass(score: number) {
  if (score >= 5) return 's5'
  if (score >= 3) return 's3'
  if (score >= 1) return 's1'
  return 's0'
}

function formatDay(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function scrollToForgettingBar() {
  expandedMonth.value = null
  globalThis.document?.querySelector('.forgetting-bar')?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<style scoped>
.timeline-container {
  max-width: 900px;
  margin: 0 auto;
}

/* 统计面板 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  background: linear-gradient(145deg, #ffffff, #f8fafc);
  border-radius: 16px;
  padding: 18px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.8);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.05);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: linear-gradient(135deg, var(--stat-color), var(--stat-color));
  opacity: 0.15;
  flex-shrink: 0;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--stat-color);
  line-height: 1.1;
}

.stat-unit {
  font-size: 14px;
  font-weight: 400;
  color: #94a3b8;
}

.stat-sub {
  font-size: 14px;
  font-weight: 500;
  color: #10b981;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

/* 趋势 */
.trend-bar {
  background: linear-gradient(145deg, #f8fafc, #f1f5f9);
  border-radius: 12px;
  padding: 14px 18px;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.trend-left {
  display: flex;
  flex-direction: column;
}

.trend-label {
  color: #64748b;
  font-size: 12px;
  margin-bottom: 2px;
}

.trend-value {
  color: #1e293b;
  font-weight: 500;
}

.trend-up { color: #10b981; font-weight: 600; }
.trend-down { color: #f59e0b; font-weight: 600; }
.trend-stable { color: #94a3b8; }

.trend-chart {
  display: flex;
  align-items: flex-end;
  gap: 20px;
  height: 60px;
}

.chart-bar {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  height: 100%;
}

.bar-item {
  width: 24px;
  background: linear-gradient(180deg, #cbd5e1, #94a3b8);
  border-radius: 4px 4px 0 0;
  position: relative;
  transition: height 0.5s ease;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
}

.bar-item.current {
  background: linear-gradient(180deg, #818cf8, #4f46e5);
}

.bar-label {
  font-size: 10px;
  color: #94a3b8;
  margin-top: 4px;
  position: absolute;
  bottom: -18px;
}

.bar-item.current .bar-label {
  color: #4f46e5;
  font-weight: 500;
}

.chart-scale {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
  font-size: 10px;
  color: #cbd5e1;
}

/* 遗忘预警 */
.forgetting-bar {
  background: linear-gradient(145deg, #fffbeb, #fef3c7);
  border: 1px solid #fde68a;
  border-radius: 16px;
  padding: 18px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(251, 191, 36, 0.15);
}

.forgetting-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.forgetting-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(251, 191, 36, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.forgetting-title-area {
  flex: 1;
}

.forgetting-title {
  font-size: 16px;
  font-weight: 600;
  color: #92400e;
  display: block;
}

.forgetting-subtitle {
  font-size: 12px;
  color: #a16207;
  margin-top: 2px;
  display: block;
}

.forgetting-count {
  background: rgba(251, 191, 36, 0.3);
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  color: #92400e;
}

.forgetting-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.forgetting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fff;
  border-radius: 12px;
  border-left: 4px solid #f59e0b;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
}

.forgetting-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.forgetting-item.high { border-left-color: #ef4444; }
.forgetting-item.medium { border-left-color: #f59e0b; }
.forgetting-item.low { border-left-color: #94a3b8; }

.forgetting-info {
  flex: 1;
}

.forgetting-name {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
  display: block;
}

.forgetting-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
  background: #f59e0b;
}

.progress-fill.high { background: #ef4444; }
.progress-fill.medium { background: #f59e0b; }
.progress-fill.low { background: #94a3b8; }

.progress-text {
  font-size: 11px;
  color: #64748b;
  white-space: nowrap;
}

.forgetting-detail {
  font-size: 12px;
  color: #64748b;
  display: block;
}

.forgetting-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 16px;
}

.urgency-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(245, 158, 11, 0.15);
  color: #92400e;
}

.urgency-badge.high {
  background: rgba(239, 68, 68, 0.15);
  color: #b91c1c;
}

.urgency-badge.low {
  background: rgba(148, 163, 184, 0.15);
  color: #475569;
}

/* 日历热力图 */
.calendar-heatmap {
  margin-bottom: 16px;
}

.heatmap-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.heatmap-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.heatmap-months {
  display: flex;
  gap: 6px;
}

.month-label {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  background: #f1f5f9;
}

.month-label.active {
  background: #4f46e5;
  color: #fff;
}

/* 月块 */
.month-block {
  margin-bottom: 8px;
}

.month-summary {
  display: flex;
  gap: 14px;
  align-items: center;
  cursor: pointer;
  padding: 12px 16px;
  border-radius: 12px;
  background: linear-gradient(145deg, #ffffff, #f8fafc);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.month-summary:hover {
  background: #f1f5f9;
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.month-bar-container {
  display: flex;
  gap: 4px;
}

.week-preview {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.day-cell {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  cursor: pointer;
  position: relative;
}

.day-cell:hover {
  transform: scale(1.3);
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.day-cell.s0 { background: #f3f4f6; }
.day-cell.s1 { background: #d1fae5; }
.day-cell.s3 { background: #6ee7b7; }
.day-cell.s5 { background: #059669; }

.day-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6);
}

.month-info {
  display: flex;
  flex-direction: column;
}

.month-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.month-stats {
  font-size: 12px;
  color: #94a3b8;
}

/* 展开的日事件 */
.month-detail {
  padding: 16px 0 16px 24px;
  border-left: 2px solid #c4b5fd;
  margin-left: 8px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.week-section {
  margin-bottom: 16px;
}

.week-label {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 8px;
}

.day-section {
  margin-bottom: 10px;
}

.day-header {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 4px;
}

.day-date {
  font-weight: 600;
  color: #1e293b;
}

.day-score {
  font-size: 11px;
  color: #94a3b8;
}

.day-events {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.timeline-event {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #f1f5f9;
  cursor: pointer;
  transition: background 0.15s;
}

.timeline-event:hover {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.timeline-event.mastery_milestone,
.timeline-event.mastery_strong {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.timeline-event.profile_created {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.event-icon { font-size: 16px; flex-shrink: 0; }

.event-body {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.event-title {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
}

.event-desc {
  font-size: 12px;
  color: #64748b;
  margin-top: 1px;
}

.event-time {
  font-size: 11px;
  color: #94a3b8;
}

.event-score {
  font-size: 13px;
  font-weight: 600;
  color: #4f46e5;
  white-space: nowrap;
}

.timeline-event.has-link {
  cursor: pointer;
}

.timeline-event.has-link:hover {
  border-color: #818cf8;
  background: #eef2ff;
}

.event-link-icon {
  font-size: 14px;
  color: #818cf8;
  font-weight: 600;
  flex-shrink: 0;
  margin-left: 4px;
  transition: transform 0.15s ease;
}

.timeline-event.has-link:hover .event-link-icon {
  transform: translateX(3px);
  color: #4f46e5;
}

.day-empty {
  padding: 8px 10px;
  font-size: 13px;
}

.muted { color: #94a3b8; }

/* 决策面板 */
.decision-panel {
  background: linear-gradient(145deg, #f8fafc, #f1f5f9);
  border-radius: 16px;
  padding: 20px;
  margin-top: 24px;
}

.decision-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.decision-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(79, 70, 229, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.decision-title-area {
  display: flex;
  flex-direction: column;
}

.decision-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.decision-subtitle {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.decision-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.decision-card {
  display: flex;
  flex-direction: column;
  padding: 16px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
}

.decision-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.decision-card-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.decision-card-content {
  flex: 1;
}

.decision-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}

.decision-card-text {
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
}

.decision-card-action {
  margin-top: 12px;
}

.decision-card.positive { border-left: 4px solid #10b981; }
.decision-card.warning { border-left: 4px solid #f59e0b; }
.decision-card.neutral { border-left: 4px solid #64748b; }
.decision-card.info { border-left: 4px solid #3b82f6; }
</style>
