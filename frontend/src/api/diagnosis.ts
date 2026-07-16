import { apiClient } from './client'
import type { DiagnosisRecommendResponse } from '@/types/diagnosis'
import type { StudentProfileInput } from '@/types/profile'

export function recommendDiagnosis(payload: {
  student_profile: StudentProfileInput
  top_k?: number
  node_mastery?: Record<string, any>
  target_goal?: string | null
}) {
  return apiClient.post<DiagnosisRecommendResponse>('/api/diagnosis/recommend', payload).then((res) => res.data)
}
