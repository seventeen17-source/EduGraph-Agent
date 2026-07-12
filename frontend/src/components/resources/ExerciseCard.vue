<template>
  <el-card class="section-card exercise-card-container">
    <template #header>
      <div class="panel-title">
        <span>练习题</span>
        <el-tag type="warning">{{ exercises.length }}</el-tag>
        <span v-if="submitted" class="score-badge" :class="scoreClass">
          {{ correctCount }}/{{ exercises.length }} 正确 ({{ Math.round(correctCount / exercises.length * 100) }}%)
        </span>
      </div>
    </template>

    <el-empty v-if="!exercises.length" description="暂无练习题" />

    <div v-else class="exercise-list">
      <!-- 会话进度 -->
      <div v-if="!submitted" class="session-progress">
        <el-steps :active="currentStep" align-center simple>
          <el-step v-for="(_, i) in exercises" :key="i" :title="`${i + 1}`" />
        </el-steps>
      </div>

      <div
        v-for="(item, index) in exercises"
        :key="`${item.title}-${index}`"
        class="exercise-item"
        :class="{
          'item-active': !submitted && currentStep === index,
          'item-correct': submitted && checkAttempt(item, index) === 'correct',
          'item-wrong': submitted && checkAttempt(item, index) === 'wrong',
          'item-pending': submitted && checkAttempt(item, index) === 'pending'
        }"
      >
        <!-- 题号 + 类型 + 难度 -->
        <div class="exercise-header">
          <div class="header-left">
            <span class="question-number">{{ index + 1 }}</span>
            <strong>{{ localizeText(item.title) }}</strong>
            <el-tag size="small" :type="typeTag(item.type)">{{ typeLabel(item.type) }}</el-tag>
          </div>
          <div class="header-right">
            <el-rate :model-value="item.difficulty" disabled size="small" show-score />
          </div>
        </div>

        <!-- 题干 -->
        <div class="question-body markdown-body" v-html="renderMd(localizeText(item.question))" />

        <!-- 选项（选择题） -->
        <el-radio-group
          v-if="item.options?.length"
          v-model="answers[index]"
          :disabled="submitted"
          class="option-group"
        >
          <el-radio
            v-for="option in item.options"
            :key="option.label"
            :label="option.label"
            class="option-item"
          >
            <span class="option-label">{{ option.label }}</span>
            <span>{{ localizeText(option.text) }}</span>
          </el-radio>
        </el-radio-group>

        <!-- 文本输入（简答题） -->
        <el-input
          v-else-if="item.type !== 'coding'"
          v-model="answers[index]"
          type="textarea"
          :rows="3"
          :disabled="submitted"
          placeholder="输入你的答案（支持多行）"
        />

        <!-- 代码输入 -->
        <div v-else class="coding-area">
          <div v-if="!submitted" class="coding-input">
            <el-input
              v-model="answers[index]"
              type="textarea"
              :rows="5"
              placeholder="输入你的代码..."
              class="code-editor"
            />
          </div>
          <pre v-else class="code-display">{{ answers[index] || '(未作答)' }}</pre>
        </div>

        <!-- 操作按钮 -->
        <div class="exercise-actions">
          <el-button
            v-if="item.adaptive_feedback?.default && !submitted"
            size="small"
            text
            type="primary"
            @click="toggleHint(index)"
          >
            <el-icon><QuestionFilled /></el-icon>
            {{ showHint[index] ? '隐藏提示' : '查看提示' }}
          </el-button>
          <el-button
            v-if="!submitted"
            size="small"
            text
            type="info"
            @click="toggleAnswer(index)"
          >
            <el-icon><View /></el-icon>
            {{ showAnswer[index] ? '隐藏解析' : '查看解析' }}
          </el-button>
        </div>

        <!-- 提示 -->
        <el-alert
          v-if="showHint[index] && item.adaptive_feedback?.default && !submitted"
          type="info"
          :closable="false"
          :title="localizeText(item.adaptive_feedback.default)"
          show-icon
        />

        <!-- 提交后反馈 -->
        <div v-if="submitted" class="feedback-block">
          <!-- 选择题：逐选项解释 -->
          <template v-if="item.options?.length">
            <div
              v-for="option in item.options"
              :key="option.label"
              class="option-feedback"
              :class="{
                'opt-correct': option.label === (item.answer?.correct || item.answer?.reference_answer),
                'opt-user-wrong': option.label === answers[index] && option.label !== (item.answer?.correct || item.answer?.reference_answer),
                'opt-neutral': option.label !== answers[index] && option.label !== (item.answer?.correct || item.answer?.reference_answer),
              }"
            >
              <span class="opt-badge">
                <template v-if="option.label === (item.answer?.correct || item.answer?.reference_answer)">✓</template>
                <template v-else-if="option.label === answers[index]">✗</template>
                <template v-else>·</template>
              </span>
              <span class="opt-text">{{ option.label }}. {{ localizeText(option.text) }}</span>
              <span
                v-if="option.label !== (item.answer?.correct || item.answer?.reference_answer)
                  && (optionFeedback(item, option.label))"
                class="opt-why"
              >
                — {{ optionFeedback(item, option.label) }}
              </span>
            </div>
          </template>

          <!-- 非选择题：简洁反馈 -->
          <el-alert
            v-else
            :type="checkAttempt(item, index) === 'correct' ? 'success' : (checkAttempt(item, index) === 'wrong' ? 'error' : 'warning')"
            :closable="false"
            show-icon
          >
            <template #title>
              <span v-if="checkAttempt(item, index) === 'correct'">✓ 正确！</span>
              <span v-else-if="checkAttempt(item, index) === 'wrong'">✗ 需要复习</span>
              <span v-else>⚠ 未作答</span>
            </template>
          </el-alert>

          <!-- 解析 + 知识点 + 求助 -->
          <div v-if="checkAttempt(item, index) !== 'correct'" class="feedback-extra">
            <div v-if="item.answer?.explanation" class="feedback-explanation">
              <strong>💡 解析：</strong>{{ localizeText(item.answer.explanation) }}
            </div>
            <div v-if="item.answer?.knowledge_points?.length" class="feedback-kps">
              <strong>📚 相关知识点：</strong>
              <el-tag
                v-for="kp in item.answer.knowledge_points"
                :key="kp"
                size="small"
                type="warning"
                effect="plain"
                style="cursor: pointer; margin-left: 4px;"
                @click="$emit('viewInGraph', kp)"
              >
                {{ uidLabelMap?.[kp] || kp }}
              </el-tag>
            </div>
            <el-button size="small" type="primary" text @click="$emit('askAssistant', item)">
              🤖 请学习助手讲解这道题
            </el-button>
          </div>
        </div>

        <!-- 答案解析 -->
        <el-alert
          v-if="showAnswer[index] && !submitted"
          type="success"
          :closable="false"
        >
          <template #title>参考答案</template>
          <pre class="answer-pre">{{ formatAnswer(item.answer) }}</pre>
        </el-alert>

        <!-- 前/后导航 -->
        <div v-if="!submitted" class="question-nav">
          <el-button size="small" :disabled="index === 0" @click="currentStep = index - 1">
            <el-icon><ArrowLeft /></el-icon> 上一题
          </el-button>
          <span class="nav-hint">{{ index + 1 }} / {{ exercises.length }}</span>
          <el-button size="small" :disabled="index === exercises.length - 1" @click="currentStep = index + 1">
            下一题 <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 提交区域 -->
      <div v-if="!submitted" class="round-actions">
        <div class="muted">已作答 {{ answeredCount }} / {{ exercises.length }} 题</div>
        <el-button
          type="primary"
          size="large"
          :disabled="answeredCount < exercises.length"
          @click="confirmSubmit"
        >
          <el-icon><Finished /></el-icon> 提交本轮并更新画像
        </el-button>
      </div>

      <!-- 提交后操作 -->
      <div v-else class="round-actions submitted-actions">
        <div class="score-summary">
          <span class="score-text" :class="scoreClass">{{ correctCount }}/{{ exercises.length }} 正确</span>
          <span class="muted">（{{ Math.round(correctCount / exercises.length * 100) }}%）</span>
          <el-tag v-if="weakNodes.length" type="warning" size="small">
            建议复习：{{ weakNodes.map(n => uidLabelMap[n] || n).join(', ') }}
          </el-tag>
        </div>
        <div class="post-actions">
          <el-button @click="retryRound">
            <el-icon><Refresh /></el-icon> 重新作答
          </el-button>
          <el-button type="primary" @click="viewInGraph">
            <el-icon><Share /></el-icon> 在知识图谱中查看
          </el-button>
          <el-button type="success" @click="askAssistant">
            <el-icon><ChatDotRound /></el-icon> 向学习助手求助
          </el-button>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  ArrowRight,
  ChatDotRound,
  Finished,
  QuestionFilled,
  Refresh,
  Share,
  View,
} from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'

