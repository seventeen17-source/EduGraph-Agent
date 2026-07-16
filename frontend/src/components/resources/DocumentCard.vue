<template>
  <el-card class="section-card">
    <template #header>
      <div class="panel-title">
        <span>{{ localizeText(document?.title) || '讲解文档' }}</span>
        <el-tag :type="document && !hasContent ? 'warning' : 'primary'">图文讲解</el-tag>
      </div>
    </template>
    <el-empty v-if="!document" description="暂无讲解文档" />
    <el-alert
      v-else-if="!hasContent"
      type="warning"
      title="讲解文档生成结果为空"
      description="本次生成没有得到可展示的正文，请重新生成，或查看质量报告中的失败原因。"
      show-icon
      :closable="false"
    />
    <div v-else class="markdown-body" v-html="html" />
  </el-card>
</template>

<script setup lang="ts">
import hljs from 'highlight.js'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import MarkdownIt from 'markdown-it'
import { computed } from 'vue'

import type { GeneratedDocument } from '@/types/resources'
import { localizeText } from '@/utils/format'

const props = defineProps<{
  document: GeneratedDocument | null
}>()

const hasContent = computed(() => Boolean(props.document?.content?.trim()))

const FORMULA_LINE_RE =
  /(?:\\(?:frac|partial|sum|sqrt|cdot|times|alpha|beta|gamma|theta|lambda|sigma|nabla)|[∂∑√∞≈≤≥×÷]|[A-Za-z0-9_})\]]\s*=\s*[^，。；;]+(?:[+\-*/^]|\\cdot|×|∂|∑|√))/

function renderMath(source: string, displayMode: boolean): string {
  try {
    return katex.renderToString(normalizeMathExpression(source), {
      displayMode,
      throwOnError: false,
      strict: false,
      trust: false,
      output: 'html'
    })
  } catch {
    return `<code class="math-fallback">${md.utils.escapeHtml(source)}</code>`
  }
}

function isEscaped(src: string, pos: number): boolean {
  let slashCount = 0
  for (let i = pos - 1; i >= 0 && src[i] === '\\'; i -= 1) {
    slashCount += 1
  }
  return slashCount % 2 === 1
}

function mathInlineRule(state: any, silent: boolean): boolean {
  const start = state.pos
  const src = state.src
  if (src[start] !== '$' || src[start + 1] === '$' || isEscaped(src, start)) return false

  let end = start + 1
  while ((end = src.indexOf('$', end)) !== -1) {
    if (!isEscaped(src, end)) break
    end += 1
  }
  if (end === -1 || end === start + 1) return false

  const content = src.slice(start + 1, end).trim()
  if (!content) return false

  if (!silent) {
    const token = state.push('math_inline', 'math', 0)
    token.content = content
  }
  state.pos = end + 1
  return true
}

function mathBlockRule(state: any, startLine: number, endLine: number, silent: boolean): boolean {
  const start = state.bMarks[startLine] + state.tShift[startLine]
  const max = state.eMarks[startLine]
  const marker = state.src.slice(start, max).trim()
  if (!marker.startsWith('$$')) return false

  const firstLine = marker.slice(2).trim()
  let nextLine = startLine
  const lines: string[] = []

  if (firstLine.endsWith('$$') && firstLine.length > 2) {
    lines.push(firstLine.slice(0, -2).trim())
  } else {
    if (firstLine) lines.push(firstLine)
    for (nextLine = startLine + 1; nextLine < endLine; nextLine += 1) {
      const lineStart = state.bMarks[nextLine] + state.tShift[nextLine]
      const lineEnd = state.eMarks[nextLine]
      const line = state.src.slice(lineStart, lineEnd)
      const closeIndex = line.indexOf('$$')
      if (closeIndex >= 0) {
        lines.push(line.slice(0, closeIndex).trim())
        break
      }
      lines.push(line)
    }
    if (nextLine >= endLine) return false
  }

  if (silent) return true
  const token = state.push('math_block', 'math', 0)
  token.block = true
  token.content = lines.join('\n').trim()
  token.map = [startLine, nextLine + 1]
  state.line = nextLine + 1
  return true
}

