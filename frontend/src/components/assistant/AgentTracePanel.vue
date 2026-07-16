<template>
  <el-card class="section-card trace-panel-card" shadow="never">
    <template #header>
      <div class="card-header">
        <el-icon><Cpu /></el-icon>
        <span>LangGraph 编排引擎</span>
        <el-tag v-if="isRunning" type="primary" size="small" class="pulse-tag">
          {{ runningNodeLabel || '运行中' }}
        </el-tag>
        <el-tag v-else-if="hasCompleted" type="success" size="small">
          完成 {{ doneCount }}/{{ activeCount }} 节点
        </el-tag>
      </div>
    </template>

    <!-- 执行流程 -->
    <div class="graph-flow">
      <div
        v-for="(item, idx) in displayNodes"
        :key="item.node"
        class="flow-node"
        :class="{
          running: item.status === 'running',
          done: item.status === 'done',
          failed: item.status === 'failed',
          pending: item.status === 'pending',
          hidden: item.status === 'pending' && !showAllNodes,
        }"
      >
        <!-- 连接线 -->
        <div
          v-if="idx > 0 && displayNodes[idx - 1].status !== 'pending'"
          class="flow-connector"
          :class="{
            active: item.status !== 'pending',
            done: displayNodes[idx - 1].status === 'done',
          }"
        >
          <div class="connector-line" />
          <div class="connector-arrow">→</div>
        </div>

        <!-- 节点卡片 -->
        <div class="node-card" @click="toggleDetail(item.node)">
          <div class="node-indicator">
            <!-- pending: 空心圆 -->
            <div v-if="item.status === 'pending'" class="dot pending-dot" />
            <!-- running: 脉冲圆 -->
            <div v-else-if="item.status === 'running'" class="dot running-dot">
              <div class="pulse-ring" />
            </div>
            <!-- done: 勾 -->
            <el-icon v-else-if="item.status === 'done'" class="done-icon"><Check /></el-icon>
            <!-- failed: 叉 -->
            <el-icon v-else-if="item.status === 'failed'" class="failed-icon"><Close /></el-icon>
          </div>

          <div class="node-body">
            <div class="node-label">{{ localizeTraceText(item.label || item.node) }}</div>
            <div v-if="item.summary" class="node-summary">{{ localizeTraceText(item.summary) }}</div>
            <div v-else-if="item.status === 'running'" class="node-summary running-text">
              <span class="typing-dots">执行中...</span>
            </div>
          </div>

          <div v-if="item.summary" class="node-expand">
            <el-icon :size="14"><ArrowDown v-if="!expandedNodes.has(item.node)" /><ArrowUp v-else /></el-icon>
          </div>
        </div>

        <!-- 展开详情 -->
        <div v-if="expandedNodes.has(item.node) && item.summary" class="node-detail">
          {{ localizeTraceText(item.summary) }}
        </div>
      </div>
    </div>

    <!-- 展开/收起全部 -->
    <div class="flow-footer">
      <el-button
        v-if="hasPendingNodes"
        text
        size="small"
        @click="showAllNodes = !showAllNodes"
      >
        {{ showAllNodes ? '收起未执行节点' : `展开全部 ${pendingCount} 个节点` }}
      </el-button>
      <span v-if="isRunning" class="elapsed-time">
        已用 {{ elapsed }}s
      </span>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ArrowDown, ArrowUp, Check, Close, Cpu } from '@element-plus/icons-vue'
import type { LiveTraceItem } from '@/types/assistant'

const props = defineProps<{
  nodes: LiveTraceItem[]
  isRunning: boolean
  currentRunningNode: string | null
}>()

const showAllNodes = ref(false)
const expandedNodes = ref(new Set<string>())
const startTime = ref(Date.now())
const elapsed = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

