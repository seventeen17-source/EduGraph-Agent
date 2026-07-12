<template>
  <div class="timeline-container">
    <!-- 统计面板 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_active_days }}</div>
        <div class="stat-label">累计学习天数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.current_streak }}<span class="stat-unit">天</span></div>
        <div class="stat-label">当前连续</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.mastered_concepts }}<span v-if="stats.strong_concepts" class="stat-sub"> / {{ stats.strong_concepts }} 精通</span></div>
        <div class="stat-label">掌握概念 (≥0.6)</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_exercises }}</div>
        <div class="stat-label">练习完成</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_feedback }}<span class="stat-unit">次</span></div>
        <div class="stat-label">学习反馈</div>
      </div>
    </div>

    <!-- 本周 vs 上周趋势 -->
    <div v-if="stats.this_week_days > 0 || stats.last_week_days > 0" class="trend-bar">
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

    <!-- 遗忘预警 -->
    <div v-if="forgettingSoon.length" class="forgetting-bar">
      <div class="forgetting-header">
        <span class="forgetting-title">⚠️ 建议复习</span>
        <span class="forgetting-subtitle">以下知识点已超过遗忘阈值，建议近期复习</span>
      </div>
      <div class="forgetting-list">
        <div
          v-for="fn in forgettingSoon"
          :key="fn.node_id"
          class="forgetting-item"
          :class="fn.urgency"
        >
          <div class="forgetting-info">
            <span class="forgetting-name">{{ fn.node_name }}</span>
            <span class="forgetting-detail">
              掌握度 {{ percent(fn.mastery_score) }}% ·
              {{ fn.days_since_review }} 天前复习 ·
              预计遗忘 {{ percent(fn.estimated_forgetting_rate) }}%
            </span>
          </div>
          <el-button size="small" type="primary" plain @click="$emit('goToNode', fn.node_id)">
            去复习
          </el-button>
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
              />
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
                    :class="e.type"
                    @click="$emit('goToNode', e.node_id)"
                  >
                    <span class="event-icon">{{ e.icon }}</span>
                    <div class="event-body">
                      <span class="event-title">{{ e.title }}</span>
                      <span v-if="e.description" class="event-desc">{{ e.description }}</span>
                      <span v-if="e.time" class="event-time">{{ e.time }}</span>
                    </div>
                    <span v-if="e.score_after !== null" class="event-score">
                      {{ percent(e.score_after ?? 0) }}%
                    </span>
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
      <div class="decision-title">基于你的学习规律</div>

      <div v-if="stats.current_streak >= 3" class="decision-item positive">
        🎯 你已经连续学习 {{ stats.current_streak }} 天。连续学习有助于形成稳定的知识结构。
      </div>

      <div v-if="stats.week_trend === 'down' && stats.last_week_days > 0" class="decision-item neutral">
        📊 本周学习天数比上周少。研究表明间隔学习不影响长期效果，但连续超过 7 天不复习可能导致 30% 的知识遗忘。
      </div>

      <div v-if="forgettingSoon.length >= 3" class="decision-item warning">
        ⚠️ 你有 {{ forgettingSoon.length }} 个知识点超过遗忘阈值。建议今天安排 15-20 分钟复习其中 1-2 个。
      </div>

      <div v-if="stats.total_active_days <= 3" class="decision-item info">
        🌱 你正在学习的起步阶段。前 7 天是建立学习节奏的关键期，每天学一点比集中突击更有效。
      </div>

      <div v-if="stats.total_active_days >= 30" class="decision-item positive">
        🏅 你已经累计学习 {{ stats.total_active_days }} 天，形成了一个稳定的学习习惯。
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ForgettingNode, LearningStats, MonthlySummary } from '@/types/profile'
import { percent } from '@/utils/format'

const props = defineProps<{
  months: MonthlySummary[]
  stats: LearningStats
  forgettingSoon: ForgettingNode[]
}>()

defineEmits<{
  goToNode: [nodeId: string | null]
}>()

const expandedMonth = ref<string | null>(null)

// 默认展开第一个月
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
  gap: 10px;
  margin-bottom: 16px;
}

.stat-card {
  background: #f8fafc;
  border-radius: 12px;
  padding: 16px 12px;
  text-align: center;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #4f46e5;
  line-height: 1.2;
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
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}

/* 趋势 */
.trend-bar {
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.trend-label { color: #64748b; }
.trend-value { color: #1e293b; }
.trend-up { color: #10b981; font-weight: 600; }
.trend-down { color: #f59e0b; font-weight: 600; }
.trend-stable { color: #94a3b8; }

/* 遗忘预警 */
.forgetting-bar {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 16px;
}

.forgetting-header {
  margin-bottom: 10px;
}

.forgetting-title {
  font-size: 15px;
  font-weight: 600;
  color: #92400e;
}

.forgetting-subtitle {
  font-size: 12px;
  color: #a16207;
  margin-left: 8px;
}

.forgetting-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.forgetting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #fff;
  border-radius: 8px;
  border-left: 3px solid #f59e0b;
}

.forgetting-item.high { border-left-color: #ef4444; }
.forgetting-item.medium { border-left-color: #f59e0b; }
.forgetting-item.low { border-left-color: #94a3b8; }

.forgetting-name {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
}

.forgetting-detail {
  font-size: 12px;
  color: #64748b;
  margin-left: 8px;
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
  gap: 12px;
  align-items: center;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  background: #f8fafc;
}

.month-summary:hover {
  background: #f1f5f9;
}

.month-bar-container {
  display: flex;
  gap: 3px;
}

.week-preview {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.day-cell {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  background: #f1f5f9;
}

.day-cell.s0 { background: #f1f5f9; }
.day-cell.s1 { background: #d9f99d; }
.day-cell.s3 { background: #86efac; }
.day-cell.s5 { background: #22c55e; }

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
  padding: 12px 0 12px 20px;
  border-left: 2px solid #e2e8f0;
  margin-left: 6px;
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

.day-empty {
  padding: 8px 10px;
  font-size: 13px;
}

.muted { color: #94a3b8; }

/* 决策面板 */
.decision-panel {
  background: #f8fafc;
  border-radius: 12px;
  padding: 16px;
  margin-top: 20px;
}

.decision-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
}

.decision-item {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  margin-bottom: 6px;
}

.decision-item.positive { background: #f0fdf4; color: #166534; }
.decision-item.warning { background: #fffbeb; color: #92400e; }
.decision-item.neutral { background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }
.decision-item.info { background: #eff6ff; color: #1e40af; }
</style>
