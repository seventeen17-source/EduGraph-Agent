<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>课程知识图谱</h1>
        <div class="muted">围绕核心知识点展开前置关系、相关节点和证据路径。</div>
      </div>
      <div class="graph-search">
        <el-autocomplete
          v-model="nodeInput"
          placeholder="输入知识点名称，如：反向"
          clearable
          value-key="value"
          :fetch-suggestions="fetchSearchSuggestions"
          :trigger-on-focus="false"
          :debounce="240"
          popper-class="graph-search-popper"
          @select="selectSearchSuggestion"
          @keyup.enter="loadBySearch(nodeInput)"
        >
          <template #default="{ item }">
            <div class="suggestion-item">
              <strong>{{ item.label }}</strong>
              <span>{{ item.summary }}</span>
            </div>
          </template>
        </el-autocomplete>
        <el-button type="primary" :loading="learningStore.loadingGraph || searching" @click="loadBySearch(nodeInput)">
          加载节点
        </el-button>
      </div>
    </div>

    <ErrorAlert :message="learningStore.error" :retry="() => loadNode(selectedUid)" />

    <div class="two-column">
      <!-- 左栏：图谱画布 -->
      <el-card class="section-card graph-card">
        <template #header>
          <div class="panel-title">
            <el-segmented v-model="viewMode" :options="viewOptions" size="small" />
            <el-space>
              <el-tag v-if="selectedNode" :type="masteryTagType(masteryLevel)" effect="dark" size="small">
                {{ masteryLabel }}
              </el-tag>
              <el-tag v-if="selectedNode && isWeakPoint" type="danger" size="small">⚠️ 薄弱点</el-tag>
              <el-tag type="info" size="small">{{ subgraphNodes }} 节点</el-tag>
            </el-space>
          </div>
        </template>

        <!-- 全览视图 -->
        <div v-if="viewMode === 'full'" class="full-graph-wrapper">
          <div v-if="loadingAll" class="full-graph-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载全部节点...</span>
          </div>
          <div v-else-if="allNodes.length === 0" class="full-graph-empty">
            <el-empty description="暂无节点数据" />
          </div>
          <FullGraphCanvas
            v-else
            :nodes="allNodes"
            :mastery-map="masteryMap"
            :weak-points="weakPoints"
            @select="selectNode"
            @generate-resources="goGenerateResources"
            @view-exercises="goExercises"
            @ask-question="goAsk"
          />
        </div>

        <!-- 子图视图 -->
        <GraphCanvas
          v-else
          :subgraph="learningStore.subgraph"
          :selected-uid="selectedUid"
          :mastery-map="masteryMap"
          :weak-points="weakPoints"
          @select="selectNode"
          @generate-resources="goGenerateResources"
          @view-exercises="goExercises"
          @ask-question="goAsk"
          @add-to-path="goPath"
        />
      </el-card>

      <!-- 右栏：节点详情 -->
      <el-card class="section-card detail-card">
        <template #header>
          <div class="panel-title">
            <span>节点详情</span>
            <el-tag v-if="selectedNode">{{ uidLabel(selectedNode.uid) }}</el-tag>
          </div>
        </template>

        <LoadingSkeleton v-if="learningStore.loadingGraph" :rows="8" />
        <el-empty v-else-if="!selectedNode" description="点击图谱节点查看详情" />
        <div v-else class="node-detail">
          <h2>{{ nodeName(selectedNode) }}</h2>
          <p>{{ selectedNode.properties?.summary || '暂无摘要' }}</p>

          <!-- 状态标签 -->
          <div class="tag-row">
            <el-tag type="primary">{{ nodeTypeLabel(selectedNode.properties?.node_type) }}</el-tag>
            <el-tag type="success">{{ roleLabel(selectedNode.properties?.role_in_path) }}</el-tag>
            <el-tag type="warning">{{ difficultyStars(selectedNode.properties?.difficulty) }}</el-tag>
            <el-tag v-if="masteryLevel" :type="masteryTagType(masteryLevel)" size="small">
              {{ masteryLabel }}
            </el-tag>
          </div>

          <!-- 证据评分 -->
          <div v-if="evidenceScore > 0" class="evidence-score-row">
            <span class="score-label">证据评分</span>
            <el-progress
              :percentage="Math.round(evidenceScore * 100)"
              :color="scoreColor"
              :stroke-width="6"
              :show-text="true"
              style="flex:1"
            />
          </div>

          <!-- 关系摘要 -->
          <div v-if="relationSummary.length" class="relation-summary-block">
            <div class="block-label">关系摘要</div>
            <div v-for="(s, idx) in relationSummary" :key="idx" class="summary-item">{{ s }}</div>
          </div>

          <!-- 推荐动作 -->
          <div v-if="recommendedActions.length" class="action-block">
            <div class="block-label">推荐下一步</div>
            <div v-for="(action, idx) in recommendedActions" :key="idx" class="action-item">
              <el-icon><ArrowRight /></el-icon>
              {{ action }}
            </div>
          </div>

          <!-- 关键词 -->
          <el-divider />
          <div class="detail-block">
            <strong>关键词</strong>
            <div class="tag-row">
              <el-tag v-for="tag in (selectedNode.properties?.keywords || [])" :key="tag" effect="plain">{{ tag }}</el-tag>
            </div>
          </div>

          <!-- 前置知识 -->
          <div class="detail-block">
            <strong>前置知识</strong>
            <el-button
              v-for="uid in (selectedNode.properties?.prerequisites || [])"
              :key="uid"
              link
              type="primary"
              @click="loadNode(uid)"
            >
              {{ uidLabel(uid) }}
            </el-button>
          </div>

          <!-- 相关知识 -->
          <div class="detail-block">
            <strong>相关知识</strong>
            <el-button
              v-for="uid in (selectedNode.properties?.related || [])"
              :key="uid"
              link
              type="primary"
              @click="loadNode(uid)"
            >
              {{ uidLabel(uid) }}
            </el-button>
          </div>

          <!-- 配套练习 -->
          <div v-if="exerciseCount > 0" class="detail-block">
            <strong>配套练习</strong>
            <el-tag type="info">{{ exerciseCount }} 道题目可用</el-tag>
            <el-button type="primary" plain size="small" @click="goExercises(selectedNode)">
              查看练习
            </el-button>
          </div>

          <!-- 操作按钮 -->
          <div class="detail-actions">
            <el-button @click="$router.push('/learning-path')">查看学习路径</el-button>
            <el-button type="primary" @click="goGenerateResources(selectedNode)">
              生成学习资源
            </el-button>
            <el-button @click="goAsk(selectedNode)">向学习助手提问</el-button>
          </div>

          <div class="node-id muted">图谱标识：{{ uidLabel(selectedNode.uid) || '未映射知识点' }}</div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowRight, Loading } from '@element-plus/icons-vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ErrorAlert from '@/components/common/ErrorAlert.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import GraphCanvas from '@/components/graph/GraphCanvas.vue'
