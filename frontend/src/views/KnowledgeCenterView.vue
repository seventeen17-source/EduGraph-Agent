<template>
  <div class="page">
    <div class="page-title">
      <div class="page-title-left">
        <div class="page-title-icon">📚</div>
        <div class="page-title-info">
          <h1>知识中心</h1>
          <div class="muted">沉淀每次智能体生成的讲解、导图、练习、脚本和代码案例，方便复习和继续学习。</div>
        </div>
      </div>
      <el-button type="primary" plain :loading="learningStore.loadingResourceCenter" @click="refresh">刷新资源</el-button>
    </div>

    <ErrorAlert :message="learningStore.error" :retry="refresh" />

    <div class="center-layout">
      <el-card class="section-card resource-list-card">
        <template #header>
          <div class="panel-title">
            <span>资源记录</span>
            <el-tag>{{ filteredCenterItems.length }} / {{ learningStore.resourceCenterItems.length }}</el-tag>
          </div>
          <div class="list-toolbar">
            <el-input
              v-model="centerSearch"
              placeholder="搜索资源、题干、代码、讲解正文..."
              size="small"
              clearable
              class="search-input"
              @keyup.enter="searchFullText"
              @clear="searchFullText"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-button size="small" :loading="learningStore.loadingResourceCenter" @click="searchFullText">
              全文搜索
            </el-button>
            <el-select v-model="centerSort" size="small" style="width: 110px">
              <el-option label="最新" value="newest" />
              <el-option label="最早" value="oldest" />
              <el-option label="质量最高" value="quality" />
            </el-select>
            <el-tooltip content="只显示关联了你当前薄弱知识点的资源" placement="top">
              <el-switch
                v-model="filterByWeakPoints"
                size="small"
                active-text="按薄弱点筛选"
                inline-prompt
                @change="searchFullText"
              />
            </el-tooltip>
          </div>
        </template>
        <el-empty v-if="!learningStore.resourceCenterItems.length" description="暂无备课记录，先去 AI 备课台生成一次学习资源">
          <el-button type="primary" @click="$router.push('/resources')">前往 AI 备课台</el-button>
        </el-empty>
        <el-empty v-if="learningStore.resourceCenterItems.length && !filteredCenterItems.length" description="无匹配资源，尝试换个关键词" />
        <div v-else class="resource-list">
          <button
            v-for="item in filteredCenterItems"
            :key="item.id"
            class="resource-item"
            :class="{ active: selectedId === item.id }"
            @click="selectItem(item.id)"
          >
            <div class="item-title">{{ displayNodeLabel(item.center_node_name || item.resolved_uid, '未命名资源') }}</div>
            <div class="item-query">{{ localizeText(item.query) }}</div>
            <div class="item-meta">
              <span>{{ formatDate(item.created_at) }}</span>
              <span>质量 {{ percent(item.quality_score) }}%</span>
            </div>
            <div class="tag-row">
              <el-tag v-for="type in item.resource_types" :key="type" size="small" effect="plain">
                {{ resourceLabel(type) }}
              </el-tag>
            </div>
            <div v-if="item.related_nodes?.length" class="tag-row related-nodes-row">
              <el-tag
                v-for="uid in item.related_nodes.slice(0, 4)"
                :key="uid"
                size="small"
                type="info"
                effect="plain"
              >
                {{ displayNodeLabel(uid) }}
              </el-tag>
              <span v-if="item.related_nodes.length > 4" class="more-nodes">+{{ item.related_nodes.length - 4 }}</span>
            </div>
            <div class="practice-status">
              <span v-if="item.is_practiced" class="practiced-badge">
                ✅ 已练习 · 正确率 {{ percent(item.practice_accuracy ?? 0) }}%
              </span>
              <span v-else class="unpracticed-badge">未练习</span>
            </div>
          </button>
        </div>
      </el-card>

      <div class="resource-detail">
        <el-empty v-if="!detail" description="请选择一条资源记录" />
        <template v-else>
          <el-card class="section-card">
            <div class="detail-head">
              <div>
                <h2>{{ displayNodeLabel(detail.center_node_name || detail.resolved_uid, '学习资源') }}</h2>
                <div class="muted">{{ localizeText(detail.query) }}</div>
              </div>
              <div class="detail-actions">
                <el-tag type="success">质量 {{ percent(detail.quality_score) }}%</el-tag>
                <el-button plain @click="goGenerateAgain">基于该问题再生成</el-button>
              </div>
            </div>
          </el-card>

          <el-tabs v-model="activeTab" type="border-card" class="detail-tabs">
            <el-tab-pane label="讲解文档" name="document">
              <DocumentCard :document="detail.resources.document" />
            </el-tab-pane>
            <el-tab-pane label="思维导图" name="mindmap">
              <MindmapCard :mindmap="detail.resources.mindmap" editable @save="saveMindmap" />
            </el-tab-pane>
            <el-tab-pane :label="`练习题 (${detail.resources.exercises.length})`" name="exercise">
              <div v-if="!detail.resources.exercises.length" class="exercise-empty">
                <el-empty description="本次生成未包含练习题" />
              </div>
              <div v-else class="exercise-summary">
                <div class="exercise-summary-header">
                  <div class="summary-stats">
                    <div class="stat-item">
                      <span class="stat-num">{{ detail.resources.exercises.length }}</span>
                      <span class="stat-label">道题目</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-num">{{ exerciseTypeCount }}</span>
                      <span class="stat-label">种题型</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-num">{{ exerciseDifficultyLabel }}</span>
                      <span class="stat-label">平均难度</span>
                    </div>
                  </div>
                  <el-button
                    type="primary"
                    size="large"
                    @click="startExerciseFromResource"
                  >
                    <el-icon style="margin-right: 6px"><EditPen /></el-icon>
                    立即开始作答
                  </el-button>
                </div>
                <div class="exercise-type-distribution">
                  <el-tag
                    v-for="[type, count] in exerciseTypeDistribution"
                    :key="type"
                    size="large"
                    effect="plain"
                  >
                    {{ typeLabel(type) }} · {{ count }} 道
                  </el-tag>
                </div>
                <div class="exercise-question-list">
                  <div class="list-hint">题目概览（正式作答请在"练习与评估"中进行）：</div>
                  <div
                    v-for="(ex, idx) in detail.resources.exercises"
                    :key="idx"
                    class="exercise-question-item"
                  >
                    <span class="q-num">{{ idx + 1 }}</span>
                    <span class="q-type">{{ typeLabel(ex.type) }}</span>
                    <span class="q-stem">{{ ex.question }}</span>
                  </div>
                </div>
                <div class="exercise-cta">
                  <el-button type="primary" plain @click="startExerciseFromResource">
                    前往练习与评估作答
                  </el-button>
                  <span class="muted">作答后自动记录错题、更新画像</span>
                </div>
              </div>
            </el-tab-pane>
            <el-tab-pane label="视频脚本" name="video">
              <VideoScriptCard :script="detail.resources.video_script" />
            </el-tab-pane>
            <el-tab-pane label="代码案例" name="code">
              <CodeCaseCard :code-case="detail.resources.code_case" />
            </el-tab-pane>
            <el-tab-pane label="教学图片" name="image">
              <ImageCard :image="detail.resources.image || detail.resources.document?.illustrations?.[0] || null" />
            </el-tab-pane>
            <el-tab-pane label="证据与质量" name="evidence">
              <div class="evidence-grid">
                <EvidencePanel :evidence="detail.evidence" />
                <el-card class="section-card">
                  <template #header>
                    <div class="panel-title">
                      <span>生成质量</span>
                      <el-tag :type="detail.quality_report.grounded ? 'success' : 'warning'">
                        {{ detail.quality_report.grounded ? '证据充分' : '需要复核' }}
                      </el-tag>
                    </div>
                  </template>
                  <el-progress :percentage="percent(detail.quality_report.score)" />
                  <div class="tag-row quality-tags">
                    <el-tag v-for="source in detail.quality_report.source_uids" :key="source" effect="plain">
                      {{ displaySourceLabel(source, '证据来源') }}
                    </el-tag>
                  </div>
                  <el-alert
                    v-for="warning in detail.quality_report.warnings"
                    :key="warning"
                    type="warning"
                    :title="localizeText(warning)"
                    :closable="false"
                    show-icon
                  />
                </el-card>
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { LocationQueryRaw } from 'vue-router'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import ErrorAlert from '@/components/common/ErrorAlert.vue'
import EvidencePanel from '@/components/graphrag/EvidencePanel.vue'
import CodeCaseCard from '@/components/resources/CodeCaseCard.vue'
import DocumentCard from '@/components/resources/DocumentCard.vue'
import ImageCard from '@/components/resources/ImageCard.vue'
import MindmapCard from '@/components/resources/MindmapCard.vue'
import VideoScriptCard from '@/components/resources/VideoScriptCard.vue'
import { EditPen } from '@element-plus/icons-vue'
import { useLearningStore } from '@/stores/learning'
import { useProfileStore } from '@/stores/profile'
import { displayNodeLabel, displaySourceLabel, localizeText, percent, resourceLabel, formatDate } from '@/utils/format'

