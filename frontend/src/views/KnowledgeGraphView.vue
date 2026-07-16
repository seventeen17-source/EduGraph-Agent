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

    <!-- 学习进度总览仪表盘 -->
    <div class="learning-overview">
      <div v-if="loadingOverview" class="overview-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载学习进度...</span>
      </div>
      <div v-else-if="learningOverview && learningOverview.total_nodes > 0" class="overview-content">
        <div class="overview-cards">
          <div class="overview-card mastered">
            <div class="card-label">已掌握</div>
            <div class="card-value">{{ learningOverview.mastered }}</div>
            <div class="card-percent">{{ overviewPercent('mastered') }}%</div>
          </div>
          <div class="overview-card weak">
            <div class="card-label">薄弱</div>
            <div class="card-value">{{ learningOverview.weak }}</div>
            <div class="card-percent">{{ overviewPercent('weak') }}%</div>
          </div>
          <div class="overview-card forgetting">
            <div class="card-label">遗忘预警</div>
            <div class="card-value">{{ learningOverview.forgetting }}</div>
            <div class="card-percent">{{ overviewPercent('forgetting') }}%</div>
          </div>
          <div class="overview-card learning">
            <div class="card-label">学习中</div>
            <div class="card-value">{{ learningOverview.learning }}</div>
            <div class="card-percent">{{ overviewPercent('learning') }}%</div>
          </div>
          <div class="overview-card unlearned">
            <div class="card-label">未学习</div>
            <div class="card-value">{{ learningOverview.unlearned }}</div>
            <div class="card-percent">{{ overviewPercent('unlearned') }}%</div>
          </div>
        </div>
        <div class="overview-progress">
          <span class="progress-label">总掌握率</span>
          <el-progress
            :percentage="Math.round((learningOverview.mastery_rate || 0) * 100)"
            :stroke-width="14"
            :text-inside="true"
            style="flex:1"
          />
        </div>
      </div>
      <el-alert
        v-else
        type="info"
        :closable="false"
        show-icon
        title="暂无学习进度数据"
        description="开始学习后，这里会显示你的掌握情况总览，包括已掌握、薄弱、遗忘预警等状态分布。"
      />
    </div>

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
          <!-- 筛选工具栏（仅全览视图显示） -->
          <div v-if="viewMode === 'full'" class="filter-toolbar">
            <el-select v-model="filterStatus" placeholder="状态筛选" size="small" class="filter-select">
              <el-option label="全部状态" value="all" />
              <el-option label="已掌握" value="mastered" />
              <el-option label="薄弱" value="weak" />
              <el-option label="遗忘" value="forgetting" />
              <el-option label="学习中" value="learning" />
              <el-option label="未学习" value="unlearned" />
            </el-select>
            <el-select v-model="filterChapter" placeholder="章节筛选" size="small" class="filter-select">
              <el-option label="全部章节" value="all" />
              <el-option
                v-for="ch in chapterList"
                :key="ch"
                :label="chapterLabel(ch)"
                :value="ch"
              />
            </el-select>
            <el-tag type="info" size="small" effect="plain">
              {{ filteredNodes.length }} / {{ allNodes.length }}
            </el-tag>
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
            :nodes="filteredNodes"
            :mastery-map="masteryMap"
            :weak-points="weakPoints"
            :node-status-map="nodeStatusMap"
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
          :node-status-map="nodeStatusMap"
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
            <el-tag v-if="selectedNode">{{ displayNodeLabel(selectedNode.uid) }}</el-tag>
          </div>
        </template>

        <LoadingSkeleton v-if="learningStore.loadingGraph" :rows="8" />
        <el-empty v-else-if="!selectedNode" description="点击图谱节点查看详情" />
        <div v-else class="node-detail">
          <h2>{{ nodeName(selectedNode) }}</h2>
          <p>{{ localizeText(selectedNode.properties?.summary || '暂无摘要') }}</p>

          <!-- 状态标签 -->
          <div class="tag-row">
            <el-tag type="primary">{{ nodeTypeLabel(selectedNode.properties?.node_type) }}</el-tag>
            <el-tag type="success">{{ roleLabel(selectedNode.properties?.role_in_path) }}</el-tag>
            <el-tag type="warning">{{ difficultyStars(selectedNode.properties?.difficulty) }}</el-tag>
            <el-tag v-if="masteryLevel" :type="masteryTagType(masteryLevel)" size="small">
              {{ masteryLabel }}
            </el-tag>
            <el-tag v-if="weakStatus?.is_weak" type="danger" size="small" effect="dark">⚠️ 薄弱节点</el-tag>
          </div>

          <!-- 推荐起点提示 -->
          <el-alert
            v-if="recommendedStart && selectedNode && selectedNode.uid === recommendedStart.uid && recommendedStart.reason"
            type="success"
            :closable="false"
            show-icon
            :title="`推荐起点：${localizeText(recommendedStart.reason)}`"
            class="recommend-start-alert"
          />

          <!-- 决策面板加载中提示 -->
          <div v-if="loadingNodeDetail && !nodeDetail" class="decision-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在加载节点决策数据...</span>
          </div>

          <!-- 折叠式详情面板 -->
          <el-collapse v-else v-model="activeCollapse" class="detail-collapse">
            <!-- 1. 推荐决策 -->
            <el-collapse-item name="recommendation" title="🎯 推荐决策">
              <div v-if="nodeRecommendation" class="decision-block recommendation-block">
                <div class="recommendation-row">
                  <el-tag :type="recommendationTagType(nodeRecommendation.action)" effect="dark" size="small">
                    {{ recommendationActionText(nodeRecommendation.action) }}
                  </el-tag>
                  <span class="recommendation-reason">{{ localizeText(nodeRecommendation.reason) }}</span>
                </div>
              </div>
              <div v-if="recommendedActions.length" class="action-block">
                <div class="block-label">推荐下一步</div>
                <div v-for="(action, idx) in recommendedActions" :key="idx" class="action-item">
                  <el-icon><ArrowRight /></el-icon>
                  {{ localizeText(action) }}
                </div>
              </div>
              <div v-if="!nodeRecommendation && !recommendedActions.length" class="muted small">暂无推荐信息</div>
            </el-collapse-item>

            <!-- 2. 掌握度状态 -->
            <el-collapse-item name="mastery" title="📊 掌握度状态">
              <div class="decision-block mastery-block">
                <div class="mastery-row">
                  <el-progress
                    :percentage="masteryPercent"
                    :color="scoreColor"
                    :stroke-width="10"
                    :text-inside="true"
                    style="flex:1"
                  />
                  <el-tag
                    v-if="masteryTrendLabel"
                    size="small"
                    :style="{ color: masteryTrendColor, borderColor: masteryTrendColor }"
                    effect="plain"
                  >
                    {{ masteryTrendLabel }}
                  </el-tag>
                </div>
                <div v-if="masteryInfo?.last_attempt" class="maturity-meta">
                  最近作答：{{ masteryInfo.last_attempt }}
                </div>
              </div>
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
            </el-collapse-item>

            <!-- 3. 薄弱状态与遗忘风险 -->
            <el-collapse-item name="weak" title="⚠️ 薄弱状态与遗忘风险">
              <div v-if="weakStatus?.is_weak" class="decision-block weak-block">
                <div class="block-label">薄弱状态</div>
                <el-alert
                  type="error"
                  :closable="false"
                  show-icon
                  :title="localizeText(weakStatus.reason || '该知识点被识别为薄弱点')"
                />
              </div>
              <div v-if="forgettingRisk" class="decision-block forgetting-block">
                <div class="block-label">遗忘风险</div>
                <div class="forgetting-row">
                  <el-tag :type="forgettingRiskTagType(forgettingRisk.level)" effect="dark" size="small">
                    {{ forgettingRiskLabel(forgettingRisk.level) }}
                  </el-tag>
                  <span v-if="forgettingRisk.days_since_last != null" class="forgetting-meta">
                    距上次学习 {{ forgettingRisk.days_since_last }} 天
                  </span>
                  <span v-if="forgettingRisk.suggested_review_date" class="forgetting-meta">
                    建议复习：{{ forgettingRisk.suggested_review_date }}
                  </span>
                </div>
              </div>
              <div v-if="!weakStatus?.is_weak && !forgettingRisk" class="muted small">
                当前节点暂无薄弱或遗忘风险
              </div>
            </el-collapse-item>

            <!-- 4. 前置与后继关系 -->
            <el-collapse-item name="relations" title="🔗 前置与后继关系">
              <div v-if="relationSummary.length" class="relation-summary-block">
                <div class="block-label">关系摘要</div>
                <div v-for="(s, idx) in relationSummary" :key="idx" class="summary-item">{{ localizeText(s) }}</div>
              </div>
              <div class="detail-block">
                <strong>前置关系</strong>
                <div v-if="prerequisitesWithWeight.length" class="edge-list">
                  <el-tooltip
                    v-for="edge in prerequisitesWithWeight"
                    :key="edge.uid"
                    :content="`权重：${edge.weight}｜${edge.explanation}`"
                    placement="top"
                  >
                    <div class="edge-item" :class="{ mastered: edge.mastered }" @click="loadNode(edge.uid)">
                      <span class="edge-mastered-icon">{{ edge.mastered ? '✓' : '○' }}</span>
                      <span class="edge-name">{{ displayNodeLabel(edge.name || edge.uid) }}</span>
                      <el-tag size="small" effect="plain" class="edge-weight">权重 {{ edge.weight.toFixed(2) }}</el-tag>
                    </div>
                  </el-tooltip>
                </div>
                <div v-else class="muted small">
                  <el-button
                    v-for="uid in (selectedNode.properties?.prerequisites || [])"
                    :key="uid"
                    link
                    type="primary"
                    @click="loadNode(uid)"
                  >
                    {{ displayNodeLabel(uid) }}
                  </el-button>
                  <span v-if="!(selectedNode.properties?.prerequisites || []).length">暂无前置知识</span>
                </div>
              </div>
              <div v-if="nextNodesWithWeight.length" class="detail-block">
                <strong>后继节点</strong>
                <div class="edge-list">
                  <el-tooltip
                    v-for="edge in nextNodesWithWeight"
                    :key="edge.uid"
                    :content="`权重：${edge.weight}｜${edge.explanation}`"
                    placement="top"
                  >
                    <div class="edge-item" :class="{ mastered: edge.mastered }" @click="loadNode(edge.uid)">
                      <span class="edge-mastered-icon">{{ edge.mastered ? '✓' : '○' }}</span>
                      <span class="edge-name">{{ displayNodeLabel(edge.name || edge.uid) }}</span>
                      <el-tag size="small" effect="plain" class="edge-weight">权重 {{ edge.weight.toFixed(2) }}</el-tag>
                    </div>
                  </el-tooltip>
                </div>
              </div>
            </el-collapse-item>

            <!-- 5. 基础信息 -->
            <el-collapse-item name="basic" title="📋 基础信息">
              <div class="detail-block">
                <strong>关键词</strong>
                <div class="tag-row">
                  <el-tag v-for="tag in (selectedNode.properties?.keywords || [])" :key="tag" effect="plain">{{ localizeText(tag) }}</el-tag>
                </div>
              </div>
              <el-divider />
              <div class="detail-block">
                <strong>相关知识</strong>
                <el-button
                  v-for="uid in (selectedNode.properties?.related || [])"
                  :key="uid"
                  link
                  type="primary"
                  @click="loadNode(uid)"
                >
                  {{ displayNodeLabel(uid) }}
                </el-button>
              </div>
              <div v-if="exerciseCount > 0" class="detail-block">
                <strong>配套练习</strong>
                <el-tag type="info">{{ exerciseCount }} 道题目可用</el-tag>
                <el-button type="primary" plain size="small" @click="goExercises(selectedNode)">
                  查看练习
                </el-button>
              </div>
            </el-collapse-item>

            <!-- 6. 快捷入口 -->
            <el-collapse-item name="actions" title="🚀 快捷入口">
              <div class="detail-block quick-actions-block">
                <el-button-group class="quick-action-group">
                  <el-button size="small" type="primary" @click="quickGenerateResources">
                    📄 生成资源
                  </el-button>
                  <el-button size="small" type="success" @click="quickExercises">
                    📝 去练习
                  </el-button>
                  <el-button size="small" type="warning" @click="quickAsk">
                    💬 问助手
                  </el-button>
                  <el-button size="small" @click="quickAddToPath">
                    🚀 加入学习路径
                  </el-button>
                </el-button-group>
              </div>
            </el-collapse-item>
          </el-collapse>

          <div class="node-id muted">图谱标识：{{ displayNodeLabel(selectedNode.uid, '未映射知识点') }}</div>
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
import { getAllNodesWithMastery, getNodeDetail, getLearningOverview, getRecommendedStart, searchGraphNodes } from '@/api/graph'
import { useLearningStore } from '@/stores/learning'
import { useProfileStore } from '@/stores/profile'
import type { GraphNode, LearningOverview, NodeDetailResponse, NodeEdgeWithWeight, NodeWithMastery, RecommendedStart } from '@/types/graph'
import { chapterLabel, difficultyStars, displayNodeLabel, localizeText, nodeName, nodeTypeLabel, roleLabel } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const learningStore = useLearningStore()
const profileStore = useProfileStore()