import FullGraphCanvas from '@/components/graph/FullGraphCanvas.vue'
import { getAllNodes, searchGraphNodes } from '@/api/graph'
import { useLearningStore } from '@/stores/learning'
import { useProfileStore } from '@/stores/profile'
import type { GraphNode } from '@/types/graph'
import { difficultyStars, nodeName, nodeTypeLabel, roleLabel, uidLabel } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const learningStore = useLearningStore()
const profileStore = useProfileStore()

const nodeInput = ref('ml_gradient_descent')
const selectedUid = ref('ml_gradient_descent')
const searching = ref(false)

// ---- 全览视图 ----
const viewMode = ref<'subgraph' | 'full'>('subgraph')
const viewOptions = [
  { label: '子图', value: 'subgraph' },
  { label: '全览', value: 'full' },
]
const allNodes = ref<GraphNode[]>([])
const loadingAll = ref(false)

async function loadAllNodes() {
  if (allNodes.value.length > 0) return
  loadingAll.value = true
  try {
    allNodes.value = await getAllNodes()
  } catch (e) {
    console.error('loadAllNodes error', e)
  } finally {
    loadingAll.value = false
  }
}

watch(viewMode, (mode) => {
  if (mode === 'full') loadAllNodes()
})

// ---- computed ----

const selectedNode = computed(() => learningStore.currentNode)

