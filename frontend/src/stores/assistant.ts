import { defineStore } from 'pinia'

import { chatAssistant, getAssistantHistory, streamAssistant, submitFeedback } from '@/api/assistant'
import type {
  AssistantAction,
  AssistantChatResponse,
  AssistantMessage,
  AssistantPathPlan,
  AssistantTraceItem,
  ClarifyOption,
  ExerciseFeedback,
  LiveTraceItem,
  MemoryEntrySummary,
  SuggestedNextAction
} from '@/types/assistant'
import type { EvidencePackage } from '@/types/graphrag'
import type { GeneratedResources } from '@/types/resources'

/** LangGraph 全部 16 节点及其中文标签 */
const ALL_NODES: { node: string; label: string }[] = [
  { node: 'load_context', label: '加载画像上下文' },
  { node: 'retrieve_memory', label: '检索历史记忆' },
  { node: 'understand_intent', label: '识别学习意图' },
  { node: 'update_profile', label: '更新学生画像' },
  { node: 'record_progress', label: '记录学习进度' },
  { node: 'retrieve_evidence', label: '检索 GraphRAG 证据' },
  { node: 'evaluate_evidence', label: '评估证据质量' },
  { node: 'expand_evidence', label: '扩展证据检索' },
  { node: 'generate_resources', label: '生成学习资源' },
  { node: 'reflect_on_resources', label: '反思资源质量' },
  { node: 'explain_exercise', label: '生成练习讲解' },
  { node: 'plan_learning_path', label: '规划学习路径' },
  { node: 'review_assessment', label: '评估复盘' },
  { node: 'general_tutor', label: '智能答疑' },
  { node: 'compose_response', label: '整理学习回复' },
  { node: 'extract_memory', label: '提取记忆条目' },
  { node: 'error_recovery', label: '错误恢复' },
]

function makeNodeLabelMap(): Record<string, string> {
  const map: Record<string, string> = {}
  for (const n of ALL_NODES) map[n.node] = n.label
  return map
}

function makeInitialLiveTrace(): LiveTraceItem[] {
  return ALL_NODES.map((n) => ({
    node: n.node,
    label: n.label,
    status: 'pending' as const,
    summary: '',
  }))
}