import type { GeneratedExercise } from '@/types/resources'
import { localizeText } from '@/utils/format'

const props = defineProps<{
  exercises: GeneratedExercise[]
  submitted: boolean
  correctCount: number
  correctNodes: string[]
  weakNodes: string[]
  uidLabelMap: Record<string, string>
}>()

const emit = defineEmits<{
  submit: [answers: Array<{ exercise: GeneratedExercise; answer: string }>]
  retry: []
  viewInGraph: [nodeIds: string[]]
  askAssistant: [target: string | GeneratedExercise]
}>()

const answers = reactive<Record<number, string>>({})
const showAnswer = reactive<Record<number, boolean>>({})
const showHint = reactive<Record<number, boolean>>({})
const currentStep = ref(0)

const md = new MarkdownIt({ html: false, breaks: true })

const answeredCount = computed(() =>
  props.exercises.filter((_, i) => Boolean(String(answers[i] || '').trim())).length
)

const scoreClass = computed(() => {
  const pct = props.correctCount / Math.max(props.exercises.length, 1)
  return pct >= 0.8 ? 'score-high' : pct >= 0.5 ? 'score-mid' : 'score-low'
})

function checkAttempt(exercise: GeneratedExercise, index: number): 'correct' | 'wrong' | 'pending' {
  const answer = String(answers[index] || '').trim()
  if (!answer) return 'pending'
  const correct = exercise.answer?.correct ?? exercise.answer?.reference_answer
  if (!correct) return 'pending'
  return answer === String(correct) ? 'correct' : 'wrong'
}