// 从 profile 提取掌握度映射：uid -> level string
const masteryMap = computed<Record<string, string>>(() => {
  if (!profileStore.profile?.node_mastery) return {}
  const result: Record<string, string> = {}
  for (const [uid, mastery] of Object.entries(profileStore.profile.node_mastery)) {
    result[uid] = mastery.level
  }
  return result
})

// 薄弱点列表（从 diagnosed 和 self_reported 提取 node_id）
const weakPoints = computed<string[]>(() => {
  const wp = profileStore.profile?.weak_points
  if (!wp) return []
  const ids: string[] = []
  for (const d of wp.diagnosed || []) {
    if (d.node_id) ids.push(d.node_id)
  }
  for (const s of wp.self_reported || []) {
    if (s.node_id) ids.push(s.node_id)
  }
  return [...new Set(ids)]
})

// 节点是否在薄弱点中
const isWeakPoint = computed(() => {
  if (!selectedNode.value) return false
  return weakPoints.value.includes(selectedNode.value.uid)
})

// 掌握度
const masteryLevel = computed(() => {
  if (!selectedNode.value) return ''
  return masteryMap.value[selectedNode.value.uid] || ''
})

// 掌握度标签
function masteryTagType(level: string): string {
  const map: Record<string, string> = { weak: 'danger', basic: 'info', intermediate: 'primary', advanced: 'success' }
  return map[level] || 'info'
}

// 掌握度标签文本
const masteryLabel = computed(() => {
  const map: Record<string, string> = { weak: '薄弱', basic: '基础', intermediate: '学习中', advanced: '已掌握' }
  return map[masteryLevel.value] || '未学习'
})

// 子图节点数
const subgraphNodes = computed(() => learningStore.subgraph?.nodes.length || 0)

// 练习数量（从 evidence 推断）
const exerciseCount = computed(() => {
  return learningStore.subgraph?.relationships.filter(r => r.type === 'HAS_EXERCISE' || r.type === 'ASSESSES').length || 0
})

// 关系摘要（从 evidence 推断）
const relationSummary = computed<string[]>(() => {
  if (!selectedNode.value) return []
  // 从属性推断
  const prereqs = selectedNode.value.properties?.prerequisites as string[] || []
  const related = selectedNode.value.properties?.related as string[] || []
  const summaries: string[] = []
  if (prereqs.length) summaries.push(`其前置知识包括：${prereqs.slice(0, 3).map(uidLabel).join('、')}...`)
  if (related.length) summaries.push(`与当前内容紧密相关的知识点有：${related.slice(0, 3).map(uidLabel).join('、')}...`)
  return summaries
})

// 推荐动作（从 evidence 推断）
const recommendedActions = computed<string[]>(() => {
  if (!selectedNode.value) return []
  const actions: string[] = []
  actions.push(`阅读「${nodeName(selectedNode.value)}」的讲解文档`)
  if (exerciseCount.value > 0) actions.push(`完成「${nodeName(selectedNode.value)}」配套练习`)
  actions.push(`向学习助手提问「${nodeName(selectedNode.value)}」是什么`)
  return actions
})

// 证据评分（从 evidence 推断）
const evidenceScore = computed(() => 0.6) // TODO: 接入真实 evidence

// 评分颜色
const scoreColor = computed(() => {
  const s = evidenceScore.value
  if (s >= 0.7) return '#67C23A'
  if (s >= 0.4) return '#E6A23C'
  return '#F56C6C'
})

// ---- actions ----

