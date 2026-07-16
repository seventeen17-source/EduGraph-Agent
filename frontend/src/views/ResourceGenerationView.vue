<template>
  <div class="page">
    <div class="page-title">
      <div class="page-title-left">
        <div class="page-title-icon">🎓</div>
        <div class="page-title-info">
          <h1>AI 备课台</h1>
          <div class="muted">基于图谱增强检索证据包，按需生成讲解、导图、练习、视频脚本和代码案例。</div>
        </div>
      </div>
    </div>

    <ErrorAlert :message="learningStore.error" :retry="generate" />

    <el-card class="section-card control-card">
      <div v-if="!query && !response" class="empty-guide">
        <div class="guide-icon">🎓</div>
        <div class="guide-title">AI 学习资源生成</div>
        <div class="guide-desc">输入知识点名称或自然语言问题，选择生成模式，按需生成讲解、导图、练习、视频脚本和代码案例。</div>
        <div class="guide-modes">
          <div
            v-for="mode in generateModes"
            :key="mode.label"
            class="guide-mode-card"
            :class="{ active: selectedMode === mode.label }"
            @click="selectMode(mode.label)"
          >
            <span class="mode-icon">{{ mode.icon }}</span>
            <span class="mode-label">{{ mode.label }}</span>
          </div>
        </div>
      </div>
      <div class="resource-controls">
        <div class="mode-selector">
          <span
            v-for="mode in generateModes"
            :key="mode.label"
            class="mode-chip"
            :class="{ active: selectedMode === mode.label }"
            @click="selectMode(mode.label)"
          >
            {{ mode.icon }} {{ mode.label }}
          </span>
        </div>
        <el-input v-model="query" placeholder="输入知识点名称或自然语言问题" />
        <el-checkbox-group v-model="selectedTypes" class="type-checks">
          <el-checkbox-button
            v-for="rt in allResourceTypes"
            :key="rt.value"
            :label="rt.value"
            :disabled="generatedTypes.has(rt.value)"
          >
            {{ rt.label }}
            <el-tag v-if="generatedTypes.has(rt.value)" size="small" type="success" effect="dark" class="type-badge">
              ✅
            </el-tag>
            <el-tag v-else-if="learningStore.loadingResources && selectedTypes.includes(rt.value)" size="small" type="warning" effect="dark" class="type-badge">
              🔄
            </el-tag>
          </el-checkbox-button>
        </el-checkbox-group>
        <div class="generate-actions">
          <el-button type="primary" :loading="learningStore.loadingResources" :disabled="!selectedTypes.length || !query.trim()" @click="generate">
            {{ generatedTypes.size ? `生成选中资源（${selectedTypes.length}项）` : '开始生成' }}
          </el-button>
          <el-button v-if="generatedTypes.size" plain @click="resetGeneration">重置重新生成全部</el-button>
        </div>
      </div>
    </el-card>

    <AgentProgressPanel :statuses="learningStore.agentStatuses" />

    <div v-if="learningStore.loadingResources" class="resource-loading">
      <LoadingSkeleton :rows="10" />
    </div>

    <!-- 解析质量提示 -->
    <el-alert
      v-if="response && response.resolution_quality !== 'exact'"
      class="resolution-alert"
      :type="response.resolution_quality === 'none' ? 'warning' : 'info'"
      :closable="true"
      show-icon
    >
      <template #title>
        {{ response.resolution_quality === 'none' ? '未找到精确匹配' : '已自动匹配最接近的知识点' }}
      </template>
      <p>{{ response.resolution_notice }}</p>
      <div v-if="response.suggested_alternatives?.length" class="alt-tags">
        <span class="alt-label">建议尝试：</span>
        <el-tag
          v-for="alt in response.suggested_alternatives.slice(0, 5)"
          :key="alt.uid"
          type="primary"
          effect="plain"
          class="alt-tag"
          @click="query = alt.name; generate()"
        >
          {{ alt.name }}
        </el-tag>
      </div>
    </el-alert>

    <!-- 失败资源自修复：列出失败原因和重试按钮 -->
    <div v-if="response && failedResourceTypes.length" class="failed-resources-section">
      <el-alert
        v-for="rt in failedResourceTypes"
        :key="rt.value"
        type="error"
        :closable="false"
        show-icon
        class="failed-resource-alert"
      >
        <template #title>
          <div class="failed-alert-title">
            <span class="failed-label">⚠️ {{ rt.label }}生成失败</span>
            <el-button
              type="primary"
              size="small"
              :loading="retrying.has(rt.value)"
              @click="retryResource(rt)"
            >
              重试
            </el-button>
          </div>
        </template>
        <div class="failed-alert-body">
          <span class="failed-reason-label">失败原因：</span>
          <span class="failed-reason-text">{{ getFailureReason(rt.value) }}</span>
        </div>
      </el-alert>
    </div>

    <div v-if="response" class="resource-layout">
      <div class="resource-main">
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="讲解文档" name="document">
            <DocumentCard :document="response.resources.document" />
            <div v-if="isResourceFailed('document')" class="tab-retry-bar">
              <el-tag type="danger" size="small">生成失败</el-tag>
              <span class="tab-retry-reason">{{ getFailureReason('document') }}</span>
              <el-button
                type="primary"
                size="small"
                :loading="retrying.has('document')"
                @click="retryResource(allResourceTypes[0])"
              >
                重试生成
              </el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="思维导图" name="mindmap">
            <MindmapCard :mindmap="response.resources.mindmap" />
            <div v-if="isResourceFailed('mindmap')" class="tab-retry-bar">
              <el-tag type="danger" size="small">生成失败</el-tag>
              <span class="tab-retry-reason">{{ getFailureReason('mindmap') }}</span>
              <el-button
                type="primary"
                size="small"
                :loading="retrying.has('mindmap')"
                @click="retryResource(allResourceTypes[1])"
              >
                重试生成
              </el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="练习题" name="exercise">
            <div class="exercise-preview-head">
              <div>
                <h3>题目预览</h3>
                <div class="muted">AI 备课台负责生成和沉淀资源。正式作答、评分、错题记录和画像更新请进入“练习与评估”。</div>
              </div>
              <el-button
                type="primary"
                :disabled="!response.resources.exercises.length"
                @click="startExerciseFromGenerated"
              >
                去练习与评估作答
              </el-button>
            </div>
            <ExerciseCard
              :exercises="response.resources.exercises"
              readonly
              :submitted="false"
              :correct-count="0"
              :correct-nodes="[]"
              :weak-nodes="[]"
              :uid-label-map="{}"
            />
            <div v-if="isResourceFailed('exercise')" class="tab-retry-bar">
              <el-tag type="danger" size="small">生成失败</el-tag>
              <span class="tab-retry-reason">{{ getFailureReason('exercise') }}</span>
              <el-button
                type="primary"
                size="small"
                :loading="retrying.has('exercise')"
                @click="retryResource(allResourceTypes[2])"
              >
                重试生成
              </el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="视频脚本" name="video">
            <VideoScriptCard :script="response.resources.video_script" />
            <div v-if="isResourceFailed('video_script')" class="tab-retry-bar">
              <el-tag type="danger" size="small">生成失败</el-tag>
              <span class="tab-retry-reason">{{ getFailureReason('video_script') }}</span>
              <el-button
                type="primary"
                size="small"
                :loading="retrying.has('video_script')"
                @click="retryResource(allResourceTypes[3])"
              >
                重试生成
              </el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="代码案例" name="code">
            <CodeCaseCard :code-case="response.resources.code_case" />
            <div v-if="isResourceFailed('code_case')" class="tab-retry-bar">
              <el-tag type="danger" size="small">生成失败</el-tag>
              <span class="tab-retry-reason">{{ getFailureReason('code_case') }}</span>
              <el-button
                type="primary"
                size="small"
                :loading="retrying.has('code_case')"
                @click="retryResource(allResourceTypes[4])"
              >
                重试生成
              </el-button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="教学图片" name="image">
            <ImageCard :image="response.resources.image || response.resources.document?.illustrations?.[0] || null" />
            <div v-if="isResourceFailed('image')" class="tab-retry-bar">
              <el-tag type="danger" size="small">生成失败</el-tag>
              <span class="tab-retry-reason">{{ getFailureReason('image') }}</span>
              <el-button
                type="primary"
                size="small"
                :loading="retrying.has('image')"
                @click="retryResource(allResourceTypes[5])"
              >
                重试生成
              </el-button>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <div class="resource-side">
        <EvidencePanel :evidence="response.evidence" />
        <el-card class="section-card quality-card">
          <template #header>
            <div class="panel-title">
              <span>质量报告</span>
              <el-tag :type="response.quality_report.grounded ? 'success' : 'warning'">
                {{ response.quality_report.grounded ? '证据充分' : '需复核' }}
              </el-tag>
            </div>
          </template>
          <el-progress :percentage="percent(response.quality_report.score)" />
          <div class="quality-breakdown">
            <div v-for="item in qualityDimensions" :key="item.key" class="quality-dimension">
              <span>{{ item.label }}</span>
              <el-progress :percentage="percent(item.value)" :show-text="false" :stroke-width="5" />
              <strong>{{ Math.round((item.value || 0) * 100) }}%</strong>
            </div>
          </div>
          <div class="tag-row quality-tags">
            <el-tag v-for="source in response.quality_report.source_uids" :key="source" effect="plain">
              {{ sourceLabelForReport(source) }}
            </el-tag>
          </div>
          <el-alert
            v-for="warning in response.quality_report.warnings"
            :key="warning"
            type="warning"
            :title="localizeText(warning)"
            :closable="false"
            show-icon
          />
          <el-alert
            v-for="reason in response.quality_report.weak_reasons || []"
            :key="reason"
            type="info"
            :title="localizeText(reason)"
            :closable="false"
            show-icon
          />
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import ErrorAlert from '@/components/common/ErrorAlert.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import EvidencePanel from '@/components/graphrag/EvidencePanel.vue'
import AgentProgressPanel from '@/components/resources/AgentProgressPanel.vue'
import CodeCaseCard from '@/components/resources/CodeCaseCard.vue'
import DocumentCard from '@/components/resources/DocumentCard.vue'
import ExerciseCard from '@/components/resources/ExerciseCard.vue'
import ImageCard from '@/components/resources/ImageCard.vue'
import MindmapCard from '@/components/resources/MindmapCard.vue'
import VideoScriptCard from '@/components/resources/VideoScriptCard.vue'
import { retryResourceType } from '@/api/agents'
import { useLearningStore } from '@/stores/learning'
import { useProfileStore } from '@/stores/profile'
import type { ResourceType } from '@/types/profile'
import type { AgentTraceItem } from '@/types/resources'
import { displayNodeLabel, displaySourceLabel, localizeText, percent } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const profileStore = useProfileStore()
const learningStore = useLearningStore()