const nodeInput = ref('')
const selectedUid = ref('')
const searching = ref(false)

// ---- 节点详情（Task 6） ----
const nodeDetail = ref<NodeDetailResponse | null>(null)
const loadingNodeDetail = ref(false)

// ---- 全览视图 ----
const viewMode = ref<'subgraph' | 'full'>('subgraph')
const viewOptions = [
  { label: '子图', value: 'subgraph' },
  { label: '全览', value: 'full' },
]
const allNodes = ref<GraphNode[]>([])
const allNodesWithMastery = ref<NodeWithMastery[]>([])
const loadingAll = ref(false)

// ---- 学习进度总览 ----
const learningOverview = ref<LearningOverview | null>(null)
const loadingOverview = ref(false)

// ---- 推荐起点 ----
const recommendedStart = ref<RecommendedStart | null>(null)

// ---- 筛选工具栏 ----
const filterStatus = ref<string>('all')
const filterChapter = ref<string>('all')

// ---- 折叠面板 ----
const activeCollapse = ref<string[]>(['recommendation', 'mastery'])

async function loadAllNodes() {
  if (allNodes.value.length > 0) return
  const studentId = profileStore.studentId
  if (!studentId) {
    loadingAll.value = true
    try {
      allNodes.value = []
    } finally {
      loadingAll.value = false
    }
    return
  }
  loadingAll.value = true
  try {
    const nodesWithMastery = await getAllNodesWithMastery(studentId)
    allNodesWithMastery.value = nodesWithMastery
    // 将 NodeWithMastery 转换为 GraphNode 格式供组件使用
    const graphNodes: GraphNode[] = nodesWithMastery.map((n) => ({
      uid: n.uid,
      labels: ['KnowledgePoint'],
      properties: {
        name: n.name,
        chapter_id: n.chapter,
        difficulty: n.difficulty,
        summary: n.summary,
        mastery_score: n.mastery_score,
        last_practiced: n.last_practiced,
      },
    }))
    allNodes.value = graphNodes
  } catch (e) {
    console.error('loadAllNodes error', e)
  } finally {
    loadingAll.value = false
  }
}

