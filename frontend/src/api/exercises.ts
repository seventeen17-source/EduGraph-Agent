import { apiClient } from './client'
import type {
  ExerciseMistakeListResponse,
  ExerciseSessionListResponse,
  ExerciseSessionRecord,
  ExerciseSessionSubmitRequest,
  ExerciseSessionSubmitResponse,
  ExerciseStatsResponse,
} from '@/types/exercises'

export function submitExerciseSession(payload: ExerciseSessionSubmitRequest) {
  return apiClient.post<ExerciseSessionSubmitResponse>('/api/exercises/sessions', payload).then((res) => res.data)
}

export function listExerciseSessions(studentId: string, params: { limit?: number; offset?: number } = {}) {
  return apiClient.get<ExerciseSessionListResponse>(`/api/exercises/sessions/${studentId}`, { params }).then((res) => res.data)
}

export function getExerciseSession(studentId: string, sessionId: string) {
  return apiClient.get<ExerciseSessionRecord>(`/api/exercises/sessions/${studentId}/${sessionId}`).then((res) => res.data)
}

export function listExerciseMistakes(studentId: string, params: { limit?: number; offset?: number; node_id?: string } = {}) {
  return apiClient.get<ExerciseMistakeListResponse>(`/api/exercises/mistakes/${studentId}`, { params }).then((res) => res.data)
}

export function getExerciseStats(studentId: string) {
  return apiClient.get<ExerciseStatsResponse>(`/api/exercises/stats/${studentId}`).then((res) => res.data)
}

export function bookmarkExerciseAttempt(attemptId: string, payload: { student_id: string; tag?: string; note?: string }) {
  return apiClient.post(`/api/exercises/attempts/${attemptId}/bookmark`, payload).then((res) => res.data)
}

export function reviewExerciseAttempt(attemptId: string, payload: {
  student_id: string
  review_result: 'correct' | 'wrong' | 'partial' | 'skipped'
  review_session_id?: string
  mastery_delta?: number
  notes?: string
}) {
  return apiClient.post(`/api/exercises/attempts/${attemptId}/review`, payload).then((res) => res.data)
}
