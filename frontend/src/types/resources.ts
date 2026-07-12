import type { GraphNode } from './graph'
import type { EvidencePackage } from './graphrag'
import type { ResourceType } from './profile'

export interface GeneratedDocument {
  title: string
  content: string
  key_points: string[]
  source_uids: string[]
}

export interface GeneratedMindmap {
  title: string
  format: 'mermaid'
  content: string
  source_uids: string[]
}

export interface GeneratedExercise {
  title: string
  type: 'choice' | 'short_answer' | 'coding' | 'case_analysis'
  related_node_id: string
  difficulty: number
  question: string
  options: Array<{ label: string; text: string }>
  answer: Record<string, any>
  adaptive_feedback: Record<string, any>
  source_uids: string[]
}

export interface GeneratedVideoScript {
  title: string
  target_duration_seconds: number
  scenes: Array<{
    scene_no: number
    title: string
    visual: string
    narration: string
    animation_hint: string
  }>
  source_uids: string[]
}

export interface GeneratedCodeCase {
  title: string
  language: 'python'
  related_node_id: string
  code: string
  explanation: string
  test_cases: Array<Record<string, any>>
  source_uids: string[]
}

export interface GeneratedResources {
  document: GeneratedDocument | null
  mindmap: GeneratedMindmap | null
  exercises: GeneratedExercise[]
  video_script: GeneratedVideoScript | null
  code_case: GeneratedCodeCase | null
}

export interface AgentTraceItem {
  agent: string
  status: 'done' | 'skipped' | 'failed'
  summary: string
}

export interface AlternativeNode {
  uid: string
  name: string
  reason: string
}

export interface ResourceGenerateResponse {
  resource_record_id?: string | null
  query: string
  resolved_uid: string | null
  center_node: GraphNode | null
  evidence: EvidencePackage
  resources: GeneratedResources
  quality_report: {
    grounded: boolean
    score: number
    warnings: string[]
    source_uids: string[]
  }
  agent_trace: AgentTraceItem[]
  uncertainty: string[]
  missing_evidence: string[]
  // 解析质量
  resolution_quality: 'exact' | 'fallback' | 'none'
  suggested_alternatives: AlternativeNode[]
  resolution_notice: string
}

export interface ResourceGenerateRequest {
  query: string
  node_id?: string | null
  student_id?: string | null
  student_profile?: import('./profile').StudentProfileInput | null
  exercise_count?: number | null
  exercise_type?: 'choice' | 'short_answer' | 'coding' | 'case_analysis' | null
  resource_types: ResourceType[]
}

export interface ResourceCenterItem {
  id: string
  student_id: string
  query: string
  resolved_uid: string
  center_node_name: string
  resource_types: ResourceType[]
  quality_score: number
  created_at: string
}

export interface ResourceCenterListResponse {
  items: ResourceCenterItem[]
}

export interface ResourceCenterDetail {
  id: string
  student_id: string
  query: string
  resolved_uid: string
  center_node_name: string
  resource_types: ResourceType[]
  resources: GeneratedResources
  evidence: EvidencePackage
  quality_report: ResourceGenerateResponse['quality_report']
  agent_trace: AgentTraceItem[]
  quality_score: number
  created_at: string
}
