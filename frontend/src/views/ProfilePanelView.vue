<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>学生画像面板</h1>
        <div class="muted">{{ localizeText(dashboard?.headline || '展示学生画像、掌握度与更新时间线。') }}</div>
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
        <el-card class="section-card weak-card">
          <template #header>
            <div class="panel-title">
              <div class="panel-title-left">
                <span class="panel-icon">⚠️</span>
                <span>薄弱点优先级</span>
              </div>
              <el-tag type="warning">{{ dashboard?.weak_point_rank.length || 0 }} 项</el-tag>
            </div>
          </template>
          <div v-if="dashboard?.weak_point_rank.length" class="weak-list">
            <div
              v-for="item in dashboard.weak_point_rank"
              :key="`${item.label}-${item.node_id}`"
              class="weak-item"
              :class="getWeakClass(item.score)"
            >
              <div class="weak-info">
                <div class="weak-header">
                  <span class="weak-urgency" :class="getWeakClass(item.score)">
                    {{ getWeakLabel(item.score) }}
                  </span>
                  <strong class="weak-name">{{ displayNodeLabel(item.label || item.node_id) }}</strong>
                  <el-button
                    v-if="item.node_id"
                    text
                    size="small"
                    class="why-btn"
                    :loading="evidenceLoading[item.node_id]"
                    @click="toggleEvidence(item.node_id)"
                  >
                    <el-icon><QuestionFilled /></el-icon>
                    {{ expandedNodes[item.node_id] ? '收起' : '为什么' }}
                  </el-button>
                </div>
                <div class="weak-meta muted">
                  {{ weakSourceLabel(item.source) }} · {{ displayNodeLabel(item.node_id, '未映射知识点') }}
                </div>
              </div>
              <div class="weak-progress">
                <div class="progress-bar-container">
                  <div class="progress-bar-bg">
                    <div
                      class="progress-bar-fill"
                      :class="getWeakClass(item.score)"
                      :style="{ width: Math.round(item.score * 100) + '%' }"
                    />
                  </div>
                  <span class="progress-value">{{ Math.round(item.score * 100) }}%</span>
                </div>
              </div>
              <!-- 证据链展开区域 -->
              <div v-if="item.node_id && expandedNodes[item.node_id]" class="evidence-section">
                <div v-if="evidenceLoading[item.node_id]" class="evidence-loading muted">
                  正在加载证据...
                </div>
                <div v-else-if="(evidenceMap[item.node_id] || []).length === 0" class="evidence-empty muted">
                  暂无掌握度证据记录
                </div>
                <div v-else class="evidence-list">
                  <div
                    v-for="ev in evidenceMap[item.node_id]"
                    :key="ev.id"
                    class="evidence-item"
                  >
                    <div class="evidence-head">
                      <el-tag size="small" :type="evidenceSourceTagType(ev.source_type)" effect="plain">
                        {{ evidenceSourceLabel(ev.source_type) }}
                      </el-tag>
                      <span v-if="ev.score_delta !== 0" class="evidence-delta" :class="{ positive: ev.score_delta > 0, negative: ev.score_delta < 0 }">
                        {{ ev.score_delta > 0 ? '+' : '' }}{{ ev.score_delta.toFixed(2) }}
                      </span>
                      <span class="evidence-time muted">{{ formatEvidenceTime(ev.created_at) }}</span>
                    </div>
                    <div class="evidence-summary">{{ localizeText(ev.summary) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无薄弱点" :image-size="60" />
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
                <strong>{{ displayNodeLabel(item.node_name || item.node_id) }}</strong>
                <div class="muted">{{ chapterLabel(item.chapter_id) }} · {{ levelLabel(item.level) }}</div>
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
              <div class="panel-title-left">
                <span class="panel-icon">🧠</span>
                <span>学习行为画像</span>
              </div>
              <el-tag :type="behavior.total_feedback_count >= 5 ? 'success' : 'info'">
                {{ behavior.total_feedback_count }} 次评价
              </el-tag>
            </div>
          </template>

          <!-- 格式有效性 -->
          <div class="behavior-section">
            <div class="behavior-label">📊 最有效的内容格式</div>
            <div v-for="eff in topFormats" :key="eff.format" class="format-bar">
              <span class="format-name">{{ formatLabel(eff.format) }}</span>
              <div class="format-progress">
                <div class="format-bar-bg">
                  <div
                    class="format-bar-fill"
                    :style="{ width: Math.round(eff.effectiveness_score * 100) + '%' }"
                    :class="getFormatClass(eff.effectiveness_score)"
                  />
                </div>
                <span class="format-value">{{ Math.round(eff.effectiveness_score * 100) }}%</span>
              </div>
            </div>
            <div v-if="!topFormats.length" class="muted">积累更多评价后显示</div>
          </div>

          <!-- 深度偏好 -->
          <div class="behavior-section">
            <div class="behavior-label">🎯 讲解深度偏好</div>
            <div class="depth-cards">
              <div
                class="depth-card"
                :class="{ active: behavior.depth_preference.preferred_level === 'basic' }"
              >
                <div class="depth-icon">📗</div>
                <div class="depth-info">
                  <span class="depth-name">基础</span>
                  <span class="depth-count">{{ behavior.depth_preference.too_shallow_count }} 次</span>
                </div>
              </div>
              <div
                class="depth-card"
                :class="{ active: behavior.depth_preference.preferred_level === 'intermediate' }"
              >
                <div class="depth-icon">📙</div>
                <div class="depth-info">
                  <span class="depth-name">适中</span>
                  <span class="depth-count">{{ behavior.depth_preference.just_right_count }} 次</span>
                </div>
              </div>
              <div
                class="depth-card"
                :class="{ active: behavior.depth_preference.preferred_level === 'advanced' }"
              >
                <div class="depth-icon">📕</div>
                <div class="depth-info">
                  <span class="depth-name">进阶</span>
                  <span class="depth-count">{{ behavior.depth_preference.too_deep_count }} 次</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 理解缺口 -->
          <div v-if="activeGaps.length" class="behavior-section">
            <div class="behavior-label">⚠️ 理解缺口</div>
            <div v-for="gap in activeGaps" :key="gap.node_id" class="gap-item">
              <div class="gap-header">
                <div class="gap-title-area">
                  <span class="gap-node">{{ displayNodeLabel(gap.node_id) }}</span>
                  <span class="gap-severity">严重度 {{ Math.round(gap.severity * 100) }}%</span>
                </div>
              </div>
              <div v-if="gap.inferred_root_cause" class="gap-cause">💡 根因：{{ localizeText(gap.inferred_root_cause) }}</div>
              <div v-if="gap.recommended_strategy" class="gap-strategy">✨ 建议：{{ localizeText(gap.recommended_strategy) }}</div>
            </div>
          </div>

          <!-- LLM 洞察 -->
          <div v-if="behavior.insights.length" class="behavior-section">
            <div class="behavior-label">💡 系统洞察</div>
            <div v-for="ins in behavior.insights.slice(0, 3)" :key="ins.key" class="insight-item">
              <div class="insight-icon">💡</div>
              <div class="insight-content">
                <div class="insight-text">{{ localizeText(ins.description) }}</div>
              </div>
            </div>
          </div>

          <!-- 知识点策略 -->
          <div v-if="Object.keys(behavior.effective_strategies || {}).length" class="behavior-section">
            <div class="behavior-label">🎯 知识点策略</div>
            <div v-for="[nid, st] in strategyEntries" :key="nid" class="strategy-item">
              <strong>{{ displayNodeLabel(nid) }}</strong>
              <div v-if="st.best_approach" class="strategy-approach good">✅ 有效：{{ localizeText(st.best_approach) }}</div>
              <div v-if="st.avoid_approach" class="strategy-approach bad">❌ 避免：{{ localizeText(st.avoid_approach) }}</div>
            </div>
          </div>
        </el-card>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { QuestionFilled } from '@element-plus/icons-vue'

import ErrorAlert from '@/components/common/ErrorAlert.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import CompletenessBar from '@/components/profile/CompletenessBar.vue'
import ProfileCard from '@/components/profile/ProfileCard.vue'
import UpdateTimeline from '@/components/profile/UpdateTimeline.vue'
import { getNodeEvidence } from '@/api/profile'
import { useProfileStore } from '@/stores/profile'
import type { MasteryEvidenceRecord, PerNodeStrategy } from '@/types/profile'
import { chapterLabel, displayNodeLabel, displaySourceLabel, levelLabel, localizeText, percent, profileFieldLabel, relativeTime, resourceLabel, uidLabel } from '@/utils/format'

const profileStore = useProfileStore()
const loading = ref(false)
const dashboard = computed(() => profileStore.dashboard)

// ── 证据链展开状态 ──
const expandedNodes = ref<Record<string, boolean>>({})
const evidenceMap = ref<Record<string, MasteryEvidenceRecord[]>>({})
const evidenceLoading = ref<Record<string, boolean>>({})

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
  return labels[fmt] || displaySourceLabel(fmt, '学习格式')
}

function getFormatClass(score: number) {
  if (score >= 0.6) return 'high'
  if (score >= 0.4) return 'medium'
  return 'low'
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
      tags: [...p.progress.completed_node_ids, ...p.progress.in_progress_node_ids].map((id) => displayNodeLabel(id)),
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
  return displaySourceLabel(source, '来源')
}

function getWeakClass(score: number) {
  if (score >= 0.7) return 'critical'
  if (score >= 0.4) return 'warning'
  return 'normal'
}

function getWeakLabel(score: number) {
  if (score >= 0.7) return '紧急'
  if (score >= 0.4) return '注意'
  return '轻微'
}

// ── 证据链相关 ──

async function toggleEvidence(nodeId: string) {
  // 切换展开状态
  expandedNodes.value[nodeId] = !expandedNodes.value[nodeId]
  // 如果展开且尚未加载证据，则发起请求
  if (expandedNodes.value[nodeId] && !evidenceMap.value[nodeId]) {
    evidenceLoading.value[nodeId] = true
    try {
      const studentId = profileStore.studentId
      if (!studentId) return
      const records = await getNodeEvidence(studentId, nodeId)
      // 按时间倒序排序
      evidenceMap.value[nodeId] = records.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
    } catch {
      evidenceMap.value[nodeId] = []
    } finally {
      evidenceLoading.value[nodeId] = false
    }
  }
}

function evidenceSourceLabel(sourceType: string) {
  const labels: Record<string, string> = {
    exercise_result: '练习结果',
    forgetting_detection: '遗忘检测',
    diagnosis: '诊断评估',
    self_report: '学生自述',
    feedback: '用户反馈',
  }
  return labels[sourceType] || displaySourceLabel(sourceType, '未知来源')
}

function evidenceSourceTagType(sourceType: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  const types: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    exercise_result: 'warning',
    forgetting_detection: 'danger',
    diagnosis: 'info',
    self_report: '',
    feedback: 'success',
  }
  return types[sourceType] || 'info'
}