const query = ref(
  (() => {
    // 优先用 query，只有 node_id 时显示中文知识点名
    const q = route.query.query as string
    const nid = route.query.node_id as string
    return q || displayNodeLabel(nid, '') || ''
  })()
)
const nodeId = ref((route.query.node_id as string) || '')
const allResourceTypes = [
  { value: 'document' as const, label: '讲解文档' },
  { value: 'mindmap' as const, label: '思维导图' },
  { value: 'exercise' as const, label: '练习题' },
  { value: 'video_script' as const, label: '视频脚本' },
  { value: 'code_case' as const, label: '代码案例' },
  { value: 'image' as const, label: '教学图片' },
]

const generateModes = [
  { label: '快速讲解', types: ['document'] as ResourceType[], icon: '📄' },
  { label: '做题巩固', types: ['exercise'] as ResourceType[], icon: '📝' },
  { label: '图解理解', types: ['mindmap'] as ResourceType[], icon: '🧠' },
  { label: '图片示意', types: ['image'] as ResourceType[], icon: '🖼️' },
  { label: '编程实践', types: ['code_case'] as ResourceType[], icon: '💻' },
  { label: '全套学习包', types: ['document', 'mindmap', 'exercise', 'video_script', 'code_case', 'image'] as ResourceType[], icon: '📦' },
]
const selectedMode = ref<string>('')