watch(viewMode, (mode) => {
  if (mode === 'full') loadAllNodes()
})

// ---- 学习进度总览 ----
async function loadLearningOverview() {
  const studentId = profileStore.studentId
  if (!studentId) return
  loadingOverview.value = true
  try {
    learningOverview.value = await getLearningOverview(studentId)
  } catch (e) {
    console.error('loadLearningOverview error', e)
  } finally {
    loadingOverview.value = false
  }
}

function overviewPercent(field: 'mastered' | 'weak' | 'forgetting' | 'learning' | 'unlearned'): number {
  if (!learningOverview.value || learningOverview.value.total_nodes === 0) return 0
  return Math.round((learningOverview.value[field] / learningOverview.value.total_nodes) * 100)
}

// ---- 推荐起点 ----
async function loadRecommendedStart() {
  const studentId = profileStore.studentId
  if (!studentId) return
  try {
    const result = await getRecommendedStart(studentId)
    recommendedStart.value = result
    if (result.uid) {
      selectedUid.value = result.uid
      nodeInput.value = result.name || result.uid
    }
  } catch (e) {
    console.error('loadRecommendedStart error', e)
    // 回退：加载所有节点，使用第一个作为默认
    try {
      await loadAllNodes()
      if (allNodes.value.length > 0) {
        selectedUid.value = allNodes.value[0].uid
        nodeInput.value = nodeName(allNodes.value[0])
      }
    } catch {}
  }
}

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

