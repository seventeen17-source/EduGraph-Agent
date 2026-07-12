<template>
  <div class="full-graph-wrapper">
    <!-- 工具栏 -->
    <div class="graph-toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchText"
          placeholder="搜索知识点..."
          size="small"
          clearable
          class="search-input"
          @input="onSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-popover trigger="click" placement="bottom-start" :width="200">
          <template #reference>
            <el-tag size="small" effect="plain" class="filter-tag">
              <el-icon><Filter /></el-icon> 章节 {{ activeChapterCount }}/6
            </el-tag>
          </template>
          <el-checkbox-group v-model="activeChapters" @change="onFilterChange">
            <el-checkbox v-for="ch in chapters" :key="ch" :label="ch" :value="ch">
              {{ chapterLabel(ch) }}
            </el-checkbox>
          </el-checkbox-group>
        </el-popover>
        <el-popover trigger="click" placement="bottom-start" :width="160">
          <template #reference>
            <el-tag size="small" effect="plain" class="filter-tag">
              <el-icon><Star /></el-icon> 难度 {{ minDiff }}-{{ maxDiff }}
            </el-tag>
          </template>
          <el-slider
            v-model="diffRange"
            range
            :min="1"
            :max="5"
            :marks="{ 1: '1★', 2: '2★', 3: '3★', 4: '4★', 5: '5★' }"
            @change="onFilterChange"
          />
        </el-popover>
        <el-tag
          v-for="status in activeLegends"
          :key="status.value"
          size="small"
          :effect="status.active ? 'dark' : 'plain'"
          :style="{ cursor: 'pointer', borderColor: status.color }"
          @click="toggleLegend(status.value)"
        >
          {{ status.label }}
        </el-tag>
      </div>
      <div class="toolbar-right">
        <el-button-group size="small">
          <el-button @click="zoomIn"><el-icon><ZoomIn /></el-icon></el-button>
          <el-button @click="zoomOut"><el-icon><ZoomOut /></el-icon></el-button>
          <el-button @click="fitView"><el-icon><FullScreen /></el-icon></el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 画布 -->
    <div ref="chartRef" class="full-graph-canvas" @contextmenu.prevent="onContextMenu" />
    <div class="node-count">{{ filteredCount }} / {{ props.nodes.length }} 个节点</div>

    <!-- 右键菜单 -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      @click.stop
    >
      <div class="ctx-header">{{ contextMenu.node ? nodeName(contextMenu.node) : '' }}</div>
      <div class="ctx-item" @click="emitAction('generateResources')">
        <el-icon><Document /></el-icon> 生成学习资源
      </div>
      <div class="ctx-item" @click="emitAction('viewExercises')">
        <el-icon><Notebook /></el-icon> 查看配套练习
      </div>
      <div class="ctx-item" @click="emitAction('askQuestion')">
        <el-icon><ChatDotRound /></el-icon> 向学习助手提问
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ChatDotRound, Document, Filter, FullScreen, Notebook, Search, Star, ZoomIn, ZoomOut } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

import type { GraphNode } from '@/types/graph'
import { nodeName } from '@/utils/format'

const props = defineProps<{
  nodes: GraphNode[]
  masteryMap?: Record<string, string>
  weakPoints?: string[]
}>()

const emit = defineEmits<{
  select: [node: GraphNode]
  generateResources: [node: GraphNode]
  viewExercises: [node: GraphNode]
  askQuestion: [node: GraphNode]
}>()

// ---- 搜索与筛选 ----
const searchText = ref('')
const activeChapters = ref<string[]>(['ch01', 'ch02', 'ch03', 'ch04', 'ch05', 'ch06'])
const diffRange = ref<[number, number]>([1, 5])
const activeLegends = reactive([
  { value: 'mastered', label: '已掌握', color: '#10b981', active: true },
  { value: 'in_progress', label: '进行中', color: '#3b82f6', active: true },
  { value: 'needs_review', label: '需复习', color: '#f59e0b', active: true },
  { value: 'recommended', label: '待学习', color: '#94a3b8', active: true },
])

const chapters = ['ch01', 'ch02', 'ch03', 'ch04', 'ch05', 'ch06']
const minDiff = computed(() => diffRange.value[0])
const maxDiff = computed(() => diffRange.value[1])
const activeChapterCount = computed(() => activeChapters.value.length)

