import type { ProfileDashboardResponse, ProfileEventResponse, StudentProfile } from './profile'

export interface ExerciseAttemptSubmit {
  exercise_id: string
  exercise_title: string
  exercise_type: string
  related_node_id: string
  related_node_name: string
  exercise_snapshot: Record<string, any>
  student_answer: Record<string, any>
  expected_answer: Record<string, any>
  is_correct: boolean | null
  score?: number | null
  difficulty: number
  cognitive_level: string
  used_hint: boolean
  time_spent_seconds: number
  feedback: Record<string, any>
  misconception_tags: string[]
  source_uids: string[]
}

export interface ExerciseSessionSubmitRequest {
  student_id: string
  round_id?: string | null
  source_type: string
  source_id?: string
  target_node_id: string
  target_node_name: string
  title: string
  duration_seconds: number
  started_at?: string | null
  attempts: ExerciseAttemptSubmit[]
}

export interface ExerciseAttemptRecord {
  id: string
  session_id: string
  student_id: string
  exercise_id: string
  exercise_title: string
  exercise_type: string
  related_node_id: string
  related_node_name: string
  exercise_snapshot: Record<string, any>
  student_answer: Record<string, any>
  expected_answer: Record<string, any>
  is_correct: boolean
  score: number
  difficulty: number
  cognitive_level: string
  used_hint: boolean
  time_spent_seconds: number
  feedback: Record<string, any>
  misconception_tags: string[]
  source_uids: string[]
  created_at: string
}

export interface ExerciseSessionRecord {
  id: string
  student_id: string
  round_id: string
  source_type: string
  source_id: string
  target_node_id: string
  target_node_name: string
  title: string
  status: string
  total_count: number
  answered_count: number
  correct_count: number
  accuracy: number
  duration_seconds: number
  mastery_before: Record<string, number>
  mastery_after: Record<string, number>
  weak_nodes: string[]
  summary: string
  started_at: string | null
  submitted_at: string
  created_at: string
  updated_at: string
  attempts: ExerciseAttemptRecord[]
}

export interface ExerciseSessionListResponse {
  student_id: string
  total: number
  items: ExerciseSessionRecord[]
}

export interface ExerciseMistakeListResponse {
  student_id: string
  total: number
  items: ExerciseAttemptRecord[]
}

export interface ExerciseStatsResponse {
  student_id: string
  total_sessions: number
  total_attempts: number
  correct_attempts: number
  accuracy: number
  mistake_count: number
  practiced_nodes: number
  recent_accuracy: number
  weak_node_counts: Record<string, number>
}

export interface ExerciseSessionSubmitResponse {
  session: ExerciseSessionRecord
  profile: StudentProfile
  dashboard: ProfileDashboardResponse
  updated_node_mastery: string[]
  update_event: ProfileEventResponse['update_event']
}