// 掌握度标签类型
function masteryTagType(level: string): string {
  const map: Record<string, string> = { weak: 'danger', basic: 'info', intermediate: 'primary', advanced: 'success' }
  return map[level] || 'info'
}

// 掌握度标签文本
const masteryLabel = computed(() => {
  const map: Record<string, string> = { weak: '薄弱', basic: '基础', intermediate: '学习中', advanced: '已掌握' }
  return map[masteryLevel.value] || '未学习'
})

// 节点状态映射：uid -> status（mastered/weak/forgetting/learning/unlearned）
const nodeStatusMap = computed<Record<string, string>>(() => {
  const result: Record<string, string> = {}
  for (const n of allNodesWithMastery.value) {
    result[n.uid] = n.status
  }
  return result
})

// 章节列表（从全览节点中提取唯一章节）
const chapterList = computed<string[]>(() => {
  const set = new Set<string>()
  for (const n of allNodes.value) {
    const ch = n.properties?.chapter_id as string
    if (ch) set.add(ch)
  }
  return [...set].sort()
})

// 筛选后的全览节点
const filteredNodes = computed<GraphNode[]>(() => {
  let result = allNodes.value
  if (filterStatus.value !== 'all') {
    result = result.filter((n) => nodeStatusMap.value[n.uid] === filterStatus.value)
  }
  if (filterChapter.value !== 'all') {
    result = result.filter((n) => (n.properties?.chapter_id as string) === filterChapter.value)
  }
  return result
})