function toggleHint(index: number) {
  showHint[index] = !showHint[index]
}

function toggleAnswer(index: number) {
  showAnswer[index] = !showAnswer[index]
}

function confirmSubmit() {
  ElMessageBox.confirm(
    `你已作答 ${answeredCount.value}/${props.exercises.length} 题，确认提交本轮练习？提交后将回写学生画像。`,
    '确认提交',
    { confirmButtonText: '提交', cancelButtonText: '继续作答', type: 'info' }
  ).then(() => {
    emit('submit', props.exercises.map((exercise, i) => ({
      exercise,
      answer: String(answers[i] || '')
    })))
  }).catch(() => {})
}

function retryRound() {
  Object.keys(answers).forEach(k => delete answers[Number(k)])
  Object.keys(showAnswer).forEach(k => delete showAnswer[Number(k)])
  Object.keys(showHint).forEach(k => delete showHint[Number(k)])
  currentStep.value = 0
  emit('retry')
}

function viewInGraph() {
  const nodeIds = [...new Set(props.exercises.map(e => e.related_node_id).filter(Boolean))]
  emit('viewInGraph', nodeIds)
}

function askAssistant() {
  const nodeId = props.exercises[0]?.related_node_id || ''
  emit('askAssistant', nodeId)
}

function renderMd(text: string) {
  return md.render(text || '')
}

function optionFeedback(item: GeneratedExercise, optionLabel: string): string {
  const af = item.adaptive_feedback as Record<string, any> | undefined
  if (!af) return ''
  // 直接 key 匹配
  if (af[optionLabel]) return localizeText(af[optionLabel])
  // by_option 嵌套
  if (af.by_option?.[optionLabel]) return localizeText(af.by_option[optionLabel])
  // answer.error_types 嵌套
  const ans = item.answer as Record<string, any> | undefined
  if (ans?.error_types?.[optionLabel]) return localizeText(ans.error_types[optionLabel])
  return ''
}