const typeLabel = (type?: string) => {
  const map: Record<string, string> = {
    choice: '选择题',
    short_answer: '简答题',
    coding: '编程题',
    case_analysis: '案例题',
  }
  return map[type || ''] || type || '未知'
}

const exerciseTypeDistribution = computed(() => {
  const exercises = detail.value?.resources?.exercises || []
  const map = new Map<string, number>()
  for (const ex of exercises) {
    const t = ex.type || 'unknown'
    map.set(t, (map.get(t) || 0) + 1)
  }
  return Array.from(map.entries())
})

const exerciseTypeCount = computed(() => exerciseTypeDistribution.value.length)

const exerciseDifficultyLabel = computed(() => {
  const exercises = detail.value?.resources?.exercises || []
  if (!exercises.length) return '-'
  const avg = exercises.reduce((s, e) => s + (e.difficulty || 3), 0) / exercises.length
  if (avg >= 4.5) return '★★★★★'
  if (avg >= 3.5) return '★★★★'
  if (avg >= 2.5) return '★★★'
  if (avg >= 1.5) return '★★'
  return '★'
})

const router = useRouter()
const route = useRoute()
const learningStore = useLearningStore()
const profileStore = useProfileStore()
const activeTab = ref('document')
const selectedId = ref<string | null>(null)
const centerSearch = ref('')
const centerSort = ref<'newest' | 'oldest' | 'quality'>('newest')
const filterByWeakPoints = ref(false)
const validTabs = ['document', 'mindmap', 'exercise', 'video', 'code', 'image', 'evidence']