function selectMode(modeLabel: string) {
  const mode = generateModes.find(m => m.label === modeLabel)
  if (mode) {
    selectedMode.value = modeLabel
    selectedTypes.value = [...mode.types]
  }
}

const selectedTypes = ref<ResourceType[]>([])
const activeTab = ref('document')
const generatedTypes = ref(new Set<string>())
const retrying = ref<Set<string>>(new Set())
const response = computed(() => learningStore.resourceResponse)

// 资源类型 → Agent 名称映射
const resourceAgentMap: Record<string, string> = {
  document: 'DocumentAgent',
  mindmap: 'MindmapAgent',
  exercise: 'ExerciseAgent',
  video_script: 'VideoScriptAgent',
  code_case: 'CodeAgent',
  image: 'ImageAgent',
}

// 获取某资源类型对应的 Agent 执行轨迹
function getAgentTrace(resourceType: string): AgentTraceItem | undefined {
  const agentName = resourceAgentMap[resourceType]
  return response.value?.agent_trace.find((t) => t.agent === agentName)
}

// 判断某资源类型是否失败（agent status 为 failed 或 error）
function isResourceFailed(resourceType: string): boolean {
  const agentName = resourceAgentMap[resourceType]
  if (!agentName) return false
  const status = learningStore.agentStatuses[agentName]
  return status === 'failed' || status === 'error'
}

