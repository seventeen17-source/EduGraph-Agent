import { apiClient } from './client'

export interface RuntimeComponentStatus {
  name: string
  status: string
  detail: string
  metadata: Record<string, any>
}

export interface RuntimeStatusResponse {
  status: string
  environment: string
  components: Record<string, RuntimeComponentStatus>
  degraded_features: string[]
  warnings: string[]
}

export function getRuntimeStatus() {
  return apiClient.get<RuntimeStatusResponse>('/api/admin/runtime-status').then((res) => res.data)
}

export interface ResourceMetrics {
  total_generations: number
  avg_quality_score: number
  by_type: Record<string, number>
}

export interface ExerciseMetrics {
  total_sessions: number
  total_attempts: number
  avg_accuracy: number
}

export interface BusinessMetricsResponse {
  resource_generation: ResourceMetrics
  exercises: ExerciseMetrics
  active_users: number
  generated_at: string
}

export function getBusinessMetrics() {
  return apiClient.get<BusinessMetricsResponse>('/api/admin/metrics').then((res) => res.data)
}
