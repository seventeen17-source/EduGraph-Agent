<template>
  <div ref="chartRef" class="graph-canvas" @contextmenu.prevent />
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { GraphNode, GraphRelationship, SubgraphResult } from '@/types/graph'
import { nodeName, pathLabel, relationLabel } from '@/utils/format'

const props = defineProps<{
  subgraph: SubgraphResult | null
  selectedUid?: string | null
  /** uid -> mastery level: weak/basic/intermediate/advanced */
  masteryMap?: Record<string, string>
  /** weak point node uids */
  weakPoints?: string[]
}>()

const emit = defineEmits<{
  select: [node: GraphNode]
  generateResources: [node: GraphNode]
  viewExercises: [node: GraphNode]
  askQuestion: [node: GraphNode]
  addToPath: [node: GraphNode]
}>()

const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
const resizeChart = () => chart?.resize()

// ---- visual helpers ----

const MASTERY_COLORS: Record<string, string> = {
  weak: '#E6A23C',      // 薄弱点：橙色
  basic: '#909399',     // 基础：灰色
  intermediate: '#409EFF', // 学习中：蓝色
  advanced: '#67C23A',  // 掌握：绿色
}

function nodeColor(node: GraphNode): string {
  const uid = node.uid
  // 薄弱点优先显示
  if (props.weakPoints?.includes(uid)) return '#F56C6C'
  // 按掌握度
  const mastery = props.masteryMap?.[uid]
  if (mastery && MASTERY_COLORS[mastery]) return MASTERY_COLORS[mastery]
  // 回退到 role
  const role = node.properties?.role_in_path
  if (role === 'core') return '#409EFF'
  if (role === 'bridge') return '#67C23A'
  if (role === 'advanced') return '#E6A23C'
  const type = node.properties?.node_type
  if (type === 'exercise') return '#F56C6C'
  return '#909399'
}

function nodeSymbol(node: GraphNode): string {
  const type = node.properties?.node_type
  if (type === 'exercise') return 'path://M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z'
  if (type === 'code_case') return 'path://M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z'
  return 'circle'
}

function nodeSize(node: GraphNode): number {
  const diff = node.properties?.difficulty || 1
  const base = node.uid === props.selectedUid ? 56 : 44
  return base + diff * 3
}

function nodeLabel(node: GraphNode): string {
  const name = nodeName(node)
  const type = node.properties?.node_type
  const icons: Record<string, string> = { exercise: '📝 ', code_case: '💻 ', document: '📄 ' }
  const icon = icons[type] || ''
  const diff = (node.properties?.difficulty as number) || 1
  const stars = '★'.repeat(diff) + '☆'.repeat(Math.max(0, 5 - diff))
  const chapter = (node.properties?.chapter as string) || ''
  const chapterPrefix = chapter ? `[${chapter}] ` : ''
  const isWeak = props.weakPoints?.includes(node.uid)
  const mastery = props.masteryMap?.[node.uid]
  let badge = ''
  if (isWeak) badge = '⚠️ '
  else if (mastery === 'advanced') badge = '✓ '
  else if (mastery === 'intermediate') badge = '~ '
  return `${icon}${badge}${chapterPrefix}${name}\n${stars}`
}

function relationColor(rel: GraphRelationship): string {
  if (rel.type === 'PREREQUISITE') return '#409EFF'
  if (rel.type === 'RELATED') return '#909399'
  if (rel.type === 'EXTENDS') return '#67C23A'
  if (rel.type === 'CONTRASTS') return '#E6A23C'
  return '#BFC6D1'
}

function relationWidth(rel: GraphRelationship): number {
  if (rel.type === 'PREREQUISITE') return 2.2
  if (rel.type === 'RELATED') return 1.4
  return 1.6
}

function relationDesc(rel: GraphRelationship): string {
  const label = relationLabel(rel.type)
  const from = pathLabel(rel.source_uid, rel.target_uid)
  const descriptions: Record<string, string> = {
    PREREQUISITE: '需要先掌握',
    RELATED: '与当前内容相关',
    EXTENDS: '在当前基础上扩展',
    CONTRACTS: '与当前内容形成对照',
    ASSESSES: '用于检验掌握程度',
    HAS_EXERCISE: '配套练习',
    SUPPORTS: '提供学习资料',
    PRACTICES: '代码实践案例',
    CITES_SOURCE: '引用自该来源',
  }
  return `${descriptions[rel.type] || label}：${from}`
}

// ---- render ----