const MAX_VISIBLE_LABELS = 60

const filteredNodes = computed<GraphNode[]>(() => {
  let result = props.nodes

  // 章节筛选
  if (activeChapters.value.length < 6) {
    const set = new Set(activeChapters.value)
    result = result.filter(n => {
      const ch = n.properties?.chapter_id as string || ''
      return set.has(ch)
    })
  }

  // 难度筛选
  result = result.filter(n => {
    const diff = (n.properties?.difficulty as number) || 3
    return diff >= minDiff.value && diff <= maxDiff.value
  })

  // 搜索
  const q = searchText.value.trim().toLowerCase()
  if (q) {
    result = result.filter(n => {
      const name = nodeName(n).toLowerCase()
      const summary = ((n.properties?.summary as string) || '').toLowerCase()
      const keywords = ((n.properties?.keywords as string[]) || []).join(' ').toLowerCase()
      const aliases = ((n.properties?.aliases as string[]) || []).join(' ').toLowerCase()
      return name.includes(q) || summary.includes(q) || keywords.includes(q) || aliases.includes(q)
    })
  }

  // 图例状态筛选
  const activeStatuses = new Set(activeLegends.filter(l => l.active).map(l => l.value))
  if (activeStatuses.size < 4) {
    result = result.filter(n => activeStatuses.has(getNodeStatus(n.uid)))
  }

  return result
})

const filteredCount = computed(() => filteredNodes.value.length)

function onSearch() { updateChart() }
function onFilterChange() { updateChart() }

function toggleLegend(value: string) {
  const item = activeLegends.find(l => l.value === value)
  if (item) item.active = !item.active
  updateChart()
}

// ---- 状态判断 ----
function getNodeStatus(uid: string): string {
  if (props.weakPoints?.includes(uid)) return 'needs_review'
  const m = props.masteryMap?.[uid]
  if (m === 'advanced') return 'mastered'
  if (m === 'intermediate') return 'in_progress'
  if (m === 'weak' || m === 'basic') return 'needs_review'
  return 'recommended'
}

function getNodeColor(uid: string): string {
  const status = getNodeStatus(uid)
  if (status === 'mastered') return '#10b981'
  if (status === 'in_progress') return '#3b82f6'
  if (status === 'needs_review') return '#f59e0b'
  return '#94a3b8'
}

function getNodeSize(node: GraphNode): number {
  const diff = (node.properties?.difficulty as number) || 3
  const base = node.uid === focusedNode.value ? 40 : 28
  return base + diff * 3
}

function getNodeOpacity(uid: string): number {
  if (!focusedNode.value) return 1
  return uid === focusedNode.value ? 1 : 0.2
}

// ---- 聚焦 ----
const focusedNode = ref<string | null>(null)

function onNodeClick(params: any) {
  const node = params.data?.node as GraphNode | undefined
  if (!node) return
  if (focusedNode.value === node.uid) {
    // 双击同一个节点 → 取消聚焦
    focusedNode.value = null
  } else {
    focusedNode.value = node.uid
  }
  updateChart()
  emit('select', node)
}

// ---- 缩放 ----
function zoomIn() { chart?.dispatchAction({ type: 'restore' }) }
function zoomOut() { chart?.dispatchAction({ type: 'restore' }) }
function fitView() {
  chart?.dispatchAction({ type: 'restore' })
  focusedNode.value = null
  updateChart()
}

// ---- 右键菜单 ----
const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const contextMenu = reactive({
  visible: false, x: 0, y: 0, node: null as GraphNode | null,
})

function onContextMenu(params: any) {
  const event = params.event as MouseEvent
  const node = params.data?.node as GraphNode | undefined
  if (!node) return
  contextMenu.node = node
  contextMenu.x = event.offsetX + 10
  contextMenu.y = event.offsetY + 10
  contextMenu.visible = true
}

function closeMenu() { contextMenu.visible = false; contextMenu.node = null }

function emitAction(action: 'generateResources' | 'viewExercises' | 'askQuestion') {
  if (contextMenu.node) emit(action as any, contextMenu.node)
  closeMenu()
}

// ---- ECharts ----
function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.on('click', onNodeClick)
  chart.on('contextmenu', onContextMenu)
  chart.getZr().on('click', (e: any) => {
    if (!e.target) { focusedNode.value = null; closeMenu(); updateChart() }
  })
  updateChart()
}