function normalizeMathExpression(source: string): string {
  return source
    .replace(/\bhaty(?=_|\b)/g, '\\hat{y}')
    .replace(/\bhat([A-Za-z])(?=_|\b)/g, '\\hat{$1}')
    .replace(/\bdots\b/g, '\\cdots')
    .replace(/\bmathbf([A-Za-z]+)\b/g, '\\mathbf{$1}')
    .replace(/\bfrac1N\b/g, '\\frac{1}{N}')
    .replace(/\bfracpartial([A-Za-z]+)partial([A-Za-z_][A-Za-z0-9_]*)\b/g, '\\frac{\\partial $1}{\\partial $2}')
    .replace(/\bsum([A-Za-z])=([0-9]+)([A-Za-z])\b/g, '\\sum_{$1=$2}^{$3}')
    .replace(/\bsum([A-Za-z])=([0-9]+)/g, '\\sum_{$1=$2}')
    .replace(/ŷ/g, '\\hat{y}')
    .replace(/([A-Za-z])ᵀ/g, '$1^T')
    .replace(/∂\s*([A-Za-z][A-Za-z0-9_]*)\s*\/\s*∂\s*([A-Za-z][A-Za-z0-9_]*)/g, '\\frac{\\partial $1}{\\partial $2}')
    .replace(/([A-Za-z])_([A-Za-z0-9]+)/g, '$1_{$2}')
    .replace(/\*/g, '\\cdot ')
    .replace(/×/g, '\\times ')
    .replace(/√\s*\(([^)]+)\)/g, '\\sqrt{$1}')
    .replace(/∑/g, '\\sum')
}