// 获取失败原因
function getFailureReason(resourceType: string): string {
  const trace = getAgentTrace(resourceType)
  return localizeText(trace?.summary || '生成失败，请重试')
}

// 失败资源列表
const failedResourceTypes = computed(() => {
  return allResourceTypes.filter((rt) => isResourceFailed(rt.value))
})

const qualityDimensions = computed(() => {
  const report = response.value?.quality_report
  if (!report) return []
  return [
    { key: 'coverage', label: '覆盖度', value: report.coverage_score || 0 },
    { key: 'relevance', label: '相关性', value: report.relevance_score || 0 },
    { key: 'grounding', label: '来源可信', value: report.grounding_score || 0 },
    { key: 'personalFit', label: '个性化', value: report.personal_fit_score || 0 },
  ]
})

// 监听新备课内容，标记已生成的类型
watch(() => response.value?.resources, (res) => {
  if (!res) return
  const types: Record<string, boolean> = {
    document: !!res.document,
    mindmap: !!res.mindmap,
    exercise: !!(res.exercises?.length),
    video_script: !!res.video_script,
    code_case: !!res.code_case,
    image: !!res.image || !!res.document?.illustrations?.length,
  }
  for (const [k, v] of Object.entries(types)) {
    if (v) generatedTypes.value.add(k)
  }
})

async function generate() {
  if (!selectedTypes.value.length) return
  if (!query.value.trim()) {
    ElMessage.warning('请先输入知识点或学习问题')
    return
  }
  if (!profileStore.profile) await profileStore.initFromAuth()
  await learningStore.generateForQuery(query.value, nodeId.value, profileStore.studentProfileInput, selectedTypes.value, profileStore.studentId)
  ElMessage.success('AI 备课完成')
}

function resetGeneration() {
  generatedTypes.value.clear()
  selectedTypes.value = []
  selectedMode.value = ''
}

// 重试单个资源类型：调用 retryResourceType，仅更新对应类型的资源
async function retryResource(rt: { value: ResourceType; label: string }) {
  const resourceId = response.value?.resource_record_id
  if (!resourceId) {
    ElMessage.warning('资源记录ID缺失，无法重试')
    return
  }
  retrying.value = new Set(retrying.value).add(rt.value)
  try {
    const updated = await retryResourceType({
      resource_id: resourceId,
      resource_type: rt.value,
      student_id: profileStore.studentId || '',
    })
    if (response.value) {
      const newResources = { ...response.value.resources }
      if (rt.value === 'exercise') {
        newResources.exercises = Array.isArray(updated.resource) ? updated.resource : []
      } else if (rt.value === 'document') {
        newResources.document = updated.resource && !Array.isArray(updated.resource)
          ? updated.resource as typeof newResources.document
          : null
      } else if (rt.value === 'mindmap') {
        newResources.mindmap = updated.resource && !Array.isArray(updated.resource)
          ? updated.resource as typeof newResources.mindmap
          : null
      } else if (rt.value === 'video_script') {
        newResources.video_script = updated.resource && !Array.isArray(updated.resource)
          ? updated.resource as typeof newResources.video_script
          : null
      } else if (rt.value === 'code_case') {
        newResources.code_case = updated.resource && !Array.isArray(updated.resource)
          ? updated.resource as typeof newResources.code_case
          : null
      } else if (rt.value === 'image') {
        newResources.image = updated.resource && !Array.isArray(updated.resource)
          ? updated.resource as typeof newResources.image
          : null
      }
      // 更新该资源类型对应 Agent 的 trace
      const agentName = resourceAgentMap[rt.value]
      const newTrace = [...response.value.agent_trace]
      const traceIdx = newTrace.findIndex((t) => t.agent === agentName)
      const updatedTrace = updated?.agent_trace?.find((t) => t.agent === agentName)
      const traceItem: AgentTraceItem = updatedTrace || { agent: agentName, status: 'done', summary: '重试成功' }
      if (traceIdx >= 0) {
        newTrace[traceIdx] = traceItem
      } else {
        newTrace.push(traceItem)
      }
      learningStore.resourceResponse = {
        ...response.value,
        resources: newResources,
        agent_trace: newTrace,
        quality_report: updated.quality_report || response.value.quality_report,
      }
      learningStore.agentStatuses[agentName] = 'done'
      // 已生成类型集合中加上该类型
      generatedTypes.value.add(rt.value)
      ElMessage.success(`${rt.label} 重试成功`)
    }
  } catch (error: any) {
    ElMessage.error(`${rt.label} 重试失败：${error?.displayMessage || error?.message || '请稍后重试'}`)
  } finally {
    const next = new Set(retrying.value)
    next.delete(rt.value)
    retrying.value = next
  }
}

