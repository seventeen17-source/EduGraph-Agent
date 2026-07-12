import type { GraphNode, GraphPath } from './graph'

export interface DependencyPath {
  path_nodes: string[]
  path_labels: string[]
  depth: number
  reasoning: string
  intermediate_evidence: Record<string, {
    has_doc: boolean
    has_code: boolean
    has_exercise: boolean
    has_misconception: boolean
  }>
}

export interface MultiHopSummary {
  center_node_id: string
  total_dependencies: number
  max_depth_found: number
  dependency_paths: DependencyPath[]
  direct_prerequisites: string[]
  transitive_prerequisites: string[]
  reasoning_chain: string[]
}

export interface EvidencePackage {
  query: string
  resolved_uid: string | null
  center_node: GraphNode | null
  query_type: string
  evidence_score: number
  relation_summary: string[]
  recommended_next_actions: string[]
  prerequisites: GraphPath[]
  related_nodes: GraphPath[]
  exercises: GraphNode[]
  document_chunks: GraphNode[]
  code_cases: GraphNode[]
  misconceptions: GraphNode[]
  semantic_hits: CourseSemanticHit[]
  graph_paths: GraphPath[]
  sources: GraphNode[]
  ranking_reason: string[]
  student_profile_adaptation: Record<string, any>
  uncertainty: string[]
  missing_evidence: string[]
  // 多跳依赖
  multi_hop_summary: MultiHopSummary | null
  dependency_paths: DependencyPath[]
  resolution_quality?: string
  suggested_alternatives?: Array<Record<string, any>>
}

export interface CourseSemanticView {
  id: string
  text: string
  target_uid: string
  target_type: 'KnowledgePoint' | 'DocumentChunk' | 'Misconception' | 'Exercise' | 'CodeCase'
  view_type: 'student_confusion' | 'concept_explanation' | 'error_diagnosis' | 'code_intent' | 'learning_action' | 'raw_summary'
  node_ids: string[]
  chapter_id: string
  source_uids: string[]
  title: string
  difficulty?: number | null
  cognitive_level: string
  tags: string[]
}

export interface CourseSemanticHit {
  view: CourseSemanticView
  score: number
  semantic_score: number
  graph_bonus: number
  profile_bonus: number
  rank_reason: string[]
}
