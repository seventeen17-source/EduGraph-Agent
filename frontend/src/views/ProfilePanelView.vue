<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>学生画像面板</h1>
        <div class="muted">{{ dashboard?.headline || '展示学生画像、掌握度与更新时间线。' }}</div>
      </div>
      <div class="title-actions">
        <el-button @click="$router.push('/profile/chat')">继续对话</el-button>
        <el-button type="primary" @click="$router.push('/graph')">开始学习</el-button>
      </div>
    </div>

    <ErrorAlert :message="profileStore.error" :retry="load" />
    <LoadingSkeleton v-if="loading" :rows="8" />

    <template v-else>
      <el-card class="section-card overview-card">
        <CompletenessBar :value="profileStore.completeness" label="画像完整度" />
        <div class="overview-meta">
          <el-tag type="primary">{{ profileStore.displayName }}</el-tag>
          <span>最近更新：{{ relativeTime(profileStore.profile?.updated_at) }}</span>
          <span>缺失维度：{{ dashboard?.missing_dimensions.map(profileFieldLabel).join('、') || '无' }}</span>
        </div>
      </el-card>

      <div class="profile-grid">
        <ProfileCard
          v-for="card in cards"
          :key="card.key"
          :title="card.title"
          :icon="card.icon"
          :summary="card.summary"
          :tags="card.tags"
          :confidence="card.confidence"
          :source="card.source"
          :last-updated="card.lastUpdated"
        />
      </div>

      <div class="lower-grid">
        <el-card class="section-card">
          <template #header>
            <div class="panel-title">
              <span>薄弱点优先级</span>
              <el-tag type="warning">{{ dashboard?.weak_point_rank.length || 0 }} 项</el-tag>
            </div>
          </template>
          <div v-if="dashboard?.weak_point_rank.length" class="weak-list">
            <div v-for="item in dashboard.weak_point_rank" :key="`${item.label}-${item.node_id}`" class="weak-item">
              <div>
                <strong>{{ item.label }}</strong>
                <div class="muted">{{ weakSourceLabel(item.source) }} · {{ uidLabel(item.node_id) || '未映射知识点' }}</div>
              </div>
              <el-progress type="circle" :width="48" :percentage="Math.round(item.score * 100)" />
            </div>
          </div>
          <el-empty v-else description="暂无薄弱点" />
        </el-card>

        <el-card class="section-card">
          <template #header>
            <div class="panel-title">
              <span>知识点掌握概览</span>
              <el-tag type="success">{{ dashboard?.mastery_overview.length || 0 }} 个知识点</el-tag>
            </div>
          </template>
          <div class="mastery-list">
            <div v-for="item in dashboard?.mastery_overview" :key="item.node_id" class="mastery-item">
              <div>
                <strong>{{ item.node_name || uidLabel(item.node_id) }}</strong>
                <div class="muted">{{ chapterLabel(item.chapter_id) }} · {{ levelLabel(item.level) }} · 置信度 {{ percent(item.confidence) }}%</div>
              </div>
              <el-progress :percentage="percent(item.mastery_score)" :stroke-width="9" class="mastery-progress" />
            </div>
          </div>
        </el-card>

        <el-card class="section-card timeline-card">
          <template #header>
            <div class="panel-title">
              <span>画像更新时间线</span>
              <el-tag>{{ profileStore.history.length }}</el-tag>
            </div>
          </template>
          <UpdateTimeline :items="profileStore.history" />
        </el-card>

        <!-- 学习行为画像 -->
        <el-card v-if="behavior" class="section-card behavior-card">
          <template #header>
            <div class="panel-title">
              <span>🧠 学习行为画像</span>
              <el-tag :type="behavior.total_feedback_count >= 5 ? 'success' : 'info'">
                {{ behavior.total_feedback_count }} 次评价
              </el-tag>
            </div>
          </template>

          <!-- 格式有效性 -->
          <div class="behavior-section">
            <div class="behavior-label">最有效的内容格式</div>
            <div v-for="eff in topFormats" :key="eff.format" class="format-bar">
              <span class="format-name">{{ formatLabel(eff.format) }}</span>
              <el-progress
                :percentage="Math.round(eff.effectiveness_score * 100)"
                :stroke-width="8"
                :color="eff.effectiveness_score >= 0.6 ? '#10b981' : eff.effectiveness_score >= 0.4 ? '#f59e0b' : '#ef4444'"
              />
            </div>
            <div v-if="!topFormats.length" class="muted">积累更多评价后显示</div>
          </div>

          <!-- 深度偏好 -->
          <div class="behavior-section">
            <div class="behavior-label">讲解深度偏好</div>
            <div class="depth-row">
              <span :class="{ active: behavior.depth_preference.preferred_level === 'basic' }">基础 🟢</span>
              <span :class="{ active: behavior.depth_preference.preferred_level === 'intermediate' }">适中 🟡</span>
              <span :class="{ active: behavior.depth_preference.preferred_level === 'advanced' }">进阶 🔴</span>
            </div>
            <div class="depth-detail muted">
              太简单{{ behavior.depth_preference.too_shallow_count }}次 ·
              适中{{ behavior.depth_preference.just_right_count }}次 ·
              太难{{ behavior.depth_preference.too_deep_count }}次
            </div>
          </div>

          <!-- 理解缺口 -->
          <div v-if="activeGaps.length" class="behavior-section">
            <div class="behavior-label">⚠️ 理解缺口</div>
            <div v-for="gap in activeGaps" :key="gap.node_id" class="gap-item">
              <div class="gap-header">
                <span class="gap-node">{{ uidLabel(gap.node_id) }}</span>
                <el-progress
                  type="circle"
                  :width="40"
                  :percentage="Math.round(gap.severity * 100)"
                  :stroke-width="6"
                  color="#ef4444"
                />
              </div>
              <div v-if="gap.inferred_root_cause" class="gap-cause muted">根因：{{ gap.inferred_root_cause }}</div>
              <div v-if="gap.recommended_strategy" class="gap-strategy">建议：{{ gap.recommended_strategy }}</div>
            </div>
          </div>

          <!-- LLM 洞察 -->
          <div v-if="behavior.insights.length" class="behavior-section">
            <div class="behavior-label">💡 系统洞察</div>
            <div v-for="ins in behavior.insights.slice(0, 3)" :key="ins.key" class="insight-item">
              {{ ins.description }}
              <span class="insight-confidence muted">(置信度 {{ Math.round(ins.confidence * 100) }}%)</span>
            </div>
          </div>

          <!-- 知识点策略 -->
          <div v-if="Object.keys(behavior.effective_strategies || {}).length" class="behavior-section">
            <div class="behavior-label">🎯 知识点策略</div>
            <div v-for="[nid, st] in strategyEntries" :key="nid" class="strategy-item">
              <strong>{{ uidLabel(nid) }}</strong>
              <div v-if="st.best_approach">✅ 有效：{{ st.best_approach }}</div>
              <div v-if="st.avoid_approach">❌ 避免：{{ st.avoid_approach }}</div>
            </div>
          </div>
        </el-card>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import ErrorAlert from '@/components/common/ErrorAlert.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import CompletenessBar from '@/components/profile/CompletenessBar.vue'