function startExerciseFromGenerated() {
  const recordId = response.value?.resource_record_id
  if (!response.value?.resources.exercises.length) {
    ElMessage.warning('当前没有可练习的题目')
    return
  }
  if (!recordId) {
    ElMessage.warning('资源尚未写入知识中心，无法创建正式练习')
    return
  }
  router.push({
    path: '/exercise',
    query: {
      resource_id: recordId,
      node_id: response.value?.resolved_uid || '',
    },
  })
}

function sourceLabelForReport(source: string) {
  return displaySourceLabel(source, '证据来源')
}

onMounted(async () => {
  if (!profileStore.profile) await profileStore.initFromAuth()
})
</script>

<style scoped>
.control-card {
  margin-bottom: 16px;
}

.resource-controls {
  display: grid;
  grid-template-columns: minmax(180px, auto) minmax(260px, 1fr) auto auto;
  gap: 12px;
  align-items: center;
}

.resource-loading {
  margin-top: 16px;
}

.resolution-alert {
  margin-bottom: 16px;
}

.resolution-alert p {
  margin: 8px 0;
  font-size: 14px;
  color: #475569;
  line-height: 1.5;
}

.alt-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.alt-label {
  font-size: 13px;
  color: #64748b;
}

.alt-tag {
  cursor: pointer;
}

.alt-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
}

.resource-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 16px;
  margin-top: 16px;
}

.resource-side {
  display: grid;
  align-content: start;
  gap: 16px;
}

.quality-card {
  min-height: 180px;
}

.quality-breakdown {
  display: grid;
  gap: 8px;
  margin: 12px 0;
}

.quality-dimension {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) 42px;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #64748b;
}

.quality-dimension strong {
  color: #334155;
  text-align: right;
}

.quality-tags {
  margin: 14px 0;
}

.exercise-preview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.exercise-preview-head h3 {
  margin: 0 0 6px;
  font-size: 18px;
}

.empty-guide {
  text-align: center;
  padding: 48px 24px;
}
.guide-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.guide-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
}
.guide-desc {
  color: var(--el-text-color-secondary);
  max-width: 500px;
  margin: 0 auto 24px;
  line-height: 1.6;
}
.guide-modes {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}
.guide-mode-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 20px;
  border: 2px solid var(--el-border-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.guide-mode-card:hover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.guide-mode-card.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.mode-icon {
  font-size: 24px;
}
.mode-label {
  font-size: 13px;
  font-weight: 500;
}

.mode-selector {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.mode-chip {
  padding: 6px 14px;
  border: 1px solid var(--el-border-color);
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.mode-chip:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}
.mode-chip.active {
  background: var(--el-color-primary);
  color: white;
  border-color: var(--el-color-primary);
}

/* ===== 失败资源自修复 ===== */
.failed-resources-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
}

.failed-resource-alert {
  margin: 0;
}

.failed-alert-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}

.failed-label {
  font-weight: 600;
  color: var(--el-color-danger);
}

.failed-alert-body {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 6px;
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
}

.failed-reason-label {
  flex-shrink: 0;
  color: #64748b;
}

.failed-reason-text {
  flex: 1;
  word-break: break-word;
}

.tab-retry-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid var(--el-color-danger-light-5);
  background: var(--el-color-danger-light-9);
  border-radius: 8px;
}

.tab-retry-reason {
  flex: 1;
  font-size: 12px;
  color: #b91c1c;
  word-break: break-word;
}
</style>
