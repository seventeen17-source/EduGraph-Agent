import { apiClient } from './client'
import type {
  ProfileChatResponse,
  ProfileChatMessageRecord,
  ProfileDashboardResponse,
  ProfileEventResponse,
  ProfileUpdateRecord,
  StudentProfile,
  TimelineResponse,
  ExerciseRoundAttempt
} from '@/types/profile'

export function initProfile(payload: { student_id: string; display_name?: string; message: string }) {
  return apiClient.post<ProfileChatResponse>('/api/profile/init', payload).then((res) => res.data)
}

export function chatProfile(payload: { student_id: string; display_name?: string; message: string }) {
  return apiClient.post<ProfileChatResponse>('/api/profile/chat', payload).then((res) => res.data)
}

export function getProfile(studentId: string) {
  return apiClient.get<StudentProfile>(`/api/profile/${studentId}`).then((res) => res.data)
}

export function getProfileDashboard(studentId: string) {
  return apiClient.get<ProfileDashboardResponse>(`/api/profile/${studentId}/dashboard`).then((res) => res.data)
}

export function getProfileHistory(studentId: string) {
  return apiClient.get<ProfileUpdateRecord[]>(`/api/profile/${studentId}/history`).then((res) => res.data)
}

export function getProfileChatHistory(studentId: string) {
  return apiClient.get<ProfileChatMessageRecord[]>(`/api/profile/${studentId}/chat-history`).then((res) => res.data)
}

export function patchProfile(studentId: string, payload: { dimension: string; value: Record<string, any> }) {
  return apiClient.patch<StudentProfile>(`/api/profile/${studentId}`, payload).then((res) => res.data)
}

export function updateProfileFromExercise(payload: {
  student_id: string
  exercise_id: string
  node_ids: string[]
  is_correct: boolean
  difficulty?: number
  cognitive_level?: string
  used_hint?: boolean
}) {
  return apiClient.post<ProfileEventResponse>('/api/profile/events/exercise-result', payload).then((res) => res.data)
}

export function updateProfileFromExerciseRound(payload: {
  student_id: string
  round_id?: string | null
  attempts: ExerciseRoundAttempt[]
}) {
  return apiClient.post<ProfileEventResponse>('/api/profile/events/exercise-round', payload).then((res) => res.data)
}

export function updateLearningProgress(payload: {
  student_id: string
  completed_node_ids?: string[]
  in_progress_node_ids?: string[]
  current_chapter_id?: string
  completion_rate?: number
}) {
  return apiClient.post<ProfileEventResponse>('/api/profile/events/learning-progress', payload).then((res) => res.data)
}

export function getLearningTimeline(studentId: string, days = 90) {
  return apiClient.get<TimelineResponse>(`/api/profile/${studentId}/timeline?days=${days}`).then((res) => res.data)
}
