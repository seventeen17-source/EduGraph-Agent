export interface RecommendationEvidence {
  source: string
  detail: string
  mastery?: number | null
  last_attempt?: string | null
}

export interface RecommendationItem {
  node_id: string
  node_name: string
  recommendation_type: string // weak_point/prerequisite/goal_related/forgetting_review/mistake_related
  reason: string
  score: number
  evidence?: RecommendationEvidence | null
  prerequisites?: string[]
  difficulty?: string | null
  chapter?: string | null
}

export interface DiagnosisRecommendResponse {
  recommended_nodes: string[]
  recommended_exercises: string[]
  reasoning: string[]
  node_priorities: Record<string, number>
  sorted_by_prerequisites: boolean
  recommendations?: RecommendationItem[]
  current_node_id?: string | null
}
