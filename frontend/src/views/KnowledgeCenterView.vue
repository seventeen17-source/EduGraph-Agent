<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>知识中心</h1>
        <div class="muted">沉淀每次智能体生成的讲解、导图、练习、脚本和代码案例，方便复习和继续学习。</div>
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
            <el-input v-model="centerSearch" placeholder="搜索资源..." size="small" clearable class="search-input">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-select v-model="centerSort" size="small" style="width: 110px">
              <el-option label="最新" value="newest" />
              <el-option label="最早" value="oldest" />
              <el-option label="质量最高" value="quality" />
            </el-select>
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
            <div class="item-title">{{ item.center_node_name || uidLabel(item.resolved_uid) || '未命名资源' }}</div>
            <div class="item-query">{{ item.query }}</div>
            <div class="item-meta">
              <span>{{ formatDate(item.created_at) }}</span>
              <span>质量 {{ percent(item.quality_score) }}%</span>
            </div>
            <div class="tag-row">
              <el-tag v-for="type in item.resource_types" :key="type" size="small" effect="plain">
                {{ resourceLabel(type) }}
              </el-tag>
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
                <h2>{{ detail.center_node_name || uidLabel(detail.resolved_uid) || '学习资源' }}</h2>
                <div class="muted">{{ detail.query }}</div>
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
            <el-tab-pane label="练习题" name="exercise">
              <ExerciseCard :exercises="detail.resources.exercises" :submitted="false" :correct-count="0" :correct-nodes="[]" :weak-nodes="[]" :uid-label-map="{}" @submit-round="submitExerciseRound" />
            </el-tab-pane>
            <el-tab-pane label="视频脚本" name="video">
              <VideoScriptCard :script="detail.resources.video_script" />
            </el-tab-pane>
            <el-tab-pane label="代码案例" name="code">
              <CodeCaseCard :code-case="detail.resources.code_case" />
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
                      {{ uidLabel(source) || source }}
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
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import ErrorAlert from '@/components/common/ErrorAlert.vue'
import EvidencePanel from '@/components/graphrag/EvidencePanel.vue'
import CodeCaseCard from '@/components/resources/CodeCaseCard.vue'
import DocumentCard from '@/components/resources/DocumentCard.vue'
import ExerciseCard from '@/components/resources/ExerciseCard.vue'
import MindmapCard from '@/components/resources/MindmapCard.vue'
import VideoScriptCard from '@/components/resources/VideoScriptCard.vue'
import { useLearningStore } from '@/stores/learning'
import { useProfileStore } from '@/stores/profile'
import type { GeneratedExercise } from '@/types/resources'
import { localizeText, percent, resourceLabel, uidLabel } from '@/utils/format'

const router = useRouter()
const route = useRoute()
const learningStore = useLearningStore()
const profileStore = useProfileStore()
const activeTab = ref('document')
const selectedId = ref<string | null>(null)
const centerSearch = ref('')
const centerSort = ref<'newest' | 'oldest' | 'quality'>('newest')

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
const detail = computed(() => learningStore.selectedResourceRecord)

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间未知'
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function refresh() {
  if (!profileStore.profile) await profileStore.initFromAuth()
  await learningStore.loadResourceCenter(profileStore.studentId)
  const routeRecordId = typeof route.query.record_id === 'string' ? route.query.record_id : ''
  if (routeRecordId) {
    await selectItem(routeRecordId)
    return
  }
  if (!selectedId.value && learningStore.resourceCenterItems.length) {
    await selectItem(learningStore.resourceCenterItems[0].id)
  }
}

async function selectItem(id: string) {
  selectedId.value = id
  await learningStore.loadResourceRecord(id)
  activeTab.value = preferredTab()
}

function preferredTab() {
  const routeTab = typeof route.query.tab === 'string' ? route.query.tab : ''
  if (['document', 'mindmap', 'exercise', 'video', 'code', 'evidence'].includes(routeTab)) {
    return routeTab
  }
  const resources = detail.value?.resources
  if (!resources) return 'document'
  if (resources.exercises?.length) return 'exercise'
  if (resources.document) return 'document'
  if (resources.mindmap) return 'mindmap'
  if (resources.video_script) return 'video'
  if (resources.code_case) return 'code'
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

async function submitExerciseRound(results: Array<{ exercise: GeneratedExercise; answer: string }>) {
  const fallbackNode = detail.value?.resolved_uid || learningStore.currentNodeId
  const attempts = results
    .map(({ exercise, answer }) => {
      const targetNode = exercise.related_node_id || fallbackNode
      if (!targetNode) return null
      const ans = String(answer || '').trim()
      const expected = String(exercise.answer?.correct || '')
      const isCorrect = Boolean(ans && expected && ans === expected)
      return {
        exercise_id: exercise.title || 'resource_center_exercise',
        exercise_title: exercise.title,
        exercise_type: exercise.type,
        related_node_id: targetNode,
        related_node_name: uidLabel(targetNode) || targetNode,
        exercise_snapshot: { ...exercise },
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
    .filter((item): item is NonNullable<typeof item> => Boolean(item))

  if (!attempts.length) {
    ElMessage.warning('未找到关联的知识点，无法记录练习结果')
    return
  }
  await profileStore.recordExerciseSession({
    round_id: `resource_center_${Date.now()}`,
    source_type: 'resource_center',
    source_id: detail.value?.id || '',
    target_node_id: fallbackNode || '',
    target_node_name: uidLabel(fallbackNode) || fallbackNode || '',
    title: `${uidLabel(fallbackNode) || detail.value?.query || '资源中心'}练习`,
    duration_seconds: 0,
    started_at: null,
    attempts
  })
  ElMessage.success('本轮练习结果已写入画像')
}

onMounted(refresh)

watch(
  () => route.query.record_id,
  async (recordId) => {
    if (typeof recordId === 'string' && recordId && recordId !== selectedId.value) {
      await selectItem(recordId)
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
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
  cursor: pointer;
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease;
}

.resource-item:hover,
.resource-item.active {
  border-color: #409eff;
  box-shadow: 0 8px 20px rgba(64, 158, 255, 0.12);
}

.item-title {
  font-weight: 700;
  margin-bottom: 6px;
}

.item-query {
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 8px;
}

.item-meta {
  display: flex;
  justify-content: space-between;
  color: #7a8494;
  font-size: 12px;
  margin-bottom: 8px;
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
</style>