import ProfileCard from '@/components/profile/ProfileCard.vue'
import UpdateTimeline from '@/components/profile/UpdateTimeline.vue'
import { useProfileStore } from '@/stores/profile'
import type { PerNodeStrategy } from '@/types/profile'
import { chapterLabel, levelLabel, percent, profileFieldLabel, relativeTime, resourceLabel, uidLabel } from '@/utils/format'

const profileStore = useProfileStore()
const loading = ref(false)
const dashboard = computed(() => profileStore.dashboard)

// 行为画像
const behavior = computed(() => profileStore.profile?.learning_behavior)

const topFormats = computed(() => {
  const b = behavior.value
  if (!b?.format_effectiveness) return []
  return Object.values(b.format_effectiveness)
    .filter(f => f.positive_count + f.negative_count >= 1)
    .sort((a, b) => b.effectiveness_score - a.effectiveness_score)
    .slice(0, 4)
})

const activeGaps = computed(() => {
  return (behavior.value?.comprehension_gaps || []).filter(g => !g.resolved)
})

const strategyEntries = computed<[string, PerNodeStrategy][]>(() => {
  return Object.entries(behavior.value?.effective_strategies || {}).slice(0, 3)
})

function formatLabel(fmt: string) {
  const labels: Record<string, string> = {
    diagram: '图解', code: '代码', formula: '公式推导',
    analogy: '类比', step_by_step: '分步讲解',
  }
  return labels[fmt] || fmt
}