// ===== Task 6: 节点详情计算属性 =====

// 掌握度详情（来自 nodeDetail）
const masteryInfo = computed(() => nodeDetail.value?.mastery || null)

// 薄弱状态详情
const weakStatus = computed(() => nodeDetail.value?.weak_status || null)

// 遗忘风险
const forgettingRisk = computed(() => nodeDetail.value?.forgetting_risk || null)

// 推荐决策
const nodeRecommendation = computed(() => nodeDetail.value?.recommendation || null)

// 前置关系（带权重和解释）
const prerequisitesWithWeight = computed<NodeEdgeWithWeight[]>(() => {
  return nodeDetail.value?.prerequisites || []
})

// 后继节点（带权重和解释）
const nextNodesWithWeight = computed<NodeEdgeWithWeight[]>(() => {
  return nodeDetail.value?.next_nodes || []
})

// 掌握度进度条百分比
const masteryPercent = computed(() => {
  if (masteryInfo.value?.value != null) {
    return Math.round(masteryInfo.value.value * 100)
  }
  // 回退到 profile 中的掌握度
  const mastery = profileStore.profile?.node_mastery?.[selectedUid.value]
  if (mastery?.mastery_score != null) {
    return Math.round(mastery.mastery_score * 100)
  }
  return 0
})

// 掌握度趋势文本
const masteryTrendLabel = computed(() => {
  const trend = masteryInfo.value?.trend
  if (trend === 'rising') return '↗ 上升'
  if (trend === 'falling') return '↘ 下降'
  if (trend === 'stable') return '→ 平稳'
  return ''
})

// 掌握度趋势颜色
const masteryTrendColor = computed(() => {
  const trend = masteryInfo.value?.trend
  if (trend === 'rising') return '#10b981'
  if (trend === 'falling') return '#ef4444'
  return '#909399'
})

