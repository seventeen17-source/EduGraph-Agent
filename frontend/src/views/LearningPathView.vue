<template>
  <div class="page">
    <!-- ===== 页面标题 ===== -->
    <div class="page-title">
      <div class="page-title-left">
        <div class="page-title-icon">🚀</div>
        <div class="page-title-info">
          <h1>我的学习路径</h1>
          <div class="muted">基于你的目标、掌握度和薄弱点，系统会动态推荐下一批学习任务</div>
        </div>
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
          <h3>还没有学习路径</h3>
          <p>设置学习目标或做一次诊断评估，系统会为你推荐学习路径。</p>
        </div>
        <div class="guide-actions">
          <el-button type="primary" @click="$router.push('/profile/chat')">
            设置学习目标
          </el-button>
          <el-button @click="$router.push('/exercise')">做诊断评估</el-button>
        </div>
      </div>
    </el-card>

    <!-- ===== 学习目标摘要（始终显示给有目标的用户） ===== -->
    <el-card v-if="hasLearningGoal" class="goal-summary-card" shadow="never">
      <div class="goal-row">
        <div class="goal-info">
          <span class="goal-label">🎯 学习目标</span>
          <span v-if="!hasMultipleGoals" class="goal-text">{{ learningGoalText }}</span>
          <el-select
            v-else
            v-model="selectedGoal"
            placeholder="选择学习目标"
            size="small"
            class="goal-select"
            @change="onGoalChange"
          >
            <el-option
              v-for="goal in availableGoals"
              :key="goal"
              :label="goal"
              :value="goal"
            />
          </el-select>
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

    <!-- ===== 有目标但无推荐路径时的引导 ===== -->
    <el-card
      v-if="hasLearningGoal && !loading && !learningStore.recommendedNodes.length"
      class="guide-card"
      shadow="never"
    >
      <div class="guide-content">
        <div class="guide-icon">🚀</div>
        <div class="guide-text">
          <h3>还没有学习路径</h3>
          <p>做一次诊断评估，系统会根据你的表现推荐个性化学习路径。</p>
        </div>
        <div class="guide-actions">
          <el-button type="primary" @click="$router.push('/exercise')">做诊断评估</el-button>
        </div>
      </div>
    </el-card>

    <!-- ===== 主内容：三栏式布局（回退，当后端未返回 recommendations 时使用） ===== -->
    <div v-if="hasLearningGoal && learningStore.recommendedNodes.length && !hasRecommendations" class="path-three-columns">
      <!-- 第一栏：当前正在学 -->
      <div class="path-column">
        <div class="column-header">
          <div class="column-title">
            <span class="col-badge current">进行中</span>
            <span>当前建议</span>
          </div>
          <el-tooltip content="当前最适合优先处理的知识点，不代表必须按固定章节顺序学习">
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
              <strong>{{ displayNodeLabel(nodeLabels[uid] || uid) }}</strong>
              <p class="node-desc">{{ localizeText(nodeMeta(uid)?.summary || '暂无简介') }}</p>
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
          <p class="muted small">可以继续查看推荐学习或薄弱点复习</p>
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
              <strong>{{ displayNodeLabel(nodeLabels[uid] || uid) }}</strong>
              <p class="node-desc">{{ localizeText(nodeReason(uid)) }}</p>
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
            <span>推荐队列</span>
          </div>
          <el-tooltip content="根据学习目标、前置知识、练习表现和掌握度动态排序的候选任务">
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
              <strong>{{ displayNodeLabel(nodeLabels[uid] || uid) }}</strong>
              <p class="node-desc">{{ localizeText(nodeMeta(uid)?.summary || '暂无简介') }}</p>
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
          <p>当前推荐队列已完成！</p>
          <p class="muted small">你已掌握所有推荐知识点</p>
        </div>
      </div>
    </div>

    <!-- ===== 主内容：基于后端 recommendations 的分组布局（Task 4） ===== -->
    <div v-if="hasLearningGoal && hasRecommendations" class="path-recommendations-layout">
      <!-- 当前建议（突出显示） -->
      <el-card class="current-reco-card" shadow="never">
        <div class="column-header">
          <div class="column-title">
            <span class="col-badge current">进行中</span>
            <span>当前建议</span>
          </div>
          <el-tooltip content="当前最适合优先处理的知识点，基于后端诊断推荐">
            <el-icon><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>
        <div v-if="currentRecommendation" class="current-reco-body" @click="selectRecommendation(currentRecommendation)">
          <div class="node-icon current-icon">📖</div>
          <div class="current-reco-content">
            <div class="current-reco-head">
              <strong>{{ recommendationNodeName(currentRecommendation) }}</strong>
              <el-tag size="small" type="primary" effect="dark">
                {{ recommendationTypeLabel(currentRecommendation.recommendation_type) }}
              </el-tag>
              <el-tag v-if="currentRecommendation.difficulty" size="small" effect="plain">
                {{ currentRecommendation.difficulty }}
              </el-tag>
            </div>
            <p class="reco-reason">{{ localizeText(currentRecommendation.reason) }}</p>
            <div v-if="evidenceSourceText(currentRecommendation)" class="reco-evidence">
              <el-icon><QuestionFilled /></el-icon>
              <span>证据：{{ evidenceSourceText(currentRecommendation) }}</span>
            </div>
            <div class="node-tags">
              <el-tag v-if="inProgressIds.has(currentRecommendation.node_id)" size="small" type="primary" effect="plain">进行中</el-tag>
              <el-tag v-if="currentRecommendation.chapter" size="small" effect="plain">{{ currentRecommendation.chapter }}</el-tag>
              <el-tag size="small" effect="plain">{{ nodeMeta(currentRecommendation.node_id)?.estimated_minutes || 30 }}分钟</el-tag>
            </div>
          </div>
        </div>
        <div v-else class="empty-column">
          <div class="empty-icon">🎉</div>
          <p>暂无当前建议</p>
          <p class="muted small">可以查看下方推荐分组</p>
        </div>
      </el-card>

      <!-- 按推荐类型分组 -->
      <div class="reco-groups-grid">
        <div
          v-for="group in orderedGroups"
          :key="group.type"
          class="path-column reco-group-column"
        >
          <div class="column-header">
            <div class="column-title">
              <span class="col-badge" :class="group.badgeClass">
                {{ group.icon }} {{ group.label }}
              </span>
              <span class="reco-group-count">{{ group.items.length }}</span>
            </div>
            <el-tooltip :content="`${group.label}：${group.items.length} 个知识点`">
              <el-icon><QuestionFilled /></el-icon>
            </el-tooltip>
          </div>

          <div class="column-nodes">
            <div
              v-for="item in group.items"
              :key="item.node_id"
              class="node-card"
              :class="group.badgeClass"
              @click="selectRecommendation(item)"
            >
              <div class="node-icon">{{ group.icon }}</div>
              <div class="node-content">
                <div class="reco-node-head">
                  <strong>{{ recommendationNodeName(item) }}</strong>
                  <el-tag v-if="item.difficulty" size="small" effect="plain">{{ item.difficulty }}</el-tag>
                </div>
                <p class="node-desc reco-reason">{{ localizeText(item.reason) }}</p>
                <div v-if="evidenceSourceText(item)" class="reco-evidence">
                  <el-icon><QuestionFilled /></el-icon>
                  <span>{{ evidenceSourceText(item) }}</span>
                </div>
                <div class="node-tags">
                  <el-tag v-if="completedIds.has(item.node_id)" size="small" type="success" effect="plain">已掌握</el-tag>
                  <el-tag v-if="item.chapter" size="small" effect="plain">{{ item.chapter }}</el-tag>
                  <el-tag v-if="item.prerequisites?.length" size="small" type="info" effect="plain">
                    需先学 {{ item.prerequisites.length }} 个
                  </el-tag>
                  <el-tag size="small" effect="plain">{{ nodeMeta(item.node_id)?.estimated_minutes || 30 }}分钟</el-tag>
                </div>
              </div>
              <div class="node-arrow">→</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 完整路径列表（可展开） ===== -->
    <el-card v-if="hasLearningGoal && learningStore.recommendedNodes.length" class="full-path-card" shadow="never">
      <template #header>
        <div class="full-path-header">
          <span>📋 完整推荐队列（共 {{ learningStore.recommendedNodes.length }} 个节点）</span>
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
              <span class="timeline-name">{{ displayNodeLabel(nodeLabels[uid] || uid) }}</span>
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
            <strong>{{ displayNodeLabel(nodeLabels[uid] || uid) }}</strong>
            <p class="muted small">{{ localizeText(nodeMeta(uid)?.summary || '') }}</p>
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
          {{ localizeText(reason) }}
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
import type { RecommendationItem } from '@/types/diagnosis'
import { displayNodeLabel, displaySourceLabel, localizeText } from '@/utils/format'

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