function formatAnswer(answer: Record<string, any>) {
  if (answer.reference_answer) return answer.reference_answer
  if (answer.reference_code) return answer.reference_code
  return JSON.stringify(answer, null, 2)
}

function typeTag(type: string) {
  const tags: Record<string, string> = { choice: 'primary', short_answer: 'success', coding: 'danger', case_analysis: 'warning' }
  return tags[type] || 'info'
}

function typeLabel(type: string) {
  const labels: Record<string, string> = { choice: '选择题', short_answer: '简答题', coding: '编程题', case_analysis: '案例分析' }
  return labels[type] || type
}
</script>

<style scoped>
.exercise-card-container :deep(.el-card__body) {
  padding: 20px 24px;
}

.exercise-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-progress {
  margin-bottom: 24px;
  padding: 0 20px;
}

.exercise-item {
  padding: 20px;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.exercise-item.item-active {
  border-color: #818cf8;
  box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.15);
}

.exercise-item.item-correct {
  border-color: #10b981;
  background: #f0fdf4;
}

.exercise-item.item-wrong {
  border-color: #f59e0b;
  background: #fffbeb;
}

.exercise-item.item-pending {
  border-color: #e2e8f0;
  background: #f8fafc;
}

.exercise-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 10px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.question-number {
  width: 28px;
  height: 28px;
  background: #4f46e5;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.question-body {
  margin-bottom: 16px;
  font-size: 15px;
  line-height: 1.7;
  color: #1e293b;
}

.option-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.option-item {
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  transition: all 0.2s;
  height: auto;
  margin: 0;
}

.option-item:hover {
  border-color: #818cf8;
  background: #f5f3ff;
}

.option-label {
  font-weight: 700;
  margin-right: 8px;
  color: #4f46e5;
}

.coding-area .code-editor :deep(textarea) {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.code-display {
  background: #1e293b;
  color: #e2e8f0;
  padding: 14px;
  border-radius: 8px;
  font-family: monospace;
  font-size: 13px;
  white-space: pre-wrap;
  max-height: 300px;
  overflow: auto;
}

.exercise-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.question-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #f1f5f9;
}

.nav-hint {
  font-size: 13px;
  color: #94a3b8;
}

.round-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 0 4px;
  margin-top: 8px;
  border-top: 2px solid #e2e8f0;
  flex-wrap: wrap;
  gap: 12px;
}

.submitted-actions {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 20px;
  gap: 16px;
}

.score-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.score-text {
  font-size: 18px;
  font-weight: 700;
}

.score-high { color: #10b981; }
.score-mid { color: #f59e0b; }
.score-low { color: #ef4444; }

.score-badge {
  font-weight: 600;
  font-size: 14px;
  margin-left: auto;
}

.post-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.feedback-detail {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
}

.answer-pre {
  margin: 8px 0 0;
  white-space: pre-wrap;
  font-size: 13px;
  background: #f0fdf4;
  padding: 10px;
  border-radius: 6px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

/* Markdown render */
.markdown-body :deep(p) { margin: 4px 0; }
.markdown-body :deep(code) {
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 13px;
}
.markdown-body :deep(pre) {
  background: #1e293b; color: #e2e8f0;
  padding: 10px; border-radius: 6px; overflow-x: auto;
}

/* 逐选项反馈 */
.feedback-block { margin-top: 12px; }
.option-feedback { padding: 6px 10px; border-radius: 6px; margin-bottom: 4px; font-size: 13px; display: flex; align-items: flex-start; gap: 6px; }
.opt-correct { background: #f0fdf4; color: #166534; }
.opt-user-wrong { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.opt-neutral { background: #f8fafc; color: #94a3b8; }
.opt-badge { font-weight: 700; font-size: 14px; flex-shrink: 0; width: 18px; }
.opt-text { flex: 1; }
.opt-why { font-size: 12px; color: #dc2626; margin-left: 8px; font-style: italic; }
.feedback-extra { margin-top: 12px; padding: 10px 12px; background: #f8fafc; border-radius: 8px; display: flex; flex-direction: column; gap: 8px; }
.feedback-explanation { font-size: 13px; line-height: 1.7; color: #475569; }
.feedback-kps { font-size: 13px; color: #475569; }
</style>