function render() {
  if (!chart) return
  if (!props.subgraph || !props.subgraph.nodes.length) {
    chart.clear()
    chart.setOption({
      title: {
        text: '暂无可展开关系',
        subtext: '可以换一个知识点，或先补充该节点的图谱关系',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#606266', fontSize: 16, fontWeight: 500 },
        subtextStyle: { color: '#909399', fontSize: 12 }
      }
    })
    return
  }

  const centerX = chart.getWidth() / 2
  const centerY = chart.getHeight() / 2

  const nodes = props.subgraph.nodes.map((node) => ({
    id: node.uid,
    name: nodeLabel(node),
    value: node.properties?.difficulty || 1,
    fixed: node.uid === props.selectedUid,
    x: node.uid === props.selectedUid ? centerX : undefined,
    y: node.uid === props.selectedUid ? centerY : undefined,
    symbol: nodeSymbol(node),
    symbolSize: nodeSize(node),
    itemStyle: {
      color: nodeColor(node),
      borderColor: node.uid === props.selectedUid ? '#1f2d3d' : '#fff',
      borderWidth: node.uid === props.selectedUid ? 3 : 2
    },
    label: {
      show: true,
      formatter: '{b}',
      fontSize: node.uid === props.selectedUid ? 12 : 10,
      fontWeight: node.uid === props.selectedUid ? 'bold' : 'normal'
    },
    raw: node
  }))

  const links = props.subgraph.relationships.map((rel) => ({
    source: rel.source_uid,
    target: rel.target_uid,
    label: {
      show: rel.type === 'PREREQUISITE',
      formatter: relationLabel(rel.type),
      fontSize: 9,
      color: '#606266'
    },
    tooltip: { formatter: relationDesc(rel) },
    lineStyle: {
      color: relationColor(rel),
      type: rel.type === 'RELATED' ? 'dashed' : rel.type === 'CONTRASTS' ? 'dotted' : 'solid',
      width: relationWidth(rel),
      curveness: 0.08
    }
  }))

  chart.clear()
  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'edge') return params.data.tooltip?.formatter || ''
        const raw = params.data?.raw as GraphNode | undefined
        if (!raw) return params.name
        const mastery = props.masteryMap?.[raw.uid]
        const isWeak = props.weakPoints?.includes(raw.uid)
        const masteryText = mastery ? `掌握程度：${mastery}` : '未学习'
        const weakText = isWeak ? ' ⚠️ 薄弱点' : ''
        const diff = raw.properties?.difficulty
        const diffText = diff ? `难度：${'★'.repeat(Math.round(diff))}` : ''
        return `<strong>${nodeName(raw)}</strong><br/>${masteryText}${weakText}<br/>${diffText}`
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        left: 24,
        right: 24,
        top: 24,
        bottom: 24,
        roam: true,
        draggable: true,
        animationDurationUpdate: 450,
        force: { repulsion: 400, edgeLength: 160, gravity: 0.1 },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 8,
        emphasis: { focus: 'adjacency', itemStyle: { shadowBlur: 12, shadowColor: 'rgba(64,158,255,0.4)' } },
        data: nodes,
        links
      }
    ]
  })
}

// ---- lifecycle ----

onMounted(() => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)

  chart.on('click', (params: any) => {
    if (params.data?.raw) emit('select', params.data.raw)
  })

  chart.on('contextmenu', (params: any) => {
    if (!params.data?.raw) return
    const raw = params.data.raw as GraphNode
    const screenX = params.event?.event?.clientX ?? 0
    const screenY = params.event?.event?.clientY ?? 0
    showContextMenu(raw, screenX, screenY)
  })

  chart.getZr().on('dblclick', (params: any) => {
    // 双击空白区域不触发
    if (params.target) return
  })

  chart.on('dblclick', (params: any) => {
    if (params.data?.raw) {
      emit('generateResources', params.data.raw)
    }
  })

  render()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  hideContextMenu()
  chart?.dispose()
})

watch(() => [props.subgraph, props.selectedUid, props.masteryMap, props.weakPoints], render, { deep: true })

// ---- context menu ----

let menuEl: HTMLDivElement | null = null

function showContextMenu(node: GraphNode, x: number, y: number) {
  hideContextMenu()
  menuEl = document.createElement('div')
  menuEl.className = 'graph-context-menu'
  menuEl.style.cssText = `position:fixed;left:${x}px;top:${y}px;z-index:9999;background:#fff;border:1px solid #e4e7ed;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.12);padding:6px 0;min-width:160px;`
  const actions = [
    { label: '📄 生成学习资源', action: () => emit('generateResources', node) },
    { label: '📝 查看配套练习', action: () => emit('viewExercises', node) },
    { label: '🔍 向学习助手提问', action: () => emit('askQuestion', node) },
    { label: '🛤️ 加入学习路径', action: () => emit('addToPath', node) },
  ]
  actions.forEach(({ label, action }) => {
    const item = document.createElement('div')
    item.textContent = label
    item.style.cssText = 'padding:8px 16px;cursor:pointer;font-size:13px;color:#303133;transition:background 0.15s;'
    item.onmouseenter = () => { item.style.background = '#f5f7fa' }
    item.onmouseleave = () => { item.style.background = '' }
    item.onclick = () => { action(); hideContextMenu() }
    menuEl!.appendChild(item)
  })
  document.body.appendChild(menuEl)
  // 点击其他地方关闭
  setTimeout(() => {
    document.addEventListener('click', hideContextMenu, { once: true })
  }, 0)
}

function hideContextMenu() {
  if (menuEl) {
    menuEl.remove()
    menuEl = null
  }
}
</script>

<style scoped>
.graph-canvas {
  width: 100%;
  height: 620px;
  cursor: default;
}
</style>