// ===== 多目标支持 =====
const availableGoals = computed<string[]>(() => {
  return profileStore.profile?.learning_goal?.goals || []
})

const hasMultipleGoals = computed(() => availableGoals.value.length > 1)

const selectedGoal = ref<string>('')

const effectiveTargetGoal = computed<string | null>(() => {
  if (!hasMultipleGoals.value) return null
  return selectedGoal.value || null
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

// ===== 后端 recommendations 分组（Task 4） =====
const recommendations = computed<RecommendationItem[]>(() => {
  return learningStore.diagnosis?.recommendations || []
})

const hasRecommendations = computed(() => recommendations.value.length > 0)

const currentNodeIdFromBackend = computed<string | null>(() => {
  return learningStore.diagnosis?.current_node_id || null
})

// 当前建议：优先 current_node_id → 进行中的节点 → 推荐队列第一项
const currentRecommendation = computed<RecommendationItem | null>(() => {
  if (!recommendations.value.length) return null
  // 1. 后端指定的 current_node_id
  if (currentNodeIdFromBackend.value) {
    const found = recommendations.value.find(r => r.node_id === currentNodeIdFromBackend.value)
    if (found) return found
  }
  // 2. 进行中的节点
  const inProgress = recommendations.value.find(r => inProgressIds.value.has(r.node_id))
  if (inProgress) return inProgress
  // 3. 取推荐队列第一项作为当前建议
  return recommendations.value[0]
})

// 推荐类型分组配置
const recommendationTypeConfig: Record<string, { label: string; icon: string; badgeClass: string; cardClass: string }> = {
  weak_point: { label: '薄弱补强', icon: '⚠️', badgeClass: 'weak', cardClass: 'weak' },
  prerequisite: { label: '前置补缺', icon: '🔗', badgeClass: 'prereq', cardClass: 'prereq' },
  goal_related: { label: '目标相关', icon: '🎯', badgeClass: 'goal', cardClass: 'goal' },
  forgetting_review: { label: '遗忘复习', icon: '🔁', badgeClass: 'review', cardClass: 'review' },
  mistake_related: { label: '错题关联', icon: '❌', badgeClass: 'mistake', cardClass: 'mistake' },
}

// 按类型分组（排除当前建议节点）
const groupedRecommendations = computed<Record<string, RecommendationItem[]>>(() => {
  const groups: Record<string, RecommendationItem[]> = {}
  for (const item of recommendations.value) {
    if (currentRecommendation.value && item.node_id === currentRecommendation.value.node_id) continue
    if (!groups[item.recommendation_type]) {
      groups[item.recommendation_type] = []
    }
    groups[item.recommendation_type].push(item)
  }
  return groups
})

// 按预定义顺序排列的分组（仅含有内容的分组）
const orderedGroups = computed(() => {
  const order = ['weak_point', 'prerequisite', 'goal_related', 'forgetting_review', 'mistake_related']
  return order
    .filter(type => groupedRecommendations.value[type]?.length)
    .map(type => ({
      type,
      label: recommendationTypeConfig[type]?.label || displaySourceLabel(type, '推荐类型'),
      icon: recommendationTypeConfig[type]?.icon || '📌',
      badgeClass: recommendationTypeConfig[type]?.badgeClass || 'default',
      items: groupedRecommendations.value[type],
    }))
})

// 简化的推荐理由（面向新用户）
const simplifiedReasons = computed(() => {
  const reasons: string[] = []
  const goal = learningGoalText.value

  if (goal) {
    reasons.push(`你的学习目标是：${goal}`)
  }

  // 优先使用后端 recommendations 的 reason
  if (hasRecommendations.value) {
    if (currentRecommendation.value) {
      reasons.push(`当前建议学习「${displayNodeLabel(currentRecommendation.value.node_name || nodeLabels.value[currentRecommendation.value.node_id] || currentRecommendation.value.node_id, '当前节点')}」：${currentRecommendation.value.reason}`)
    }
    const weakGroup = groupedRecommendations.value['weak_point']
    if (weakGroup?.length) {
      reasons.push(`系统发现你在「${displayNodeLabel(weakGroup[0].node_name || weakGroup[0].node_id, '某些知识点')}」上需要加强（薄弱补强）`)
    }
    const reviewGroup = groupedRecommendations.value['forgetting_review']
    if (reviewGroup?.length) {
      reasons.push(`有 ${reviewGroup.length} 个知识点临近遗忘，建议及时复习`)
    }
  } else {
    // 回退到原有逻辑
    if (weakNodes.value.length) {
      reasons.push(`系统发现你在「${displayNodeLabel(nodeLabels.value[weakNodes.value[0]] || weakNodes.value[0], '某些知识点')}」上需要加强`)
    }
    if (currentNodes.value.length) {
      reasons.push(`你当前正在学习「${displayNodeLabel(nodeLabels.value[currentNodes.value[0]] || currentNodes.value[0], '当前建议')}」，完成后系统会继续调整推荐队列`)
    }
    if (nextNodes.value.length) {
      reasons.push(`建议接下来学习「${displayNodeLabel(nodeLabels.value[nextNodes.value[0]] || nextNodes.value[0], '推荐内容')}」`)
    }
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

// 推荐类型标签
function recommendationTypeLabel(type: string): string {
  return recommendationTypeConfig[type]?.label || displaySourceLabel(type, '推荐类型')
}

// 推荐类型图标
function recommendationTypeIcon(type: string): string {
  return recommendationTypeConfig[type]?.icon || '📌'
}

// 证据来源文本
function evidenceSourceText(item: RecommendationItem): string {
  if (!item.evidence) return ''
  const parts: string[] = []
  if (item.evidence.source) parts.push(displaySourceLabel(item.evidence.source, '推荐证据'))
  if (item.evidence.detail) parts.push(localizeText(item.evidence.detail))
  if (item.evidence.mastery != null) {
    parts.push(`掌握度 ${Math.round((item.evidence.mastery || 0) * 100)}%`)
  }
  if (item.evidence.last_attempt) {
    parts.push(`最近作答 ${item.evidence.last_attempt}`)
  }
  return localizeText(parts.join(' · '))
}

// 节点显示名（优先 recommendation 自带名称，回退到 nodeLabels）
function recommendationNodeName(item: RecommendationItem): string {
  return displayNodeLabel(item.node_name || nodeLabels.value[item.node_id] || item.node_id)
}

// ===== 数据加载 =====
async function loadPath() {
  loading.value = true
  try {
    if (!profileStore.profile) await profileStore.initFromAuth()
    await profileStore.refreshDashboard()
    if (!hasLearningGoal.value) {
      learningStore.diagnosis = null
      return
    }
    // 多目标：初始化选中目标（默认第一个）
    if (hasMultipleGoals.value && !selectedGoal.value) {
      selectedGoal.value = availableGoals.value[0]
    }
    await learningStore.loadDiagnosis(
      profileStore.studentProfileInput,
      profileStore.profile?.node_mastery || {},
      effectiveTargetGoal.value,
    )

    const nodes = learningStore.recommendedNodes
    if (!nodes.length) return

    // 加载节点元数据
    const labels: Record<string, string> = {}
    const meta: Record<string, Record<string, any>> = {}
    await Promise.all(nodes.map(async (uid) => {
      try {
        const node = await getGraphNode(uid)
        labels[uid] = displayNodeLabel(node.properties?.name || uid)
        meta[uid] = node.properties || {}
      } catch {
        labels[uid] = displayNodeLabel(uid)
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

async function selectNode(uid: string) {
  await learningStore.loadEvidence(uid, profileStore.studentProfileInput, profileStore.studentId)
}

async function selectRecommendation(item: RecommendationItem) {
  await selectNode(item.node_id)
}

// 多目标：切换目标后重新加载诊断推荐
async function onGoalChange() {
  loading.value = true
  try {
    await learningStore.loadDiagnosis(
      profileStore.studentProfileInput,
      profileStore.profile?.node_mastery || {},
      effectiveTargetGoal.value,
    )
    const nodes = learningStore.recommendedNodes
    if (nodes.length) {
      const labels: Record<string, string> = {}
      const meta: Record<string, Record<string, any>> = {}
      await Promise.all(nodes.map(async (uid) => {
        try {
          const node = await getGraphNode(uid)
          labels[uid] = displayNodeLabel(node.properties?.name || uid)
          meta[uid] = node.properties || {}
        } catch {
          labels[uid] = displayNodeLabel(uid)
        }
      }))
      nodeLabels.value = labels
      nodeMetadata.value = meta
    }
    ElMessage.success(`已切换到目标：${selectedGoal.value}`)
  } catch (error) {
    console.error('切换目标失败:', error)
  } finally {
    loading.value = false
  }
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

.goal-select {
  width: 240px;
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

/* ===== 推荐 reasons 布局（Task 4） ===== */
.path-recommendations-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.current-reco-card {
  border: 1px solid #bfdbfe;
  background: linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%);
}

.current-reco-body {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid #dbeafe;
  background: #fff;
}

.current-reco-body:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 12px rgba(59, 130, 246, 0.15);
}

.current-icon {
  font-size: 28px;
  color: #3b82f6;
}

.current-reco-content {
  flex: 1;
  min-width: 0;
}

.current-reco-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.current-reco-head strong {
  font-size: 16px;
  color: #1e3a8a;
}

.reco-reason {
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
  margin: 0 0 8px;
  word-break: break-word;
}

.reco-evidence {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  margin: 4px 0 8px;
  padding: 6px 8px;
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 6px;
  line-height: 1.5;
  word-break: break-word;
}

.reco-evidence .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.reco-groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.reco-group-column {
  min-height: 200px;
}

.reco-group-count {
  font-size: 12px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 1px 8px;
  border-radius: 10px;
  margin-left: 4px;
}

.reco-node-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.reco-node-head strong {
  font-size: 14px;
}

/* 推荐类型 badge 配色 */
.col-badge.prereq {
  background: #ede9fe;
  color: #6d28d9;
}

.col-badge.goal {
  background: #dcfce7;
  color: #15803d;
}

.col-badge.review {
  background: #fef3c7;
  color: #b45309;
}

.col-badge.mistake {
  background: #fee2e2;
  color: #b91c1c;
}

.col-badge.default {
  background: #f1f5f9;
  color: #475569;
}

/* 节点卡片按类型左侧描边 */
.node-card.prereq {
  border-left: 4px solid #8b5cf6;
}

.node-card.goal {
  border-left: 4px solid #10b981;
}

.node-card.review {
  border-left: 4px solid #f59e0b;
}

.node-card.mistake {
  border-left: 4px solid #ef4444;
}

.node-card.default {
  border-left: 4px solid #94a3b8;
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
