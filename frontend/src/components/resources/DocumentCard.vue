<template>
  <el-card class="section-card">
    <template #header>
      <div class="panel-title">
        <span>{{ localizeText(document?.title) || '讲解文档' }}</span>
        <el-tag type="primary">图文讲解</el-tag>
      </div>
    </template>
    <div v-if="document" class="markdown-body" v-html="html" />
    <el-empty v-else description="暂无讲解文档" />
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

const FORMULA_LINE_RE =
  /(?:\\(?:frac|partial|sum|sqrt|cdot|times|alpha|beta|gamma|theta|lambda|sigma|nabla)|[∂∑√∞≈≤≥×÷]|[A-Za-z0-9_})\]]\s*=\s*[^，。；;]+(?:[+\-*/^]|\\cdot|×|∂|∑|√))/

function renderMath(source: string, displayMode: boolean): string {
  try {
    return katex.renderToString(source, {
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

const html = computed(() => md.render(preprocessMarkdownMath(props.document?.content || '')))
</script>
