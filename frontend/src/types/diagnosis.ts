export interface DiagnosisRecommendResponse {
  recommended_nodes: string[]
  recommended_exercises: string[]
  reasoning: string[]
  node_priorities: Record<string, number>
  sorted_by_prerequisites: boolean
}