export const useAssistantStore = defineStore('assistant', {
  state: () => ({
    conversationId: null as string | null,
    studentId: '' as string,
    messages: [] as AssistantMessage[],
    running: false,
    streaming: false,
    statusText: '',
    agentTrace: [] as AssistantTraceItem[],
    // === 流式实时状态 ===
    liveTrace: makeInitialLiveTrace() as LiveTraceItem[],
    currentStreamNode: null as string | null,
    partialReply: '',
    partialEvidenceScore: null as number | null,
    partialResourceScore: null as number | null,
    partialScoreReason: '',
    // === 最终结果 ===
    actions: [] as AssistantAction[],
    suggestedNextActions: [] as SuggestedNextAction[],
    evidence: null as EvidencePackage | null,
    resources: null as GeneratedResources | null,
    resourceRecordId: null as string | null,
    pathPlan: null as AssistantPathPlan | null,
    exerciseFeedback: null as ExerciseFeedback | null,
    profileDelta: {} as Record<string, any>,
    // 澄清
    needsClarification: false,
    clarificationOptions: [] as ClarifyOption[],
    clarificationQuestion: '',
    // 质量
    evidenceQualityScore: null as number | null,
    resourceQualityScore: null as number | null,
    // 反思
    reflection: '',
    needsRefinement: false,
    // 语义记忆
    relevantMemories: [] as MemoryEntrySummary[],
    errors: [] as string[],
    error: null as string | null,
    hasMoreMessages: false as boolean,
    // 流式取消
    streamAbortController: null as AbortController | null,
    messageFeedback: {} as Record<string, { tags: string[]; freeText: string; submitted: boolean; adaptationSummary: string; actionTaken: string; actionResult: string }>,
  }),
  getters: {
    /** 本次流式执行中实际经过的节点 */
    activeLiveNodes(): LiveTraceItem[] {
      return this.liveTrace.filter((t) => t.status !== 'pending')
    },
    /** 实际执行的节点顺序（用于可视化） */
    executedNodeOrder(): string[] {
      return this.liveTrace
        .filter((t) => t.status !== 'pending')
        .map((t) => t.node)
    },
  },
  actions: {
    async loadHistory(studentId: string) {
      this.studentId = studentId
      try {
        const history = await getAssistantHistory(studentId)
        const latestConv = history.conversations[0]
        if (!latestConv) {
          this.messages = []
          this.conversationId = null
          this.hasMoreMessages = false
          return
        }
        this.conversationId = latestConv.id
        const convMessages = history.messages
          .filter((m) => m.conversation_id === latestConv.id)
          .slice(-20)
        this.messages = convMessages
        this.hasMoreMessages = convMessages.length >= 20
      } catch {
        this.messages = []
        this.conversationId = null
        this.hasMoreMessages = false
      }
    },
    async loadMoreHistory(studentId: string) {
      this.studentId = studentId
      if (!this.conversationId || !this.hasMoreMessages) return
      try {
        const history = await getAssistantHistory(studentId)
        const convMessages = history.messages
          .filter((m) => m.conversation_id === this.conversationId)
          .slice(0, -this.messages.length)
        if (convMessages.length === 0) {
          this.hasMoreMessages = false
          return
        }
        const existingIds = new Set(this.messages.map((m) => m.id))
        const newMsgs = convMessages.filter((m) => !existingIds.has(m.id))
        if (newMsgs.length > 0) {
          this.messages = [...newMsgs.reverse(), ...this.messages]
        }
        this.hasMoreMessages = convMessages.length > this.messages.filter((m) => existingIds.has(m.id) || newMsgs.some((n) => n.id === m.id)).length
      } catch {
        // 忽略
      }
    },

    // ── 重置流式状态 ──
    resetStreamState() {
      this.liveTrace = makeInitialLiveTrace()
      this.currentStreamNode = null
      this.partialReply = ''
      this.partialEvidenceScore = null
      this.partialResourceScore = null
      this.partialScoreReason = ''
      this.agentTrace = []
    },

    // ── 非流式发送 ──
    async sendMessage(studentId: string, content: string) {
      this.studentId = studentId
      const userMessage = this.localMessage('user', content)
      this.messages.push(userMessage)
      this.running = true
      this.error = null
      this.errors = []
      this.resetStreamState()
      try {
        const response = await chatAssistant({
          student_id: studentId,
          message: content,
          conversation_id: this.conversationId
        })
        this.applyResponse(response)
        this.messages.push(this.localMessage('assistant', response.reply, response))
        return response
      } catch (error: any) {
        this.error = error.displayMessage || error.message || '学习助手请求失败'
        throw error
      } finally {
        this.running = false
      }
    },

    // ── 流式发送 ──
    async streamMessage(studentId: string, content: string) {
      this.studentId = studentId
      this.messages.push(this.localMessage('user', content))
      this.running = true
      this.streaming = true
      this.error = null
      this.errors = []
      this.resetStreamState()
      this.statusText = '🧠 学习助手正在启动 LangGraph 编排...'

      const nodeLabelMap = makeNodeLabelMap()
      const abortController = new AbortController()
      this.streamAbortController = abortController

      try {
        await streamAssistant(
          { student_id: studentId, message: content, conversation_id: this.conversationId },
          {
            onNodeStart: (node, label) => {
              this.currentStreamNode = node
              this.statusText = `⏳ ${label}...`
              // 更新 liveTrace：标记为 running
              const idx = this.liveTrace.findIndex((t) => t.node === node)
              if (idx >= 0) {
                this.liveTrace[idx] = { ...this.liveTrace[idx], status: 'running' }
              }
            },
            onNodeComplete: (node, label) => {
              // 更新 liveTrace：标记为 done
              const idx = this.liveTrace.findIndex((t) => t.node === node)
              if (idx >= 0) {
                this.liveTrace[idx] = { ...this.liveTrace[idx], status: 'done' }
              }
              this.statusText = `✅ ${label} 完成`
            },
            onTraceItem: (node, status, summary) => {
              // 更新对应节点的摘要
              const idx = this.liveTrace.findIndex((t) => t.node === node)
              if (idx >= 0) {
                const mappedStatus = status === 'failed' ? 'failed' as const : 'done' as const
                this.liveTrace[idx] = {
                  ...this.liveTrace[idx],
                  status: mappedStatus,
                  summary,
                }
              }
              // 累积到 agentTrace（兼容旧显示）
              this.agentTrace.push({
                node,
                status: (status === 'failed' ? 'failed' : 'done') as AssistantTraceItem['status'],
                summary,
                metadata: {},
                created_at: new Date().toISOString(),
              } as AssistantTraceItem)
            },
            onQualityUpdate: (type, score, reason) => {
              if (type === 'evidence') {
                this.partialEvidenceScore = score
              } else if (type === 'resource') {
                this.partialResourceScore = score
              }
              if (reason) this.partialScoreReason = reason
            },
            onFinal: (response) => {
              this.applyResponse(response)
              // 用最终 agent_trace 覆盖实时累积的
              this.agentTrace = response.agent_trace
              this.messages.push(this.localMessage('assistant', response.reply, response))
            },
            onError: (error) => {
              this.error = error.message
            },
          },
          abortController.signal,
        )
      } catch (err: any) {
        if (err.name === 'AbortError') {
          this.statusText = '⏹ 已取消'
        } else {
          this.error = err.displayMessage || err.message || '流式请求失败'
        }
      } finally {
        this.running = false
        this.streaming = false
        this.currentStreamNode = null
        this.streamAbortController = null
      }
    },

    cancelStream() {
      this.streamAbortController?.abort()
    },

    initFeedback(messageId: string) {
      if (!this.messageFeedback[messageId]) {
        this.messageFeedback[messageId] = { tags: [], freeText: '', submitted: false, adaptationSummary: '', actionTaken: '', actionResult: '' }
      }
    },

    toggleFeedbackTag(messageId: string, tag: string) {
      this.initFeedback(messageId)
      const fb = this.messageFeedback[messageId]
      if (fb.submitted) return
      const idx = fb.tags.indexOf(tag)
      if (idx >= 0) fb.tags.splice(idx, 1)
      else fb.tags.push(tag)
    },

    setFeedbackText(messageId: string, text: string) {
      this.initFeedback(messageId)
      if (!this.messageFeedback[messageId].submitted) {
        this.messageFeedback[messageId].freeText = text
      }
    },

    async submitMessageFeedback(messageId: string, intent: string, targetNodeId: string) {
      const fb = this.messageFeedback[messageId]
      if (!fb || fb.submitted || fb.tags.length === 0) return

      // 拒绝空 student_id
      if (!this.studentId) {
        this.error = '未设置学生 ID，无法提交反馈'
        return
      }

      const assMsg = this.messages.find(m => m.id === messageId)
      const convId = assMsg?.conversation_id || this.conversationId || ''
      let response: any = null
      try {
        response = await submitFeedback({
          message_id: messageId,
          student_id: this.studentId,
          tags: fb.tags,
          free_text: fb.freeText || null,
          conversation_id: convId,
          intent: assMsg?.intent || intent,
          target_node_id: assMsg?.target_node_id || targetNodeId,
        })
        fb.submitted = true
        fb.adaptationSummary = response?.adaptation_summary || ''
        fb.actionTaken = response?.action_taken || ''
        fb.actionResult = response?.action_result || ''

        // 如果画像更新失败，暴露错误
        if (response?.profile_update_error) {
          this.error = `反馈已记录，但画像更新失败: ${response.profile_update_error}`
        } else if (response?.profile_updated) {
          // 画像更新成功 → 刷新 profile store
          this._notifyProfileRefresh()
        }
      } catch (err: any) {
        this.error = err?.message || '反馈提交失败，请重试'
      }
    },

    // 通知 profile store 刷新（通过事件总线或直接引用）
    _notifyProfileRefresh() {
      try {
        // 动态导入避免循环依赖
        import('@/stores/profile').then(({ useProfileStore }) => {
          const ps = useProfileStore()
          if (ps.studentId) {
            ps.refreshProfile()
            ps.refreshDashboard()
          }
        }).catch(() => {})
      } catch { /* 非关键 */ }
    },

    applyResponse(response: AssistantChatResponse) {
      this.conversationId = response.conversation_id
      this.agentTrace = response.agent_trace
      this.actions = response.actions
      this.suggestedNextActions = response.suggested_next_actions
      this.evidence = response.evidence
      this.resources = response.resources
      this.resourceRecordId = response.resource_record_id || null
      this.pathPlan = response.path_plan
      this.exerciseFeedback = response.exercise_feedback
      this.profileDelta = response.profile_delta
      // 澄清
      this.needsClarification = response.needs_clarification || false
      this.clarificationOptions = response.clarification_options || []
      this.clarificationQuestion = response.clarification_question || ''
      // 质量
      this.evidenceQualityScore = response.evidence_quality_score
      this.resourceQualityScore = response.resource_quality_score
      // 反思
      this.reflection = response.reflection || ''
      this.needsRefinement = response.needs_refinement || false
      this.relevantMemories = response.relevant_memories || []
      this.errors = response.errors
      const degraded = response.status === 'degraded' ? ' (降级模式)' : ''
      this.statusText = response.status === 'ok' ? '✅ 本轮学习助手已完成' : `⚠️ 本轮学习助手返回了提示或错误${degraded}`
    },

    localMessage(role: 'user' | 'assistant', content: string, response?: AssistantChatResponse): AssistantMessage {
      // 优先使用后端返回的真实 assistant_message_id
      const realId = (role === 'assistant' && response?.assistant_message_id)
        ? response.assistant_message_id
        : `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`
      return {
        id: realId,
        conversation_id: response?.conversation_id || this.conversationId || 'local',
        role,
        content,
        intent: response?.intent || '',
        target_node_id: response?.evidence?.resolved_uid || '',
        resource_record_id: response?.resource_record_id || null,
        resource_has_exercises: response?.resource_has_exercises || false,
        actions: response?.actions || [],
        suggested_next_actions: response?.suggested_next_actions || [],
        agent_trace: response?.agent_trace || [],
        created_at: new Date().toISOString()
      }
    }
  }
})