// 启动/停止计时器
watch(
  () => props.isRunning,
  (running) => {
    if (running) {
      startTime.value = Date.now()
      elapsed.value = 0
      timer = setInterval(() => {
        elapsed.value = Math.floor((Date.now() - startTime.value) / 1000)
      }, 1000)
    } else {
      if (timer) {
        clearInterval(timer)
        timer = null
      }
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})

const displayNodes = computed(() => props.nodes)

const runningNodeLabel = computed(() => {
  const running = props.nodes.find((n) => n.status === 'running')
  return running ? localizeTraceText(running.label || running.node) : null
})

const hasCompleted = computed(() => props.nodes.some((n) => n.status === 'done'))
const doneCount = computed(() => props.nodes.filter((n) => n.status === 'done').length)
const activeCount = computed(() => props.nodes.filter((n) => n.status !== 'pending').length)
const pendingCount = computed(() => props.nodes.filter((n) => n.status === 'pending').length)
const hasPendingNodes = computed(() => pendingCount.value > 0)

function toggleDetail(node: string) {
  if (expandedNodes.value.has(node)) {
    expandedNodes.value.delete(node)
  } else {
    expandedNodes.value.add(node)
  }
}

function localizeTraceText(value: string) {
  let text = value || ''
  const replacements: Array<[RegExp, string]> = [
    [/concept_explain/g, '知识点讲解'],
    [/resource_generate/g, '资源生成'],
    [/exercise_help/g, '练习辅导'],
    [/path_plan/g, '路径规划'],
    [/general_learning_chat/g, '学习问答'],
    [/profile_update/g, '画像更新'],
    [/assessment_review/g, '评估复盘'],
    [/hybrid_rag:/g, '混合检索：'],
    [/prepare_query/g, '整理问题'],
    [/resolve_learning_target/g, '定位学习目标'],
    [/retrieve_graph_context/g, '检索图谱证据'],
    [/retrieve_semantic_context/g, '检索课程语义证据'],
    [/retrieve_memory_context/g, '检索学生记忆'],
    [/fuse_canonical_evidence/g, '融合规范证据'],
    [/grade_evidence/g, '评估证据质量'],
    [/finalize_evidence/g, '生成证据包'],
    [/ml_backpropagation/g, '反向传播'],
    [/ml_gradient_descent/g, '梯度下降'],
    [/ml_multilayer_neural_network/g, '多层神经网络'],
    [/code_backprop_demo/g, '反向传播代码案例'],
    [/Neo4j canonical evidence/g, 'Neo4j 规范证据'],
    [/canonical evidence/g, '规范证据'],
    [/EvidencePackage/g, '证据包'],
    [/HybridRAG/g, '混合检索'],
    [/FAQ/g, '常见问题'],
    [/coverage/g, '覆盖度'],
    [/relevance/g, '相关性'],
  ]
  for (const [pattern, replacement] of replacements) {
    text = text.replace(pattern, replacement)
  }
  return text
}

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.trace-panel-card :deep(.el-card__body) {
  padding: 12px 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.pulse-tag {
  animation: pulse 1.2s infinite;
  margin-left: auto;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.graph-flow {
  display: flex;
  flex-direction: column;
  max-height: 440px;
  overflow-y: auto;
  padding-right: 4px;
}

/* 连接线 */
.flow-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 18px;
  margin-left: 10px;
}

.connector-line {
  width: 2px;
  flex: 1;
  background: #e2e8f0;
  transition: background 0.3s;
}

.connector-line.active,
.connector-line.done {
  background: #10b981;
}

.connector-arrow {
  font-size: 10px;
  color: #94a3b8;
  line-height: 1;
}

/* 节点卡片 */
.flow-node {
  transition: all 0.3s ease;
}

.flow-node.hidden {
  display: none;
}

.node-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.node-card:hover {
  background: #f8fafc;
}

.flow-node.running .node-card {
  background: #eff6ff;
  border-color: #93c5fd;
}

.flow-node.done .node-card {
  background: #f0fdf4;
}

.flow-node.failed .node-card {
  background: #fef2f2;
  border-color: #fca5a5;
}

/* 指示器 */
.node-indicator {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.pending-dot {
  background: #e2e8f0;
}

.running-dot {
  background: #3b82f6;
  position: relative;
}

.pulse-ring {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid #3b82f6;
  animation: pulse-ring 1.2s infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(2); opacity: 0; }
}

.done-icon {
  color: #10b981;
  font-size: 16px;
}

.failed-icon {
  color: #ef4444;
  font-size: 16px;
}

/* 节点文本 */
.node-body {
  flex: 1;
  min-width: 0;
}

.node-label {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.3;
}

.flow-node.running .node-label {
  color: #1d4ed8;
}

.flow-node.done .node-label {
  color: #065f46;
}

.flow-node.failed .node-label {
  color: #991b1b;
}

.node-summary {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 3px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.running-text {
  color: #3b82f6;
}

.typing-dots::after {
  content: '';
  animation: dots 1.5s steps(3, end) infinite;
}

@keyframes dots {
  0% { content: ''; }
  33% { content: '.'; }
  66% { content: '..'; }
  100% { content: '...'; }
}

.node-expand {
  flex-shrink: 0;
  color: #94a3b8;
  margin-top: 2px;
}

.node-detail {
  margin: 4px 10px 8px 30px;
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  border-left: 2px solid #818cf8;
}

/* 底部 */
.flow-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
}

.elapsed-time {
  font-size: 11px;
  color: #94a3b8;
}
</style>