function shouldTreatAsFormulaLine(line: string): boolean {
  const trimmed = line.trim()
  if (!trimmed || trimmed.startsWith('|') || trimmed.startsWith('```')) return false
  if (/[\u4e00-\u9fff]/.test(trimmed)) return false
  if (trimmed.includes('$')) return false
  if (/^#{1,6}\s/.test(trimmed) || /^[-*+]\s/.test(trimmed) || /^\d+\.\s/.test(trimmed)) return false
  return FORMULA_LINE_RE.test(trimmed)
}

function preprocessMarkdownMath(content: string): string {
  const lines = content.split(/\r?\n/)
  let inFence = false
  let inMathBlock = false

  return lines
    .map((line) => {
      const trimmed = line.trim()
      if (trimmed.startsWith('```')) {
        inFence = !inFence
        return line
      }
      if (inFence) return line
      if (trimmed.startsWith('$$')) {
        if (trimmed === '$$') {
          inMathBlock = !inMathBlock
        } else {
          inMathBlock = !trimmed.endsWith('$$')
        }
        return line
      }
      if (inMathBlock || !shouldTreatAsFormulaLine(line)) return line
      return `\n$$\n${normalizeMathExpression(trimmed)}\n$$`
    })
    .join('\n')
}

function normalizeDocumentMarkdown(content: string): string {
  let text = localizeText(content || '')
  const trimmed = text.trim()
  if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
    try {
      const parsed = JSON.parse(trimmed)
      if (typeof parsed === 'string') text = parsed
    } catch {
      // Keep the original text when it is not a JSON-encoded string.
    }
  }
  text = text
    .replace(/\\r\\n/g, '\n')
    .replace(/\\n(?!abla\b|eq\b|ot\b|u\b)/g, '\n')
    .replace(/\\t/g, '  ')
    .replace(/\\"/g, '"')
  text = stripLeakedJsonFields(text)
  text = repairBrokenFormulaLines(text)
  return fenceLoosePythonBlocks(text)
}

function stripLeakedJsonFields(content: string): string {
  const leakedFieldRe = /",\s*"(?:(?:代码|code|explanation|learning_objectives|prerequisites|additional_references|证据来源|source_uids|key_points)|[a-z_]{3,})"\s*:/i
  const match = leakedFieldRe.exec(content)
  if (!match || match.index < 80) return content
  return content.slice(0, match.index).trim()
}

function repairBrokenFormulaLines(content: string): string {
  const lines = content.split(/\r?\n/)
  const result: string[] = []
  let formulaBuffer: string[] = []

  const isFormulaLike = (line: string) => {
    const trimmed = line.trim()
    if (!trimmed) return false
    if (/[\u4e00-\u9fff]/.test(trimmed) && !/[=+\-^_]|frac|sum|hat|mathbf|mathbf|dots/.test(trimmed)) return false
    return /^(?:\.{2,}|[A-Za-z0-9_{}()[\]^+\-*/=,\s]+|(?:hat|frac|sum|mathbf|mathb|dots|cdot|partial)\w*)$/.test(trimmed)
      || /\b(?:haty|hat[A-Za-z]|frac1N|fracpartial|sum[A-Za-z]=|mathbf|mathb|dots)\b/.test(trimmed)
  }
  const shouldContinueFormula = (line: string) => {
    return /[=+\-*/,(]\s*$/.test(line.trim())
  }
  const flushFormula = () => {
    if (!formulaBuffer.length) return
    result.push(formulaBuffer.join(' ').replace(/\s+/g, ' ').trim())
    formulaBuffer = []
  }

  for (const line of lines) {
    const trimmed = line.trim()
    const previous = formulaBuffer[formulaBuffer.length - 1] || ''
    const mergeWithBuffer = formulaBuffer.length > 0 && (
      isFormulaLike(line)
      || shouldContinueFormula(previous)
      || /^(?:\.{2,}|frac|sum|hat|mathbf|mathb|dots)/.test(trimmed)
    )
    if (mergeWithBuffer) {
      formulaBuffer.push(trimmed)
      if (!shouldContinueFormula(trimmed) && !/^(?:frac|sum|hat|mathbf|mathb|dots|\.\.\.)/.test(trimmed)) {
        flushFormula()
      }
      continue
    }
    if (isFormulaLike(line) && shouldContinueFormula(line)) {
      formulaBuffer.push(trimmed)
      continue
    }
    flushFormula()
    result.push(line)
  }
  flushFormula()
  return result.join('\n')
}

function fenceLoosePythonBlocks(content: string): string {
  const lines = content.split(/\r?\n/)
  const result: string[] = []
  let inLoosePython = false

  const isLoosePythonStart = (index: number) => {
    return lines[index]?.trim().toLowerCase() === 'python'
      && /^(import|from|#|[A-Za-z_][A-Za-z0-9_]*\s*=)/.test(lines[index + 1]?.trim() || '')
  }
  const isPythonLikeLine = (line: string) => {
    const trimmed = line.trim()
    if (!trimmed) return true
    if (/^#{2,6}\s/.test(trimmed)) return false
    return /^(import|from|#(?!#)|print\(|for\s|if\s|elif\s|else:|def\s|class\s|return\b)/.test(trimmed)
      || /^[A-Za-z_][A-Za-z0-9_]*(?:\s*=|\.)/.test(trimmed)
      || /^[)\]},\]]/.test(trimmed)
  }

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]
    const trimmed = line.trim()
    if (!inLoosePython && isLoosePythonStart(i)) {
      result.push('```python')
      inLoosePython = true
      continue
    }
    if (inLoosePython && trimmed && !isPythonLikeLine(line)) {
      result.push('```')
      inLoosePython = false
    }
    result.push(line)
  }
  if (inLoosePython) result.push('```')
  return result.join('\n')
}

const md = new MarkdownIt({
  html: false,
  linkify: true,
  highlight(code: string, lang: string) {
    if (lang && hljs.getLanguage(lang)) {
      return `<pre><code class="hljs">${hljs.highlight(code, { language: lang }).value}</code></pre>`
    }
    return `<pre><code class="hljs">${md.utils.escapeHtml(code)}</code></pre>`
  }
})

md.inline.ruler.before('escape', 'math_inline', mathInlineRule)
md.block.ruler.before('fence', 'math_block', mathBlockRule, {
  alt: ['paragraph', 'reference', 'blockquote', 'list']
})
md.renderer.rules.math_inline = (tokens: any[], idx: number) => renderMath(tokens[idx].content, false)
md.renderer.rules.math_block = (tokens: any[], idx: number) => {
  return `<div class="math-block">${renderMath(tokens[idx].content, true)}</div>\n`
}

const html = computed(() => md.render(preprocessMarkdownMath(normalizeDocumentMarkdown(props.document?.content || ''))))
</script>

<style scoped>
.markdown-body :deep(img) {
  display: block;
  max-width: 100%;
  max-height: 520px;
  height: auto;
  object-fit: contain;
  margin: 18px auto 8px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #fff;
}

.markdown-body :deep(em) {
  color: #64748b;
}
</style>