function updateChart() {
  if (!chart) return

  const visible = new Set(filteredNodes.value.map(n => n.uid))
  const showLabels = filteredNodes.value.length <= MAX_VISIBLE_LABELS

  const seriesData = props.nodes.map(dn => {
    const sv = getNodeSize(dn)
    return {
      id: dn.uid, name: nodeName(dn), uid: dn.uid, node: dn,
      value: sv,
      symbolSize: sv,
      itemStyle: {
        color: getNodeColor(dn.uid),
        opacity: getNodeOpacity(dn.uid),
        borderColor: focusedNode.value === dn.uid ? '#1e293b' : '#fff',
        borderWidth: focusedNode.value === dn.uid ? 3 : 1,
      },
      label: {
        show: showLabels && visible.has(dn.uid) && !(focusedNode.value && dn.uid !== focusedNode.value),
      },
    }
  })

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#e2e8f0',
      textStyle: { color: '#1e293b', fontSize: 13 },
      formatter: (p: any) => {
        const n = p.data?.node as GraphNode
        if (!n) return ''
        const summary = (n.properties?.summary as string) || '暂无摘要'
        const diff = '★'.repeat((n.properties?.difficulty as number) || 3)
        const ch = (n.properties?.chapter_id as string) || '?'
        const type = (n.properties?.node_type as string) || '知识点'
        const status = getNodeStatus(n.uid)
        const labels: Record<string, string> = {
          mastered: '✓ 已掌握', in_progress: '⚡ 进行中',
          needs_review: '⚠ 需复习', recommended: '○ 待学习'
        }
        return `<b>${nodeName(n)}</b><br/>` +
          `<span style="color:#94a3b8">${type} | ${ch}章 | ${diff}</span><br/>` +
          `<span>${labels[status] || ''}</span><br/>` +
          `<div style="color:#64748b;margin-top:6px;max-width:240px">${summary}</div>`
      },
    },
    series: [{
      type: 'graph',
      layout: 'force',
      animation: true,
      draggable: true,
      force: { repulsion: 300, gravity: 0.1, edgeLength: [50, 150], layoutAnimation: true },
      roam: true,
      label: { show: showLabels, position: 'right', fontSize: 10, color: '#475569' },
      emphasis: {
        focus: 'self',
        itemStyle: { borderWidth: 3, shadowBlur: 16, shadowColor: 'rgba(59,130,246,0.5)' },
        scale: 1.3,
      },
      data: seriesData,
    }],
  }, true)
}

watch(
  () => [props.nodes, props.masteryMap, props.weakPoints],
  () => updateChart(),
  { deep: false },
)

const resizeChart = () => chart?.resize()
onMounted(() => {
  initChart()
  window.addEventListener('resize', resizeChart)
  document.addEventListener('click', closeMenu)
})
onBeforeUnmount(() => {
  chart?.dispose()
  window.removeEventListener('resize', resizeChart)
  document.removeEventListener('click', closeMenu)
})

function chapterLabel(ch: string) {
  const labels: Record<string, string> = {
    ch01: '1.导论与评估', ch02: '2.数学基础', ch03: '3.线性模型',
    ch04: '4.监督学习', ch05: '5.无监督学习', ch06: '6.神经网络',
  }
  return labels[ch] || ch
}
</script>

<style scoped>
.full-graph-wrapper {
  position: relative;
  background: #f8fafc;
  border-radius: 12px;
  overflow: hidden;
}

.graph-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.search-input {
  width: 200px;
}

.filter-tag {
  cursor: pointer;
}

.toolbar-right {
  display: flex;
  gap: 6px;
}

.full-graph-canvas {
  width: 100%;
  height: 520px;
  cursor: default;
}

.node-count {
  position: absolute;
  bottom: 10px;
  left: 14px;
  font-size: 11px;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.8);
  padding: 2px 10px;
  border-radius: 10px;
}

.context-menu {
  position: absolute;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 6px 0;
  z-index: 9999;
  min-width: 170px;
}

.ctx-header {
  padding: 6px 14px 6px;
  font-size: 11px;
  color: #94a3b8;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 4px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ctx-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 13px;
  color: #334155;
  transition: background 0.15s;
}

.ctx-item:hover { background: #f1f5f9; color: #3b82f6; }
</style>