function formatEvidenceTime(timeStr: string) {
  if (!timeStr) return ''
  return new Date(timeStr).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
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
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 薄弱点卡片 */
.weak-card {
  border-radius: 12px;
}

.weak-item {
  display: flex;
  flex-direction: column;
  padding: 14px 16px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid rgba(255, 255, 255, 0.8);
  transition: all 0.2s ease;
}

.weak-item:hover {
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.weak-item.critical {
  border-left: 4px solid #ef4444;
  background: linear-gradient(145deg, #fff, #fef2f2);
}

.weak-item.warning {
  border-left: 4px solid #f59e0b;
  background: linear-gradient(145deg, #fff, #fffbeb);
}

.weak-item.normal {
  border-left: 4px solid #94a3b8;
}

.weak-info {
  margin-bottom: 10px;
}

.weak-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.weak-urgency {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.weak-urgency.critical {
  background: rgba(239, 68, 68, 0.15);
  color: #b91c1c;
}

.weak-urgency.warning {
  background: rgba(245, 158, 11, 0.15);
  color: #92400e;
}

.weak-urgency.normal {
  background: rgba(148, 163, 184, 0.15);
  color: #475569;
}

.weak-meta {
  margin-top: 4px;
  font-size: 12px;
}

.why-btn {
  margin-left: auto;
  padding: 2px 6px;
  font-size: 12px;
  color: #6366f1;
}

.why-btn :deep(.el-icon) {
  margin-right: 2px;
}

/* 证据链展开区域 */
.evidence-section {
  margin-top: 10px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  border-left: 3px solid #818cf8;
}

.evidence-loading,
.evidence-empty {
  font-size: 12px;
  padding: 6px 0;
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.evidence-item {
  padding: 8px 10px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #f1f5f9;
}

.evidence-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.evidence-delta {
  font-size: 12px;
  font-weight: 600;
}

.evidence-delta.positive {
  color: #059669;
}

.evidence-delta.negative {
  color: #dc2626;
}

.evidence-time {
  margin-left: auto;
  font-size: 11px;
}

.evidence-summary {
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
}

.weak-progress {
  margin-top: 4px;
}

.progress-bar-container {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-bar-bg {
  flex: 1;
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}

.progress-bar-fill.critical {
  background: linear-gradient(90deg, #ef4444, #f87171);
}

.progress-bar-fill.warning {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
}

.progress-bar-fill.normal {
  background: linear-gradient(90deg, #94a3b8, #cbd5e1);
}

.progress-value {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  min-width: 40px;
  text-align: right;
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
.behavior-card {
  border-radius: 12px;
}

.behavior-card :deep(.el-card__body) {
  padding: 18px 22px;
}

.behavior-section {
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid #f1f5f9;
}

.behavior-section:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

.behavior-label {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.format-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 10px;
}

.format-name {
  font-size: 13px;
  color: #475569;
  min-width: 70px;
  font-weight: 500;
}

.format-progress {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
}

.format-bar-bg {
  flex: 1;
  height: 8px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}

.format-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.format-bar-fill.high {
  background: linear-gradient(90deg, #10b981, #34d399);
}

.format-bar-fill.medium {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
}

.format-bar-fill.low {
  background: linear-gradient(90deg, #ef4444, #f87171);
}

.format-value {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  min-width: 36px;
  text-align: right;
}

/* 深度卡片 */
.depth-cards {
  display: flex;
  gap: 12px;
}

.depth-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 10px;
  border: 2px solid transparent;
  transition: all 0.2s ease;
}

.depth-card:hover {
  background: #f1f5f9;
}

.depth-card.active {
  background: #eef2ff;
  border-color: #6366f1;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15);
}

.depth-icon {
  font-size: 24px;
}

.depth-info {
  display: flex;
  flex-direction: column;
}

.depth-name {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.depth-count {
  font-size: 12px;
  color: #94a3b8;
}

.depth-card.active .depth-name {
  color: #4f46e5;
}

/* 理解缺口 */
.gap-item {
  padding: 14px 16px;
  background: linear-gradient(145deg, #fff, #fef2f2);
  border-radius: 10px;
  margin-bottom: 10px;
  border-left: 4px solid #ef4444;
}

.gap-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.gap-title-area {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.gap-node {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
}

.gap-severity {
  font-size: 12px;
  color: #ef4444;
  font-weight: 500;
}

.gap-cause,
.gap-strategy {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.gap-strategy {
  color: #6366f1;
}

/* 洞察 */
.insight-item {
  display: flex;
  gap: 12px;
  padding: 12px 14px;
  background: linear-gradient(145deg, #f0fdf4, #ecfdf5);
  border-radius: 10px;
  margin-bottom: 8px;
}

.insight-icon {
  font-size: 20px;
}

.insight-content {
  flex: 1;
}

.insight-text {
  font-size: 13px;
  line-height: 1.5;
  color: #334155;
}

.insight-confidence {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}

/* 策略 */
.strategy-item {
  padding: 12px 14px;
  background: linear-gradient(145deg, #f8fafc, #f1f5f9);
  border-radius: 10px;
  margin-bottom: 8px;
}

.strategy-item strong {
  color: #1e293b;
  font-size: 14px;
}

.strategy-approach {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.5;
}

.strategy-approach.good {
  color: #059669;
}

.strategy-approach.bad {
  color: #dc2626;
}
</style>