type SearchSuggestion = { value: string; label: string; uid: string; summary: string }

function toSuggestion(node: GraphNode): SearchSuggestion {
  return {
    value: nodeName(node),
    label: nodeName(node),
    uid: node.uid,
    summary: node.properties?.summary || '暂无摘要'
  }
}

async function loadNode(uid: string) {
  selectedUid.value = uid || 'ml_gradient_descent'
  nodeInput.value = selectedUid.value
  await learningStore.loadGraph(selectedUid.value)
  nodeInput.value = nodeName(learningStore.currentNode) || uidLabel(selectedUid.value)
}

async function fetchSearchSuggestions(input: string, cb: (items: SearchSuggestion[]) => void) {
  const keyword = input.trim()
  if (!keyword) { cb([]); return }
  searching.value = true
  try {
    const candidates = await searchGraphNodes(keyword, 8)
    cb(candidates.map(toSuggestion))
  } catch { cb([]) } finally { searching.value = false }
}

async function selectSearchSuggestion(item: SearchSuggestion) {
  await loadNode(item.uid)
}

async function loadBySearch(input: string) {
  const keyword = input.trim()
  if (!keyword) { await loadNode('ml_gradient_descent'); return }
  searching.value = true
  try {
    const candidates = await searchGraphNodes(keyword, 8)
    if (candidates.length) {
      await loadNode(candidates[0].uid)
      nodeInput.value = nodeName(candidates[0])
      return
    }
    await loadNode(keyword)
  } finally { searching.value = false }
}

async function selectNode(node: GraphNode) {
  await loadNode(node.uid)
  viewMode.value = 'subgraph'
}

// ---- 快捷操作 ----

function goGenerateResources(node: GraphNode) {
  router.push({
    path: '/resources',
    query: { query: nodeName(node), node_id: node.uid }
  })
}

function goExercises(node: GraphNode) {
  // 如果当前是练习题节点，尝试从 properties 中找知识点 ID
  const kpId = node.properties?.related_kp || node.properties?.knowledge_point_id || node.uid
  router.push({ path: '/exercise', query: { node_id: kpId } })
}

function goAsk(node: GraphNode) {
  router.push({
    path: '/tutor',
    query: { message: `${nodeName(node)} 是什么？请帮我解释一下` }
  })
}

function goPath(node: GraphNode) {
  router.push({ path: '/learning-path', query: { add: node.uid } })
}

function generateResourcesForNode(node: GraphNode) {
  goGenerateResources(node)
}

onMounted(() => loadNode(selectedUid.value))
</script>

<style scoped>
.graph-search {
  display: grid;
  grid-template-columns: 260px 96px;
  gap: 8px;
}

.graph-card {
  min-height: 660px;
}

.detail-card {
  min-height: 660px;
}

.node-detail h2 {
  margin: 0 0 8px;
}

.node-detail p {
  color: #606266;
  line-height: 1.7;
}

.detail-block {
  display: grid;
  gap: 8px;
  margin: 16px 0;
}

.node-id {
  margin-top: 10px;
  font-size: 12px;
}

.detail-actions {
  display: grid;
  gap: 10px;
  margin-top: 20px;
}

.suggestion-item {
  display: grid;
  gap: 2px;
  padding: 6px 0;
}

.suggestion-item strong {
  color: #1f2d3d;
}

.suggestion-item span {
  overflow: hidden;
  color: #7a8494;
  font-size: 12px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.evidence-score-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0;
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 6px;
}

.score-label {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
  min-width: 56px;
}

.relation-summary-block {
  margin: 10px 0;
  padding: 8px 10px;
  background: #f0f9eb;
  border-radius: 6px;
}

.action-block {
  margin: 10px 0;
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 6px;
}

.block-label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-item {
  font-size: 12px;
  color: #303133;
  line-height: 1.6;
  padding: 2px 0;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #303133;
  padding: 2px 0;
}

.detail-block {
  display: grid;
  gap: 6px;
  margin: 12px 0;
}
</style>
