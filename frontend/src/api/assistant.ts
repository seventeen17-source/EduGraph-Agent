import { apiClient, defaultApiBaseUrl } from './client'
import type {
  AssistantChatRequest,
  AssistantChatResponse,
  AssistantHistoryResponse,
  AssistantStreamHandlers
} from '@/types/assistant'

export function chatAssistant(payload: AssistantChatRequest) {
  return apiClient.post<AssistantChatResponse>('/api/assistant/chat', payload).then((res) => res.data)
}

export function getAssistantHistory(studentId: string) {
  return apiClient.get<AssistantHistoryResponse>(`/api/assistant/${studentId}/history`).then((res) => res.data)
}

export interface FeedbackSubmitPayload {
  message_id: string
  student_id: string
  tags: string[]
  free_text?: string | null
  conversation_id?: string
  intent?: string
  target_node_id?: string
}

export interface FeedbackSubmitResponse {
  ok: boolean
  feedback_id: string
  created: boolean
  profile_updated: boolean
  profile_update_error: string
  adaptation_summary: string
  action_taken: string
  action_result: string
}

export function submitFeedback(payload: FeedbackSubmitPayload) {
  return apiClient.post<FeedbackSubmitResponse>('/api/assistant/feedback', payload).then((res) => res.data)
}

export async function streamAssistant(
  payload: AssistantChatRequest,
  handlers: AssistantStreamHandlers = {},
  signal?: AbortSignal,
) {
  const baseURL = defaultApiBaseUrl()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  try {
    const raw = localStorage.getItem('edugraph_auth')
    if (raw) {
      const { accessToken } = JSON.parse(raw)
      if (accessToken) headers.Authorization = `Bearer ${accessToken}`
    }
  } catch {}
  const response = await fetch(`${baseURL}/api/assistant/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
    signal,
  })
  if (!response.ok || !response.body) {
    throw new Error(`学习助手流式请求失败：${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''
    for (const chunk of chunks) {
      const eventLine = chunk.split('\n').find((line) => line.startsWith('event:'))
      const dataLine = chunk.split('\n').find((line) => line.startsWith('data:'))
      const event = eventLine?.replace('event:', '').trim() || 'message'
      const data = dataLine ? JSON.parse(dataLine.replace('data:', '').trim()) : {}
      handlers.onEvent?.(event, data)
      switch (event) {
        case 'node_started':
          handlers.onNodeStart?.(data.node, data.label || data.node)
          break
        case 'node_completed':
          handlers.onNodeComplete?.(data.node, data.label || data.node)
          break
        case 'trace_item':
          handlers.onTraceItem?.(data.node, data.status, data.summary)
          break
        case 'quality_update':
          handlers.onQualityUpdate?.(data.type, data.score, data.reason)
          break
        case 'final_response':
          handlers.onFinal?.(data as AssistantChatResponse)
          break
        case 'error':
          handlers.onError?.(new Error(data.message || '流式执行异常'))
          break
      }
    }
  }
}
