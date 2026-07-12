<template>
  <div class="page">
    <!-- ===== 页面标题 ===== -->
    <div class="page-header">
      <div class="page-title">
        <h1>📚 我的学习路径</h1>
        <p class="muted">基于你的学习目标，系统会推荐最合适的学习顺序</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" :loading="loading" @click="loadPath">
          🔄 刷新路径
        </el-button>
      </div>
    </div>

    <ErrorAlert :message="learningStore.error" :retry="loadPath" />

    <!-- ===== 新用户引导：未设置学习目标 ===== -->
    <el-card v-if="!hasLearningGoal" class="guide-card" shadow="never">
      <div class="guide-content">
        <div class="guide-icon">🎯</div>
        <div class="guide-text">
          <h3>欢迎来到学习路径！</h3>
          <p>告诉系统你想学什么，它会为你规划一条最合适的学习路线。</p>
        </div>
        <div class="guide-actions">
          <el-button type="primary" @click="$router.push('/profile')">
            设置学习目标
          </el-button>
          <el-button @click="useQuickStart">快速体验（示例路径）</el-button>
        </div>
      </div>
    </el-card>

    <!-- ===== 学习目标摘要（始终显示给有目标的用户） ===== -->
    <el-card v-if="hasLearningGoal" class="goal-summary-card" shadow="never">
      <div class="goal-row">
        <div class="goal-info">
          <span class="goal-label">🎯 学习目标</span>
          <span class="goal-text">{{ learningGoalText }}</span>
        </div>
        <div class="goal-stats">
          <div class="stat-item">
            <span class="stat-num">{{ completedCount }}</span>
            <span class="stat-label">已完成</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-num">{{ inProgressCount }}</span>
            <span class="stat-label">进行中</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-num">{{ recommendedCount }}</span>
            <span class="stat-label">待学习</span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- ===== 主内容：三栏式布局 ===== -->
    <div class="path-three-columns">
      <!-- 第一栏：当前正在学 -->
      <div class="path-column">
        <div class="column-header">
          <div class="column-title">
            <span class="col-badge current">进行中</span>
            <span>当前章节</span>
          </div>
          <el-tooltip content="你目前正在学习的知识点，完成后可继续下一章节">
            <el-icon><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>

        <div v-if="currentNodes.length" class="column-nodes">
          <div
            v-for="uid in currentNodes"
            :key="uid"
            class="node-card current"
            @click="selectNode(uid)"
          >
            <div class="node-icon">📖</div>
            <div class="node-content">
              <strong>{{ nodeLabels[uid] || uidLabel(uid) }}</strong>
              <p class="node-desc">{{ nodeMeta(uid)?.summary || '暂无简介' }}</p>
              <div class="node-tags">
                <el-tag size="small" type="primary" effect="plain">进行中</el-tag>
                <el-tag size="small" effect="plain">{{ nodeMeta(uid)?.estimated_minutes || 30 }}分钟</el-tag>
              </div>
            </div>
            <div class="node-arrow">→</div>
          </div>
        </div>

        <div v-else class="empty-column">
          <div class="empty-icon">🎉</div>
          <p>恭喜！已完成当前章节</p>
          <p class="muted small">点击下方"下一步"开始新章节</p>
        </div>
      </div>

      <!-- 第二栏：需要加强的薄弱点 -->
      <div class="path-column">
        <div class="column-header">
          <div class="column-title">
            <span class="col-badge weak">⚠️ 薄弱点</span>
            <span>需要加强</span>
          </div>
          <el-tooltip content="根据你的练习表现和自评，系统识别出的知识点薄弱环节">
            <el-icon><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>

        <div v-if="weakNodes.length" class="column-nodes">
          <div
            v-for="uid in weakNodes"
            :key="uid"
            class="node-card weak"
            @click="selectNode(uid)"
          >
            <div class="node-icon">📝</div>
            <div class="node-content">
              <strong>{{ nodeLabels[uid] || uidLabel(uid) }}</strong>
              <p class="node-desc">{{ nodeReason(uid) }}</p>
              <div class="node-tags">
                <el-tag size="small" type="warning" effect="plain">薄弱点</el-tag>
                <el-tag v-if="masteryMap[uid]" size="small" effect="plain">
                  掌握度 {{ Math.round((masteryMap[uid]?.mastery_score || 0) * 100) }}%
                </el-tag>
              </div>
            </div>
            <div class="node-arrow">→</div>
          </div>
        </div>

        <div v-else class="empty-column">
          <div class="empty-icon">✅</div>
          <p>暂无薄弱点</p>
          <p class="muted small">继续保持！</p>
        </div>
      </div>

      <!-- 第三栏：推荐下一步 -->
      <div class="path-column">
        <div class="column-header">
          <div class="column-title">
            <span class="col-badge next">▶️ 建议</span>
            <span>推荐学习</span>
          </div>
          <el-tooltip content="根据你的学习目标和前置知识，系统推荐的下一步学习内容">
            <el-icon><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>

        <div v-if="nextNodes.length" class="column-nodes">
          <div
            v-for="uid in nextNodes"
            :key="uid"
            class="node-card recommended"
            @click="selectNode(uid)"
          >
            <div class="node-icon">⭐</div>
            <div class="node-content">
              <strong>{{ nodeLabels[uid] || uidLabel(uid) }}</strong>
              <p class="node-desc">{{ nodeMeta(uid)?.summary || '暂无简介' }}</p>
              <div class="node-tags">
                <el-tag size="small" effect="plain">{{ nodeMeta(uid)?.estimated_minutes || 30 }}分钟</el-tag>
                <el-tag v-if="prereqCount(uid) > 0" size="small" type="info" effect="plain">
                  需先学 {{ prereqCount(uid) }} 个
                </el-tag>
              </div>
            </div>
            <div class="node-arrow">→</div>
          </div>
        </div>

        <div v-else class="empty-column">
          <div class="empty-icon">🏁</div>
          <p>学习路径已完成！</p>
          <p class="muted small">你已掌握所有推荐知识点</p>
        </div>
      </div>
    </div>

    <!-- ===== 完整路径列表（可展开） ===== -->
    <el-card class="full-path-card" shadow="never">
      <template #header>
        <div class="full-path-header">
          <span>📋 完整学习路径（共 {{ learningStore.recommendedNodes.length }} 个节点）</span>
          <el-button size="small" @click="showFullPath = !showFullPath">
            {{ showFullPath ? '收起' : '展开全部' }}
          </el-button>
        </div>
      </template>

      <!-- 路径流程图 -->
      <div v-if="learningStore.recommendedNodes.length" class="path-timeline">
        <div class="timeline-track">
          <div
            v-for="(uid, index) in learningStore.recommendedNodes"
            :key="uid"
            class="timeline-node"
            :class="nodeStatusClass(uid)"
            @click="selectNode(uid)"
          >
            <div class="timeline-step">{{ index + 1 }}</div>
            <div class="timeline-connector" v-if="index < learningStore.recommendedNodes.length - 1"></div>
            <div class="timeline-info">
              <span class="timeline-name">{{ nodeLabels[uid] || uidLabel(uid) }}</span>
              <span class="timeline-status">{{ nodeStatusLabel(uid) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 展开后的详细列表 -->
      <div v-if="showFullPath" class="full-path-list">
        <div v-for="(uid, index) in learningStore.recommendedNodes" :key="uid" class="full-path-item">
          <div class="item-step" :class="nodeStatusClass(uid)">{{ index + 1 }}</div>
          <div class="item-content">
            <strong>{{ nodeLabels[uid] || uidLabel(uid) }}</strong>
            <p class="muted small">{{ nodeMeta(uid)?.summary || '' }}</p>
          </div>
          <div class="item-status">
            <el-tag size="small" :type="nodeStatusTagType(uid)" effect="plain">
              {{ nodeStatusLabel(uid) }}
            </el-tag>
          </div>
          <div class="item-actions">
            <el-button
              v-if="!completedIds.has(uid)"
              type="primary"
              size="small"
              @click="$router.push({ path: '/exercise', query: { node_id: uid } })"
            >
              开始练习
            </el-button>
            <el-button
              size="small"
              @click="$router.push({ path: '/graph', query: { node_id: uid } })"
            >
              查看图谱
            </el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- ===== 学习推荐理由（简化版） ===== -->
    <el-card v-if="hasLearningGoal" class="reason-card" shadow="never">
      <template #header>
        <div class="panel-title">
          <span>💡 为什么推荐这些内容？</span>
        </div>
      </template>
      <ul class="reason-list">
        <li v-for="(reason, i) in simplifiedReasons" :key="i">
          {{ reason }}
        </li>
      </ul>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { QuestionFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { getGraphNode, getSubgraph } from '@/api/graph'
import { useLearningStore } from '@/stores/learning'
import { useProfileStore } from '@/stores/profile'
import { localizeText, uidLabel } from '@/utils/format'

const profileStore = useProfileStore()
const learningStore = useLearningStore()
const loading = ref(false)
const showFullPath = ref(false)
const nodeLabels = ref<Record<string, string>>({})
const nodeMetadata = ref<Record<string, Record<string, any>>>({})
const prereqEdges = ref<Map<string, string[]>>(new Map())

// ===== 计算属性 =====
const weakNodeIds = computed(() => profileStore.studentProfileInput.weak_points || [])
const completedIds = computed(() => new Set(profileStore.profile?.progress.completed_node_ids || []))
const inProgressIds = computed(() => new Set(profileStore.profile?.progress.in_progress_node_ids || []))
const masteryMap = computed(() => profileStore.profile?.node_mastery || {})

const hasLearningGoal = computed(() => {
  const goal = profileStore.profile?.learning_goal?.description
  const inputGoal = profileStore.studentProfileInput.goal
  return !!(goal || inputGoal)
})

const learningGoalText = computed(() => {
  return profileStore.profile?.learning_goal?.description || profileStore.studentProfileInput.goal || '未设置'
})

const completedCount = computed(() => completedIds.value.size)
const inProgressCount = computed(() => inProgressIds.value.size)
const recommendedCount = computed(() => learningStore.recommendedNodes.length - completedCount.value - inProgressCount.value)

// 当前正在学的节点
const currentNodes = computed(() => {
  return learningStore.recommendedNodes.filter(uid =>
    inProgressIds.value.has(uid) && !completedIds.value.has(uid)
  )
})

// 薄弱点节点
const weakNodes = computed(() => {
  return learningStore.recommendedNodes.filter(uid =>
    weakNodeIds.value.includes(uid) && !completedIds.value.has(uid)
  ).slice(0, 3) // 最多显示3个
})

// 推荐下一步节点（排除已完成和进行中的）
const nextNodes = computed(() => {
  const nodes = learningStore.recommendedNodes.filter(uid =>
    !completedIds.value.has(uid) && !inProgressIds.value.has(uid)
  )
  // 如果没有推荐节点，显示前2个推荐节点
  return nodes.length ? nodes.slice(0, 2) : learningStore.recommendedNodes.slice(0, 2)
})

// 简化的推荐理由（面向新用户）
const simplifiedReasons = computed(() => {
  const reasons: string[] = []
  const goal = learningGoalText.value

  if (goal) {
    reasons.push(`你的学习目标是：${goal}`)
  }

  if (weakNodes.value.length) {
    reasons.push(`系统发现你在「${nodeLabels.value[weakNodes.value[0]] || '某些知识点'}」上需要加强`)
  }

  if (currentNodes.value.length) {
    reasons.push(`你当前正在学习「${nodeLabels.value[currentNodes.value[0]] || '当前章节'}」，完成后继续下一章节`)
  }

  if (nextNodes.value.length) {
    reasons.push(`建议接下来学习「${nodeLabels.value[nextNodes.value[0]] || '推荐内容'}」`)
  }

  return reasons.length ? reasons : ['完成学习目标设置后，系统会为你推荐学习路径']
})

// ===== 工具函数 =====
function nodeMeta(uid: string): Record<string, any> | undefined {
  return nodeMetadata.value[uid]
}

function prereqCount(uid: string): number {
  return prereqEdges.value.get(uid)?.length || 0
}

function nodeStatusClass(uid: string): Record<string, boolean> {
  return {
    mastered: completedIds.value.has(uid),
    in_progress: inProgressIds.value.has(uid) && !completedIds.value.has(uid),
    weak: weakNodeIds.value.includes(uid),
    recommended: !completedIds.value.has(uid) && !inProgressIds.value.has(uid) && !weakNodeIds.value.includes(uid),
  }
}

function nodeStatusLabel(uid: string): string {
  if (completedIds.value.has(uid)) return '已掌握'
  if (inProgressIds.value.has(uid)) return '进行中'
  if (weakNodeIds.value.includes(uid)) return '需加强'
  return '待学习'
}

function nodeStatusTagType(uid: string): string {
  if (completedIds.value.has(uid)) return 'success'
  if (inProgressIds.value.has(uid)) return 'primary'
  if (weakNodeIds.value.includes(uid)) return 'warning'
  return 'info'
}

function nodeReason(uid: string): string {
  const mastery = masteryMap.value[uid]
  if (weakNodeIds.value.includes(uid)) {
    const src = profileStore.dashboard?.weak_point_rank?.find(w => w.label === uid)?.source
    const srcText = src === 'diagnosed' ? '练习表现' : '自我评估'
    return `这是你的薄弱点（来自${srcText}），建议优先加强`
  }
  if (mastery) {
    return `掌握度 ${Math.round(mastery.mastery_score * 100)}%，建议通过练习巩固`
  }
  return '推荐学习此知识点'
}

// ===== 数据加载 =====
async function loadPath() {
  loading.value = true
  try {
    if (!profileStore.profile) await profileStore.initFromAuth()
    await profileStore.refreshDashboard()
    await learningStore.loadDiagnosis(profileStore.studentProfileInput, profileStore.profile?.node_mastery || {})

    const nodes = learningStore.recommendedNodes
    if (!nodes.length) return

    // 加载节点元数据
    const labels: Record<string, string> = {}
    const meta: Record<string, Record<string, any>> = {}
    await Promise.all(nodes.map(async (uid) => {
      try {
        const node = await getGraphNode(uid)
        labels[uid] = node.properties?.name || uidLabel(uid)
        meta[uid] = node.properties || {}
      } catch {
        labels[uid] = uidLabel(uid)
      }
    }))
    nodeLabels.value = labels
    nodeMetadata.value = meta

    // 加载前置关系
    try {
      if (nodes[0]) {
        const subgraph = await getSubgraph(nodes[0], { depth: 2, limit: 200 })
        const edges = new Map<string, string[]>()
        for (const rel of subgraph.relationships || []) {
          if (rel.type === 'PREREQUISITE') {
            const list = edges.get(rel.source_uid) || []
            list.push(rel.target_uid)
            edges.set(rel.source_uid, list)
          }
        }
        prereqEdges.value = edges
      }
    } catch { prereqEdges.value = new Map() }

    ElMessage.success(`已加载学习路径（${nodes.length} 个知识点）`)
  } catch (error) {
    console.error('加载学习路径失败:', error)
  } finally {
    loading.value = false
  }
}

function useQuickStart() {
  // 快速体验模式：使用示例路径
  ElMessage.info('正在加载示例学习路径...')
  loadPath()
}

async function selectNode(uid: string) {
  await learningStore.loadEvidence(uid, profileStore.studentProfileInput, profileStore.studentId)
}

onMounted(loadPath)
</script>

<style scoped>
.page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

/* ===== 页面标题 ===== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-title h1 {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* ===== 引导卡片 ===== */
.guide-card {
  margin-bottom: 20px;
  border: 2px dashed #818cf8;
  background: linear-gradient(135deg, #faf5ff 0%, #f0f4ff 100%);
}

.guide-content {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 8px;
}

.guide-icon {
  font-size: 48px;
  flex-shrink: 0;
}

.guide-text h3 {
  margin: 0 0 8px;
  font-size: 18px;
  color: #4f46e5;
}

.guide-text p {
  margin: 0;
  color: #64748b;
}

.guide-actions {
  display: flex;
  gap: 12px;
  margin-left: auto;
}

/* ===== 目标摘要卡片 ===== */
.goal-summary-card {
  margin-bottom: 20px;
  background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
  border: 1px solid #86efac;
}

.goal-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.goal-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.goal-label {
  font-weight: 600;
  color: #166534;
}

.goal-text {
  color: #15803d;
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.goal-stats {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 24px;
  font-weight: 700;
  color: #166534;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: #d1fae5;
}

/* ===== 三栏式布局 ===== */
.path-three-columns {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.path-column {
  background: #fafafa;
  border-radius: 12px;
  padding: 16px;
  min-height: 280px;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.column-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
}

.col-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.col-badge.current {
  background: #dbeafe;
  color: #1d4ed8;
}

.col-badge.weak {
  background: #fef3c7;
  color: #b45309;
}

.col-badge.next {
  background: #dcfce7;
  color: #15803d;
}

.column-nodes {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.node-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid #e2e8f0;
  background: #fff;
}

.node-card:hover {
  border-color: #818cf8;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.1);
  transform: translateX(4px);
}

.node-card.current {
  border-left: 4px solid #3b82f6;
}

.node-card.weak {
  border-left: 4px solid #f59e0b;
}

.node-card.recommended {
  border-left: 4px solid #10b981;
}

.node-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.node-content {
  flex: 1;
  min-width: 0;
}

.node-content strong {
  display: block;
  font-size: 14px;
  margin-bottom: 4px;
}

.node-desc {
  font-size: 12px;
  color: #64748b;
  margin: 0 0 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.node-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.node-arrow {
  font-size: 18px;
  color: #cbd5e1;
  flex-shrink: 0;
}

.empty-column {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 32px 16px;
  color: #64748b;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

/* ===== 完整路径卡片 ===== */
.full-path-card {
  margin-bottom: 20px;
}

.full-path-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.path-timeline {
  padding: 16px 0;
  overflow-x: auto;
}

.timeline-track {
  display: flex;
  align-items: center;
  gap: 0;
  min-width: min-content;
}

.timeline-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  position: relative;
  min-width: 100px;
}

.timeline-step {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  z-index: 1;
}

.timeline-node.mastered .timeline-step {
  background: #10b981;
  color: #fff;
}

.timeline-node.in_progress .timeline-step {
  background: #3b82f6;
  color: #fff;
}

.timeline-node.weak .timeline-step {
  background: #f59e0b;
  color: #fff;
}

.timeline-connector {
  position: absolute;
  top: 16px;
  left: calc(50% + 16px);
  width: calc(100% - 32px);
  height: 2px;
  background: #e2e8f0;
  z-index: 0;
}

.timeline-info {
  margin-top: 8px;
  text-align: center;
}

.timeline-name {
  display: block;
  font-size: 12px;
  font-weight: 500;
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-status {
  font-size: 11px;
  color: #94a3b8;
}

.full-path-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
  border-top: 1px solid #e2e8f0;
  padding-top: 16px;
}

.full-path-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 8px;
  background: #f8fafc;
}

.item-step {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12px;
  flex-shrink: 0;
}

.item-step.mastered {
  background: #10b981;
  color: #fff;
}

.item-step.in_progress {
  background: #3b82f6;
  color: #fff;
}

.item-step.weak {
  background: #f59e0b;
  color: #fff;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-content strong {
  display: block;
  font-size: 14px;
}

.item-status {
  flex-shrink: 0;
}

.item-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* ===== 推荐理由卡片 ===== */
.reason-card {
  background: linear-gradient(135deg, #fefce8 0%, #fef9c3 100%);
  border: 1px solid #fef08a;
}

.reason-list {
  margin: 0;
  padding-left: 20px;
  line-height: 2;
  color: #713f12;
}

.reason-list li {
  padding-left: 8px;
}

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .path-three-columns {
    grid-template-columns: 1fr;
  }

  .goal-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .goal-stats {
    width: 100%;
    justify-content: space-around;
  }
}
</style>