const cards = computed(() => {
  const p = profileStore.profile
  if (!p) return []
  return [
    {
      key: 'background',
      title: '专业背景',
      icon: 'User',
      summary: `${p.background.major || '未填写'} · 大${p.background.grade || '?'}`,
      tags: p.background.course_foundation,
      confidence: p.background.confidence,
      source: p.background.source,
      lastUpdated: p.background.last_updated
    },
    {
      key: 'learning_goal',
      title: '学习目标',
      icon: 'Target',
      summary: p.learning_goal.description || '未填写学习目标',
      tags: p.learning_goal.goal_type,
      confidence: p.learning_goal.confidence,
      source: p.learning_goal.source,
      lastUpdated: p.learning_goal.last_updated
    },
    {
      key: 'knowledge_base',
      title: '知识掌握',
      icon: 'BookOpen',
      summary: `${p.knowledge_base.known_topics.length} 个已知主题，${Object.keys(p.node_mastery).length} 个知识点记录`,
      tags: p.knowledge_base.known_topics.map((item) => `${item.topic}/${levelLabel(item.level)}`),
      confidence: p.knowledge_base.confidence,
      source: p.knowledge_base.source,
      lastUpdated: p.knowledge_base.last_updated
    },
    {
      key: 'progress',
      title: '学习进度',
      icon: 'Clock',
      summary: `${chapterLabel(p.progress.current_chapter_id) || '未进入章节'} · 完成率 ${percent(p.progress.completion_rate)}%`,
      tags: [...p.progress.completed_node_ids, ...p.progress.in_progress_node_ids].map(uidLabel),
      confidence: p.progress.confidence,
      source: p.progress.source,
      lastUpdated: p.progress.last_active_at
    },
    {
      key: 'cognitive_style',
      title: '认知风格',
      icon: 'MagicStick',
      summary: `${resourceLabel(p.cognitive_style.primary) || '未判断'} / ${resourceLabel(p.cognitive_style.secondary) || '未判断'}`,
      tags: p.cognitive_style.style_ranking.map(resourceLabel),
      confidence: p.cognitive_style.confidence,
      source: p.cognitive_style.source,
      lastUpdated: p.cognitive_style.last_updated
    },
    {
      key: 'weak_points',
      title: '薄弱点',
      icon: 'AlertTriangle',
      summary: `${p.weak_points.self_reported.length + p.weak_points.diagnosed.length} 个需要补强`,
      tags: p.weak_points.self_reported.map((item) => item.topic),
      confidence: p.weak_points.confidence,
      source: p.weak_points.source,
      lastUpdated: p.weak_points.last_updated
    },
    {
      key: 'preferences',
      title: '学习偏好',
      icon: 'SlidersHorizontal',
      summary: p.preferences.resource_ranking.map(resourceLabel).join(' > ') || '未填写偏好',
      tags: [levelLabel(p.preferences.session_length), levelLabel(p.preferences.difficulty_preference), ...p.preferences.resource_ranking.map(resourceLabel)],
      confidence: p.preferences.confidence,
      source: p.preferences.source,
      lastUpdated: p.preferences.last_updated
    },
    {
      key: 'ability_state',
      title: '能力水平',
      icon: 'TrendCharts',
      summary: `编程 ${levelLabel(p.ability_state.programming)} · 数学 ${levelLabel(p.ability_state.mathematics)}`,
      tags: [`论文阅读 ${levelLabel(p.ability_state.reading_papers)}`, `应用 ${levelLabel(p.ability_state.application)}`],
      confidence: p.ability_state.confidence,
      source: p.ability_state.source,
      lastUpdated: p.ability_state.last_updated
    }
  ]
})

function weakSourceLabel(source: string) {
  if (source === 'self_reported') return '学生自述'
  if (source === 'diagnosed') return '练习诊断'
  if (source === 'mastery') return '掌握度计算'
  return source
}

async function load() {
  loading.value = true
  try {
    if (!profileStore.profile) {
      await profileStore.initFromAuth()
    } else {
      await profileStore.loadCurrentStudent()
    }
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.title-actions,
.overview-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.overview-card {
  margin-bottom: 16px;
}

.overview-meta {
  margin-top: 12px;
  color: #606266;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.lower-grid {
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr) 430px;
  gap: 16px;
  margin-top: 16px;
}

.weak-list,
.mastery-list {
  display: grid;
  gap: 12px;
}

.weak-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.mastery-item {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  align-items: center;
  gap: 16px;
}

.timeline-card {
  max-height: 500px;
  overflow: auto;
}

/* 行为画像 */
.behavior-card :deep(.el-card__body) {
  padding: 16px 20px;
}

.behavior-section {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #f1f5f9;
}

.behavior-section:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

.behavior-label {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}

.format-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.format-name {
  font-size: 13px;
  color: #475569;
  min-width: 60px;
}

.depth-row {
  display: flex;
  gap: 16px;
  font-size: 14px;
}

.depth-row span {
  padding: 4px 12px;
  border-radius: 14px;
  background: #f1f5f9;
  color: #94a3b8;
  cursor: default;
}

.depth-row span.active {
  background: #eef2ff;
  color: #4f46e5;
  font-weight: 600;
}

.depth-detail {
  margin-top: 6px;
  font-size: 12px;
}

.gap-item {
  padding: 10px;
  background: #fef2f2;
  border-radius: 8px;
  margin-bottom: 8px;
}

.gap-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.gap-node {
  font-weight: 600;
  font-size: 14px;
}

.gap-cause,
.gap-strategy {
  margin-top: 4px;
  font-size: 12px;
}

.gap-strategy {
  color: #4f46e5;
}

.insight-item {
  padding: 8px 10px;
  background: #f0fdf4;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 6px;
  line-height: 1.5;
}

.insight-confidence {
  font-size: 11px;
}

.strategy-item {
  padding: 8px 10px;
  background: #f8fafc;
  border-radius: 6px;
  margin-bottom: 6px;
  font-size: 13px;
}

.strategy-item div {
  margin-top: 3px;
  font-size: 12px;
  color: #64748b;
}
</style>
