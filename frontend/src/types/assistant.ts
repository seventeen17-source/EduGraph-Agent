import type { EvidencePackage } from './graphrag'
import type { GeneratedResources } from './resources'

export type AssistantIntent =
  | 'profile_update'
  | 'concept_explain'
  | 'resource_generate'
  | 'exercise_help'
  | 'path_plan'
  | 'progress_update'
  | 'assessment_review'
  | 'navigation_help'
  | 'general_learning_chat'
  | 'clarify_intent'

export interface ClarifyOption {
  value: string
  label: string
  description: string
  intent: AssistantIntent | null
  target_node_id: string | null
}

export interface AssistantChatRequest {
  student_id: string
  message: string
  conversation_id?: string | null
}

export interface AssistantAction {
  type: string
  label: string
  description: string
  route: string
  query: Record<string, any>
  node_id?: string | null
  resource_record_id?: string | null
  payload: Record<string, any>
}

export interface AssistantTraceItem {
  node: string
  status: 'started' | 'done' | 'skipped' | 'failed'
  summary: string
  metadata: Record<string, any>
  created_at: string
}

export interface SuggestedNextAction {
  label: string
  description: string
  action_type: string
  priority: number
  route: string
  query: Record<string, any>
}

export interface PathPlanNode {
  node_id: string
  label: string
  status: 'recommended' | 'in_progress' | 'mastered' | 'needs_review' | 'added_by_mistake' | 'skipped_by_student'
  reason: string
  recommended_resource_types: string[]
}

export interface AssistantPathPlan {
  mode: 'current_goal' | 'gap_filling' | 'exam_review' | 'project_practice' | 'free_exploration'
  title: string
  goal: string
  nodes: PathPlanNode[]
  reasons: string[]
}

export interface ExerciseFeedback {
  summary: string
  likely_causes: string[]
  hints: string[]
  related_node_ids: string[]
}

export interface MemoryEntrySummary {
  id: string
  student_question_summary: string
  key_insight: string
  confusion_nodes: string[]
  caution_topics: string[]
  learning_preference_hint: string
  intent: string
  node_ids: string[]
  engagement_level: string
  suggested_follow_up: string
  score: number
  timestamp: string
}

export interface AssistantChatResponse {
  // 记忆
  relevant_memories: MemoryEntrySummary[]
  reply: string
  intent: AssistantIntent | null
  intent_confidence: number
  conversation_id: string
  assistant_message_id: string
  status: 'ok' | 'degraded' | 'unavailable' | 'error'
  // 意图澄清
  needs_clarification: boolean
  clarification_options: ClarifyOption[]
  clarification_question: string
  // 质量评分
  evidence_quality_score: number | null
  resource_quality_score: number | null
  // 反思
  reflection: string
  needs_refinement: boolean
  // 原有字段
  actions: AssistantAction[]
  suggested_next_actions: SuggestedNextAction[]
  profile_delta: Record<string, any>
  evidence: EvidencePackage | null
  resource_record_id?: string | null
  resources: GeneratedResources | null
  path_plan: AssistantPathPlan | null
  exercise_feedback: ExerciseFeedback | null
  agent_trace: AssistantTraceItem[]
  errors: string[]
}

export interface AssistantMessage {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  intent: string
  target_node_id: string
  resource_record_id?: string | null
  actions: AssistantAction[]
  agent_trace: AssistantTraceItem[]
  created_at: string
}

export interface AssistantConversation {
  id: string
  student_id: string
  title: string
  last_intent: string
  updated_at: string
  created_at: string
}

export interface AssistantHistoryResponse {
  student_id: string
  conversations: AssistantConversation[]
  messages: AssistantMessage[]
}

export interface LiveTraceItem {
  node: string
  label: string
  status: 'running' | 'done' | 'failed' | 'pending'
  summary: string
}

export interface AssistantStreamHandlers {
  onEvent?: (event: string, data: any) => void
  onNodeStart?: (node: string, label: string) => void
  onNodeComplete?: (node: string, label: string) => void
  onTraceItem?: (node: string, status: string, summary: string) => void
  onQualityUpdate?: (type: string, score: number, reason: string) => void
  onFinal?: (response: AssistantChatResponse) => void
  onError?: (error: Error) => void
}