const filteredCenterItems = computed(() => {
  let items = learningStore.resourceCenterItems
  // 搜索
  const q = centerSearch.value.trim().toLowerCase()
  if (q) {
    items = items.filter(i =>
      (i.center_node_name || '').toLowerCase().includes(q) ||
      (i.query || '').toLowerCase().includes(q) ||
      (i.resource_types || []).some(t => t.toLowerCase().includes(q))
    )
  }
  // 排序
  const sorted = [...items]
  sorted.sort((a, b) => {
    if (centerSort.value === 'quality') return (b.quality_score || 0) - (a.quality_score || 0)
    const ta = new Date(a.created_at).getTime()
    const tb = new Date(b.created_at).getTime()
    return centerSort.value === 'newest' ? tb - ta : ta - tb
  })
  return sorted
})
const detail = computed(() => {
  const record = learningStore.selectedResourceRecord
  if (!record || record.id !== selectedId.value) return null
  return record
})

async function refresh() {
  if (!profileStore.profile) await profileStore.initFromAuth()
  await learningStore.loadResourceCenter(profileStore.studentId, centerSearch.value.trim(), filterByWeakPoints.value)
  const routeRecordId = typeof route.query.record_id === 'string' ? route.query.record_id : ''
  const routeRecordVisible = routeRecordId
    ? learningStore.resourceCenterItems.some((item) => item.id === routeRecordId)
    : false
  if (routeRecordId && routeRecordVisible) {
    await selectItem(routeRecordId, { syncRoute: false })
    return
  }
  const currentStillVisible = selectedId.value
    ? learningStore.resourceCenterItems.some((item) => item.id === selectedId.value)
    : false
  const targetId = currentStillVisible
    ? selectedId.value
    : learningStore.resourceCenterItems[0]?.id
  if (targetId) {
    await selectItem(targetId)
  }
}

async function searchFullText() {
  selectedId.value = null
  await refresh()
}

async function selectItem(id: string, options: { syncRoute?: boolean } = {}) {
  const syncRoute = options.syncRoute ?? true
  selectedId.value = id
  learningStore.selectedResourceRecord = null
  await learningStore.loadResourceRecord(id)
  activeTab.value = preferredTab()
  if (syncRoute && route.query.record_id !== id) {
    const nextQuery: LocationQueryRaw = { ...route.query, record_id: id }
    delete nextQuery.tab
    await router.replace({ path: route.path, query: nextQuery })
  }
}

