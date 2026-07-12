<template>
  <el-card class="section-card mindmap-card">
    <template #header>
      <div class="panel-title">
        <span>{{ mindmap?.title || '思维导图' }}</span>
        <div class="mindmap-actions">
          <el-button text @click="collapseAll">收起</el-button>
          <el-button text @click="expandAll">展开</el-button>
          <el-button text @click="fitMindmap">适配</el-button>
          <el-button v-if="editable" text type="primary" @click="toggleEditing">
            {{ editing ? '预览' : '编辑' }}
          </el-button>
          <el-button v-if="editable && hasUnsavedChanges" text type="success" @click="emitSave">保存修改</el-button>
          <el-button text type="primary" @click="openFull">全屏</el-button>
        </div>
      </div>
    </template>

    <el-empty v-if="!mindmap" description="暂无思维导图" />
    <template v-else>
      <div v-if="editing" class="mindmap-editor">
        <el-input
          v-model="draftContent"
          type="textarea"
          :rows="15"
          resize="vertical"
          placeholder="使用 Mermaid mindmap 语法编辑，例如：
mindmap
  root((反向传播))
    前置知识
      梯度下降
    核心机制
      链式法则"
        />
        <div class="editor-actions">
          <span class="muted">点击“预览”可先查看效果，点击“保存修改”会写回知识中心数据库。</span>
          <el-button @click="resetDraft">还原</el-button>
          <el-button type="primary" @click="emitSave">保存修改</el-button>
        </div>
      </div>

      <div v-else class="mindmap-shell">
        <svg ref="svgRef" class="markmap-svg" />
        <Teleport to="body">
          <div
            v-if="inlineEdit.visible"
            :style="inlineEditStyle"
            class="mindmap-inline-editor"
            @dblclick.stop
            @mousedown.stop
            @click.stop
          >
            <input
              ref="inlineInputRef"
              v-model="inlineEdit.text"
              class="inline-edit-input"
              @keydown.enter.prevent="commitInlineEdit"
              @keydown.escape.prevent="cancelInlineEdit"
              @blur="commitInlineEdit"
            />
          </div>
        </Teleport>
        <div class="chart-hint">双击节点可直接改文字，滚轮缩放，拖拽移动，点击节点展开或折叠</div>
      </div>
    </template>

    <el-dialog v-model="open" width="92%" title="思维导图" @opened="renderDialogMindmap">
      <div class="mindmap-shell dialog-shell">
        <svg ref="dialogSvgRef" class="markmap-svg dialog-svg" />
        <div class="chart-hint">双击节点可直接改文字，滚轮缩放，拖拽移动，点击节点展开或折叠</div>
      </div>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { GeneratedMindmap } from '@/types/resources'

const props = defineProps<{
  mindmap: GeneratedMindmap | null
  editable?: boolean
}>()

const emit = defineEmits<{
  save: [payload: { title: string; content: string }]
}>()

const transformer = new Transformer()
const svgRef = ref<SVGElement | null>(null)
const dialogSvgRef = ref<SVGElement | null>(null)
const open = ref(false)
const editing = ref(false)
const draftContent = ref('')
const expandLevel = ref(6)
const inlineInputRef = ref<HTMLInputElement | null>(null)
const inlineEdit = ref({
  visible: false,
  text: '',
  sourceIndex: -1,
  x: 0,
  y: 0
})
const hasUnsavedChanges = computed(() => {
  return normalizeMindmapContent(draftContent.value) !== normalizeMindmapContent(props.mindmap?.content || '')
})
const inlineEditStyle = computed(() => ({
  position: 'fixed' as const,
  left: `${inlineEdit.value.x}px`,
  top: `${inlineEdit.value.y}px`,
  zIndex: 3000
}))

let markmap: Markmap | null = null
let dialogMarkmap: Markmap | null = null
let resizeObserver: ResizeObserver | null = null
const inlineListenerCleanup: Array<() => void> = []