// 遗忘风险标签类型
function forgettingRiskTagType(level: string): string {
  if (level === 'high') return 'danger'
  if (level === 'medium') return 'warning'
  if (level === 'low') return 'success'
  return 'info'
}

// 遗忘风险标签文本
function forgettingRiskLabel(level: string): string {
  if (level === 'high') return '高风险'
  if (level === 'medium') return '中风险'
  if (level === 'low') return '低风险'
  return '未知'
}

// 推荐决策文案
function recommendationActionText(action: string): string {
  const map: Record<string, string> = {
    recommend_now: '✅ 立即推荐学习',
    learn_prerequisites_first: '🔗 先学前置知识',
    skip: '⏭️ 暂时跳过',
    review: '🔁 建议复习巩固',
  }
  return map[action] || action
}

// 推荐决策标签类型
function recommendationTagType(action: string): string {
  const map: Record<string, string> = {
    recommend_now: 'success',
    learn_prerequisites_first: 'warning',
    skip: 'info',
    review: 'primary',
  }
  return map[action] || 'info'
}

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
  if (prereqs.length) summaries.push(`其前置知识包括：${prereqs.slice(0, 3).map((id) => displayNodeLabel(id)).join('、')}...`)
  if (related.length) summaries.push(`与当前内容紧密相关的知识点有：${related.slice(0, 3).map((id) => displayNodeLabel(id)).join('、')}...`)
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

// 证据评分：优先使用 HybridRAG 质量分，其次使用 EvidencePackage 自身分数。
const evidenceScore = computed(() => {
  const evidence = learningStore.evidencePackage
  if (!evidence) return 0
  if (evidence.resolved_uid && evidence.resolved_uid !== selectedUid.value) return 0
  const quality = evidence.student_profile_adaptation?.hybrid_rag_quality
  const score = Number(quality?.overall_score ?? evidence.evidence_score ?? 0)
  return Number.isFinite(score) ? Math.max(0, Math.min(1, score)) : 0
})

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
  if (uid) {
    selectedUid.value = uid
    nodeInput.value = selectedUid.value
  }
  if (!selectedUid.value) return
  await learningStore.loadGraph(selectedUid.value)
  await learningStore.loadEvidence(
    selectedUid.value,
    profileStore.profile ? profileStore.studentProfileInput : null,
    profileStore.studentId || null,
  )
  nodeInput.value = nodeName(learningStore.currentNode) || displayNodeLabel(selectedUid.value)
  // Task 6.4: 同时调用 getNodeDetail 获取详细数据
  await loadNodeDetail(selectedUid.value)
}

// 加载节点详情（Task 6.4）
async function loadNodeDetail(uid: string) {
  const studentId = profileStore.studentId || ''
  if (!studentId) {
    nodeDetail.value = null
    return
  }
  loadingNodeDetail.value = true
  try {
    nodeDetail.value = await getNodeDetail(uid, studentId)
  } catch (e) {
    // 详情加载失败不影响主流程，仅清空详情
    nodeDetail.value = null
  } finally {
    loadingNodeDetail.value = false
  }
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
  if (!keyword) return
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
  sessionStorage.setItem('assistant_prefill', `${nodeName(node)} 是什么？请结合课程图谱帮我解释一下。`)
  router.push('/assistant')
}

function goPath(node: GraphNode) {
  router.push({ path: '/learning-path', query: { add: node.uid } })
}

function generateResourcesForNode(node: GraphNode) {
  goGenerateResources(node)
}

// Task 6.3 快捷入口：基于 selectedNode 的快捷操作
function quickGenerateResources() {
  if (selectedNode.value) {
    router.push({ path: '/resources', query: { node_id: selectedNode.value.uid } })
  }
}

function quickExercises() {
  if (selectedNode.value) {
    const kpId = selectedNode.value.properties?.related_kp || selectedNode.value.properties?.knowledge_point_id || selectedNode.value.uid
    router.push({ path: '/exercise', query: { node_id: kpId } })
  }
}