function preferredTab() {
  const routeTab = typeof route.query.tab === 'string' ? route.query.tab : ''
  if (validTabs.includes(routeTab)) {
    return routeTab
  }
  const resources = detail.value?.resources
  if (!resources) return 'document'
  if (resources.document) return 'document'
  if (resources.mindmap) return 'mindmap'
  if (resources.exercises?.length) return 'exercise'
  if (resources.video_script) return 'video'
  if (resources.code_case) return 'code'
  if (resources.image) return 'image'
  return 'evidence'
}

async function saveMindmap(payload: { title: string; content: string }) {
  if (!detail.value) return
  await learningStore.saveResourceMindmap(detail.value.id, payload)
  ElMessage.success('思维导图已保存到知识中心')
}

function goGenerateAgain() {
  router.push({ path: '/resources', query: { query: detail.value?.query || '' } })
}

function startExerciseFromResource() {
  if (!detail.value?.resources.exercises.length) {
    ElMessage.warning('这条资源记录没有可练习的题目')
    return
  }
  router.push({
    path: '/exercise',
    query: {
      resource_id: detail.value.id,
      node_id: detail.value.resolved_uid || '',
    },
  })
}

onMounted(refresh)

watch(
  () => route.query.record_id,
  async (recordId) => {
    if (typeof recordId === 'string' && recordId && recordId !== selectedId.value) {
      await selectItem(recordId, { syncRoute: false })
    } else if (typeof recordId === 'string' && recordId && recordId === selectedId.value) {
      activeTab.value = preferredTab()
    }
  }
)

watch(
  () => route.query.tab,
  () => {
    if (detail.value) activeTab.value = preferredTab()
  }
)
</script>

<style scoped>
.center-layout {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 16px;
}

.resource-list-card {
  align-self: start;
}

.resource-list {
  display: grid;
  gap: 10px;
  max-height: calc(100vh - 230px);
  overflow: auto;
  padding-right: 4px;
}

.resource-item {
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  border-radius: 12px;
  padding: 16px;
  background: #fff;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.resource-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
  border-color: rgba(99, 102, 241, 0.2);
}

.resource-item.active {
  background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
  border-color: #6366f1;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.15);
}

.item-title {
  font-weight: 600;
  font-size: 15px;
  color: #1e293b;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-query {
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #94a3b8;
  font-size: 12px;
  margin-bottom: 10px;
}

.item-meta span:last-child {
  font-weight: 500;
  color: #6366f1;
}

.resource-detail {
  min-width: 0;
}

.detail-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.detail-head h2 {
  margin: 0 0 6px;
  font-size: 21px;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-tabs {
  margin-top: 16px;
}

.evidence-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
}

.quality-tags {
  margin: 14px 0;
}

/* 练习题摘要样式 */
.exercise-summary {
  padding: 8px 0;
}

.exercise-summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.1);
}

.summary-stats {
  display: flex;
  gap: 32px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-num {
  font-size: 28px;
  font-weight: 700;
  color: #6366f1;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: #94a3b8;
}

.exercise-type-distribution {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.exercise-question-list {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
}

.list-hint {
  padding: 10px 16px;
  background: #f8fafc;
  font-size: 13px;
  color: #64748b;
  border-bottom: 1px solid #e2e8f0;
}

.exercise-question-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  transition: background 0.2s;
}

.exercise-question-item:last-child {
  border-bottom: none;
}

.exercise-question-item:hover {
  background: #f8fafc;
}

.q-num {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #6366f1;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.q-type {
  flex-shrink: 0;
  font-size: 12px;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
  padding: 2px 8px;
  border-radius: 4px;
}

.q-stem {
  font-size: 13px;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.exercise-cta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed #e2e8f0;
}

.exercise-empty {
  padding: 40px 0;
}

.related-nodes-row {
  margin-top: 6px;
  gap: 4px;
  flex-wrap: wrap;
}

.more-nodes {
  font-size: 11px;
  color: #94a3b8;
  align-self: center;
}

.practice-status {
  margin-top: 8px;
  font-size: 12px;
}

.practiced-badge {
  color: #10b981;
  font-weight: 500;
}

.unpracticed-badge {
  color: #94a3b8;
}
</style>
