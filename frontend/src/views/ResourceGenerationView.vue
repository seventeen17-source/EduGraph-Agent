<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>AI 备课台</h1>
        <div class="muted">基于图谱增强检索证据包，按需生成讲解、导图、练习、视频脚本和代码案例。</div>
      </div>
    </div>

    <ErrorAlert :message="learningStore.error" :retry="generate" />

    <el-card class="section-card control-card">
      <div class="resource-controls">
        <el-input v-model="query" placeholder="输入知识点名称或自然语言问题" />
        <div class="type-checks">
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
        </div>
        <div class="generate-actions">
          <el-button type="primary" :loading="learningStore.loadingResources" :disabled="!selectedTypes.length" @click="generate">
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

    <div v-if="response" class="resource-layout">
      <div class="resource-main">
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="讲解文档" name="document">
            <DocumentCard :document="response.resources.document" />
          </el-tab-pane>
          <el-tab-pane label="思维导图" name="mindmap">
            <MindmapCard :mindmap="response.resources.mindmap" />
          </el-tab-pane>
          <el-tab-pane label="练习题" name="exercise">
            <ExerciseCard :exercises="response.resources.exercises" :submitted="false" :correct-count="0" :correct-nodes="[]" :weak-nodes="[]" :uid-label-map="{}" @submit-round="submitExerciseRound" />
          </el-tab-pane>
          <el-tab-pane label="视频脚本" name="video">
            <VideoScriptCard :script="response.resources.video_script" />
          </el-tab-pane>
          <el-tab-pane label="代码案例" name="code">
            <CodeCaseCard :code-case="response.resources.code_case" />
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
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import ErrorAlert from '@/components/common/ErrorAlert.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import EvidencePanel from '@/components/graphrag/EvidencePanel.vue'
import AgentProgressPanel from '@/components/resources/AgentProgressPanel.vue'
import CodeCaseCard from '@/components/resources/CodeCaseCard.vue'
import DocumentCard from '@/components/resources/DocumentCard.vue'
import ExerciseCard from '@/components/resources/ExerciseCard.vue'
import MindmapCard from '@/components/resources/MindmapCard.vue'
import VideoScriptCard from '@/components/resources/VideoScriptCard.vue'
import { useLearningStore } from '@/stores/learning'
import { useProfileStore } from '@/stores/profile'
import type { ResourceType } from '@/types/profile'
import type { GeneratedExercise } from '@/types/resources'
import { localizeText, percent, uidLabel } from '@/utils/format'

const route = useRoute()
const profileStore = useProfileStore()
const learningStore = useLearningStore()

const query = ref(
  (() => {
    // 优先用 query（中文名），node_id（英文UID）兜底，两个都没有才用默认
    const q = route.query.query as string
    const nid = route.query.node_id as string
    return q || nid || '神经网络训练时那个从后往前算梯度的过程是什么'
  })()
)
const nodeId = ref((route.query.node_id as string) || '')
const allResourceTypes = [
  { value: 'document' as const, label: '讲解文档' },
  { value: 'mindmap' as const, label: '思维导图' },
  { value: 'exercise' as const, label: '练习题' },
  { value: 'video_script' as const, label: '视频脚本' },
  { value: 'code_case' as const, label: '代码案例' },
]

const selectedTypes = ref<ResourceType[]>(['document', 'mindmap', 'exercise', 'video_script', 'code_case'])
const activeTab = ref('document')
const generatedTypes = ref(new Set<string>())
const response = computed(() => learningStore.resourceResponse)

// 监听新备课内容，标记已生成的类型
watch(() => response.value?.resources, (res) => {
  if (!res) return
  const types: Record<string, boolean> = {
    document: !!res.document,
    mindmap: !!res.mindmap,
    exercise: !!(res.exercises?.length),
    video_script: !!res.video_script,
    code_case: !!res.code_case,
  }
  for (const [k, v] of Object.entries(types)) {
    if (v) generatedTypes.value.add(k)
  }
})

async function generate() {
  if (!selectedTypes.value.length) return
  if (!profileStore.profile) await profileStore.initFromAuth()
  await learningStore.generateForQuery(query.value, nodeId.value, profileStore.studentProfileInput, selectedTypes.value, profileStore.studentId)
  ElMessage.success('AI 备课完成')
}

function resetGeneration() {
  generatedTypes.value.clear()
  selectedTypes.value = ['document', 'mindmap', 'exercise', 'video_script', 'code_case']
}

async function submitExerciseRound(results: Array<{ exercise: GeneratedExercise; answer: string }>) {
  const fallbackNode = learningStore.resourceResponse?.resolved_uid || learningStore.currentNodeId
  const attempts = results
    .map(({ exercise, answer }) => {
      const targetNode = exercise.related_node_id || fallbackNode
      if (!targetNode) return null
      const ans = String(answer || '').trim()
      const expected = String(exercise.answer?.correct || '')
      const isCorrect = Boolean(ans && expected && ans === expected)
      return {
        exercise_id: exercise.title || 'generated_exercise',
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
    round_id: `resource_exercises_${Date.now()}`,
    source_type: 'generated_resource',
    source_id: learningStore.resourceResponse?.resource_record_id || '',
    target_node_id: fallbackNode || '',
    target_node_name: uidLabel(fallbackNode) || fallbackNode || '',
    title: `${uidLabel(fallbackNode) || '生成资源'}练习`,
    duration_seconds: 0,
    started_at: null,
    attempts
  })
  ElMessage.success('本轮练习结果已统一写入画像')
}

function sourceLabelForReport(source: string) {
  return uidLabel(source) || localizeText(source)
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
  grid-template-columns: minmax(280px, 1fr) auto 130px;
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

.quality-tags {
  margin: 14px 0;
}
</style>