function quickAsk() {
  if (selectedNode.value) {
    sessionStorage.setItem('assistant_prefill', `${nodeName(selectedNode.value)} 是什么？请结合课程图谱帮我解释一下。`)
    router.push('/assistant')
  }
}

function quickAddToPath() {
  router.push({ path: '/learning-path' })
}

onMounted(async () => {
  // 确保 profile 已加载
  if (!profileStore.profile) {
    try { await profileStore.initFromAuth() } catch {}
  }
  // 加载学习进度总览（非阻塞）
  loadLearningOverview()
  // 加载推荐起点，确定默认节点
  await loadRecommendedStart()
  // 加载节点
  await loadNode(selectedUid.value)
})
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

/* ===== Task 6: 节点决策面板 ===== */
.decision-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0;
  padding: 10px 12px;
  font-size: 13px;
  color: #6366f1;
  background: #eef2ff;
  border-radius: 8px;
  border: 1px solid #c7d2fe;
}

.decision-block {
  margin: 12px 0;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}

.mastery-block {
  background: #f0f9ff;
  border-color: #bae6fd;
}

.mastery-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
}

.maturity-meta {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.weak-block {
  background: #fef2f2;
  border-color: #fecaca;
}

.forgetting-block {
  background: #fffbeb;
  border-color: #fde68a;
}

.forgetting-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.forgetting-meta {
  font-size: 12px;
  color: #92400e;
}

.recommendation-block {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.recommendation-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.recommendation-reason {
  font-size: 13px;
  color: #166534;
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

/* 带权重的边列表 */
.edge-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 6px;
}

.edge-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  background: #fff;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
}

.edge-item:hover {
  border-color: #6366f1;
  background: #eef2ff;
}

.edge-item.mastered {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.edge-mastered-icon {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #e2e8f0;
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.edge-item.mastered .edge-mastered-icon {
  background: #10b981;
  color: #fff;
}

.edge-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #1e293b;
}

.edge-weight {
  flex-shrink: 0;
  font-size: 11px;
}

/* 快捷入口 */
.quick-actions-block {
  margin-top: 4px;
}

.quick-action-group {
  display: flex;
  flex-wrap: wrap;
  margin-top: 6px;
}

.quick-action-group .el-button {
  flex: 1;
  min-width: 90px;
}

/* ===== 学习进度总览仪表盘 ===== */
.learning-overview {
  margin-bottom: 16px;
}

.overview-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 18px;
  font-size: 13px;
  color: #6366f1;
  background: #eef2ff;
  border-radius: 10px;
  border: 1px solid #c7d2fe;
}

.overview-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.overview-card {
  padding: 14px 16px;
  border-radius: 10px;
  color: #fff;
  position: relative;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.overview-card.mastered {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.overview-card.weak {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}

.overview-card.forgetting {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.overview-card.learning {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
}

.overview-card.unlearned {
  background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
}

.card-label {
  font-size: 13px;
  opacity: 0.92;
  font-weight: 500;
}

.card-value {
  font-size: 28px;
  font-weight: 700;
  margin-top: 4px;
  line-height: 1.1;
}

.card-percent {
  font-size: 12px;
  opacity: 0.85;
  margin-top: 2px;
}

.overview-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.progress-label {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
}

/* ===== 筛选工具栏 ===== */
.filter-toolbar {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.filter-select {
  width: 160px;
}

/* ===== 折叠面板 ===== */
.detail-collapse {
  margin-top: 12px;
  border: none;
}

.detail-collapse :deep(.el-collapse-item) {
  margin-bottom: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.detail-collapse :deep(.el-collapse-item__header) {
  padding: 0 14px;
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
  background: #f8fafc;
  border-bottom: none;
}

.detail-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
  background: #fff;
}

.detail-collapse :deep(.el-collapse-item__content) {
  padding: 12px 14px;
}

.detail-collapse :deep(.el-collapse-item__content) > div:first-child {
  margin-top: 0;
}

.recommend-start-alert {
  margin: 10px 0;
}

/* 响应式：小屏幕下仪表盘卡片调整为 2-3 列 */
@media (max-width: 768px) {
  .overview-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .filter-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-select {
    width: 100%;
  }
}
</style>