function cleanMindmapText(content: string): string {
  return content
    .replace(/^```(?:mermaid)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .replace(/\r\n/g, '\n')
    .trim()
}

function tokenizeOneLineMindmap(content: string): string[] {
  const source = content.replace(/\s+/g, ' ').trim()
  const tokens: string[] = []
  let current = ''
  let squareDepth = 0
  let roundDepth = 0

  for (const char of source) {
    if (char === '[') squareDepth += 1
    if (char === ']') squareDepth = Math.max(0, squareDepth - 1)
    if (char === '(') roundDepth += 1
    if (char === ')') roundDepth = Math.max(0, roundDepth - 1)
    if (char === ' ' && squareDepth === 0 && roundDepth === 0) {
      if (current) tokens.push(current)
      current = ''
    } else {
      current += char
    }
  }
  if (current) tokens.push(current)
  return tokens
}

function normalizeMindmapContent(content: string): string {
  const cleaned = cleanMindmapText(content)
  if (!cleaned) return ''
  if (cleaned.includes('\n')) return cleaned
  if (!cleaned.startsWith('mindmap ')) return cleaned

  const tokens = tokenizeOneLineMindmap(cleaned)
  const lines: string[] = []
  tokens.forEach((token, index) => {
    if (index === 0 && token === 'mindmap') {
      lines.push('mindmap')
    } else if (token.startsWith('root')) {
      lines.push(`  ${token}`)
    } else {
      lines.push(`    ${token}`)
    }
  })
  return lines.join('\n')
}

function readableLabel(line: string): string {
  return line
    .trim()
    .replace(/^root\(\((.*)\)\)$/i, '$1')
    .replace(/^root\((.*)\)$/i, '$1')
    .replace(/^([^\[]+)\[(.*)\]$/i, '$1：$2')
    .replace(/^(.+)\(\((.*)\)\)$/i, '$1：$2')
    .replace(/^(.+)\((.*)\)$/i, '$1：$2')
    .replace(/^\(\((.*)\)\)$/i, '$1')
    .replace(/^\((.*)\)$/i, '$1')
    .replace(/^\[(.*)\]$/i, '$1')
    .replace(/\(\((.*)\)\)/g, '$1')
    .replace(/\((.*)\)/g, '$1')
    .replace(/\[(.*)\]/g, '$1')
    .trim()
}

function escapeMindmapText(text: string): string {
  return text.replace(/\n+/g, ' ').trim()
}

function sourceLines(content: string): string[] {
  return normalizeMindmapContent(content).split('\n')
}

function sourceLineIndexes(content: string): number[] {
  return sourceLines(content).reduce<number[]>((indexes, line, index) => {
    if (line.trim() && line.trim() !== 'mindmap') indexes.push(index)
    return indexes
  }, [])
}

function replaceLineLabel(line: string, nextText: string): string {
  const indent = line.match(/^\s*/)?.[0] || ''
  const trimmed = line.trim()
  const text = escapeMindmapText(nextText)

  if (!text) return line
  if (/^root\(\(.*\)\)$/i.test(trimmed)) return `${indent}root((${text}))`
  if (/^root\(.*\)$/i.test(trimmed)) return `${indent}root(${text})`

  const square = trimmed.match(/^([^\[]+)\[(.*)\]$/)
  if (square) return `${indent}${square[1]}[${text}]`

  const doubleRound = trimmed.match(/^(.+)\(\((.*)\)\)$/)
  if (doubleRound) return `${indent}${doubleRound[1]}((${text}))`

  const round = trimmed.match(/^(.+)\((.*)\)$/)
  if (round) return `${indent}${round[1]}(${text})`

  return `${indent}${text}`
}

function mindmapToMarkdown(content: string): string {
  const normalized = normalizeMindmapContent(content)
  const lines = normalized
    .split('\n')
    .filter((line) => line.trim() && line.trim() !== 'mindmap')

  if (!lines.length) {
    const fallback = cleanMindmapText(content)
      .split(/[;；。]|\n+/)
      .map((item) => item.trim())
      .filter(Boolean)
    if (!fallback.length) return '# 思维导图'
    return fallback.map((item, index) => `${'#'.repeat(index === 0 ? 1 : 2)} ${readableLabel(item)}`).join('\n')
  }

  return lines
    .map((line, index) => {
      const indent = line.match(/^\s*/)?.[0].length || 0
      const level = index === 0 ? 1 : Math.min(Math.floor(indent / 2) + 1, 6)
      return `${'#'.repeat(level)} ${readableLabel(line)}`
    })
    .join('\n')
}

function buildMarkmapOptions() {
  return {
    autoFit: true,
    duration: 350,
    initialExpandLevel: expandLevel.value,
    maxWidth: 320,
    nodeMinHeight: 18,
    paddingX: 10,
    spacingHorizontal: 80,
    spacingVertical: 8,
    pan: true,
    zoom: true,
    color: (node: unknown) => {
      const colors = ['#2563eb', '#059669', '#d97706', '#7c3aed', '#475569']
      const depth = Number((node as { depth?: number }).depth || 1)
      return colors[Math.min(Math.max(depth - 1, 0), colors.length - 1)]
    }
  }
}

function clearSvg(svg: SVGElement | null) {
  if (!svg) return
  while (svg.firstChild) svg.removeChild(svg.firstChild)
}

async function renderToSvg(svg: SVGElement | null, current: Markmap | null) {
  if (!svg) return null
  const markdown = mindmapToMarkdown(draftContent.value || props.mindmap?.content || '')
  const { root } = transformer.transform(markdown)

  current?.destroy()
  clearSvg(svg)
  const instance = Markmap.create(svg, buildMarkmapOptions(), root)
  await nextTick()
  await instance.fit()
  bindInlineEditing(svg)
  return instance
}

async function renderMainMindmap() {
  if (editing.value) return
  markmap = await renderToSvg(svgRef.value, markmap)
}

async function renderDialogMindmap() {
  dialogMarkmap = await renderToSvg(dialogSvgRef.value, dialogMarkmap)
}

async function renderVisibleMindmaps() {
  await nextTick()
  await renderMainMindmap()
  if (open.value) await renderDialogMindmap()
}

async function toggleEditing() {
  editing.value = !editing.value
  if (!editing.value) await renderVisibleMindmaps()
}

async function collapseAll() {
  expandLevel.value = 1
  await renderVisibleMindmaps()
}

async function expandAll() {
  expandLevel.value = 99
  await renderVisibleMindmaps()
}

async function fitMindmap() {
  await markmap?.fit()
  await dialogMarkmap?.fit()
}

function openFull() {
  open.value = true
}

function resetDraft() {
  draftContent.value = normalizeMindmapContent(props.mindmap?.content || '')
  expandLevel.value = 6
  cancelInlineEdit()
}

async function emitSave() {
  const payload = {
    title: props.mindmap?.title || '思维导图',
    content: normalizeMindmapContent(draftContent.value)
  }
  editing.value = false
  await renderVisibleMindmaps()
  emit('save', payload)
}

function getNodeSourceIndex(group: Element): number {
  const node = (group as unknown as { __data__?: { payload?: { lines?: string } } }).__data__
  const startLine = Number(String(node?.payload?.lines || '').split(',')[0])
  if (Number.isFinite(startLine)) return startLine
  const label = group.textContent?.trim()
  if (!label) return -1
  const indexes = sourceLineIndexes(draftContent.value)
  return indexes.findIndex((lineIndex) => readableLabel(sourceLines(draftContent.value)[lineIndex]) === label)
}

function bindInlineEditing(svg: SVGElement) {
  if (!props.editable) return
  inlineListenerCleanup.splice(0).forEach((cleanup) => cleanup())

  const handler = (event: MouseEvent) => {
    const target = event.target as Element | null
    const group = target?.closest('g.markmap-node')
    if (!group) return
    const sourceIndex = getNodeSourceIndex(group)
    if (sourceIndex < 0) return

    event.preventDefault()
    event.stopPropagation()

    const foreignObject = group.querySelector('foreignObject')
    const rect = (foreignObject || group).getBoundingClientRect()
    inlineEdit.value = {
      visible: true,
      text: group.textContent?.trim() || readableLabel(sourceLines(draftContent.value)[sourceIndex]),
      sourceIndex,
      x: Math.max(12, rect.left),
      y: Math.max(12, rect.top - 6)
    }
    nextTick(() => inlineInputRef.value?.focus())
  }

  svg.addEventListener('dblclick', handler, true)
  inlineListenerCleanup.push(() => svg.removeEventListener('dblclick', handler, true))
}

async function commitInlineEdit() {
  if (!inlineEdit.value.visible) return
  const nextText = escapeMindmapText(inlineEdit.value.text)
  const targetIndex = inlineEdit.value.sourceIndex
  inlineEdit.value.visible = false
  if (!nextText || targetIndex < 0) return

  const lines = sourceLines(draftContent.value)
  if (!lines[targetIndex]) return
  lines[targetIndex] = replaceLineLabel(lines[targetIndex], nextText)
  draftContent.value = lines.join('\n')
  await renderVisibleMindmaps()
}

function cancelInlineEdit() {
  inlineEdit.value.visible = false
}

watch(
  () => props.mindmap?.content,
  async () => {
    resetDraft()
    await renderVisibleMindmaps()
  },
  { immediate: true }
)

watch(
  () => draftContent.value,
  () => {
    if (!editing.value) renderVisibleMindmaps()
  }
)

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    markmap?.fit()
    dialogMarkmap?.fit()
  })
  if (svgRef.value) resizeObserver.observe(svgRef.value)
  renderVisibleMindmaps()
})

watch(svgRef, (element) => {
  if (element && resizeObserver) resizeObserver.observe(element)
})

watch(dialogSvgRef, (element) => {
  if (element && resizeObserver) resizeObserver.observe(element)
})

onBeforeUnmount(() => {
  inlineListenerCleanup.splice(0).forEach((cleanup) => cleanup())
  resizeObserver?.disconnect()
  markmap?.destroy()
  dialogMarkmap?.destroy()
})
</script>

<style scoped>
.mindmap-card :deep(.el-card__body) {
  padding: 12px;
}

.mindmap-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.mindmap-shell {
  position: relative;
  min-height: 560px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  background:
    radial-gradient(circle at 18% 16%, rgba(64, 158, 255, 0.1), transparent 26%),
    radial-gradient(circle at 82% 76%, rgba(19, 164, 138, 0.08), transparent 26%),
    linear-gradient(180deg, #fbfdff 0%, #f6f9fc 100%);
}

.markmap-svg {
  display: block;
  width: 100%;
  height: 560px;
}

.dialog-shell {
  min-height: 74vh;
}

.dialog-svg {
  height: 74vh;
}

.mindmap-shell :deep(.markmap-node text),
.mindmap-shell :deep(.markmap-node foreignObject) {
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
}

.chart-hint {
  position: absolute;
  right: 12px;
  bottom: 10px;
  color: #7a8494;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid #e4e7ed;
  border-radius: 999px;
  padding: 4px 10px;
  backdrop-filter: blur(6px);
}

.mindmap-inline-editor {
  min-width: 140px;
  max-width: 360px;
  padding: 4px;
  border: 1px solid #409eff;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(31, 45, 61, 0.18);
}

.inline-edit-input {
  width: min(320px, 46vw);
  border: 0;
  outline: none;
  color: #1f2d3d;
  font-size: 14px;
  line-height: 24px;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
}

.mindmap-editor {
  display: grid;
  gap: 10px;
}

.mindmap-editor :deep(.el-textarea__inner) {
  font-family: Consolas, 'Microsoft YaHei', monospace;
  line-height: 1.65;
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
}

.editor-actions .muted {
  margin-right: auto;
}
</style>
