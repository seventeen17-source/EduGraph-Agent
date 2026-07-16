export type KnowledgeLevel = 'weak' | 'basic' | 'intermediate' | 'advanced'
export type ResourceType = 'document' | 'diagram' | 'mindmap' | 'exercise' | 'video_script' | 'code_case' | 'image'

export interface KnownTopic {
  topic: string
  level: KnowledgeLevel | string
  evidence: string
}

export interface StudentProfileInput {
  weak_points: string[]
  preferences: string[]
  goal?: string | null
  mastery: Record<string, number>
}

export interface ProfileUpdateRecord {
  timestamp: string
  trigger: string
  trigger_detail: string
  updated_fields: string[]
  summary: string
}

export interface ProfileChatMessageRecord {
  id?: string | null
  role: 'user' | 'assistant' | 'system'
  content: string
  round_no: number
  created_at: string
}

export interface KnowledgePointMastery {
  node_id: string
  node_name: string
  chapter_id: string
  mastery_score: number
  level: KnowledgeLevel
  confidence: number
  attempts: number
  correct_count: number
  last_practiced_at?: string | null
}

export interface StudentProfile {
  student_id: string
  display_name?: string | null
  created_at: string
  updated_at: string
  completeness: number
  background: {
    major: string
    grade: number | null
    school_type: string
    course_foundation: string[]
    source: string
    confidence: number
    last_updated: string | null
  }
  learning_goal: {
    goal_type: string[]
    description: string
    target_course: string
    expected_hours_per_week: number | null
    source: string
    confidence: number
    last_updated: string | null
    goals: string[]
  }
  knowledge_base: {
    known_topics: KnownTopic[]
    unknown_topics: string[]
    source: string
    confidence: number
    last_updated: string | null
  }
  progress: {
    current_chapter_id: string | null
    completed_node_ids: string[]
    in_progress_node_ids: string[]
    completion_rate: number
    last_active_at: string | null
    source: string
    confidence: number
  }
  cognitive_style: {
    primary: string
    secondary: string
    style_ranking: string[]
    source: string
    confidence: number
    last_updated: string | null
  }
  weak_points: {
    self_reported: Array<{ topic: string; node_id?: string | null; description: string }>
    diagnosed: Array<{ node_id: string; error_rate: number; total_attempts: number; last_wrong_at: string | null }>
    source: string
    confidence: number
    last_updated: string | null
  }
  preferences: {
    resource_ranking: ResourceType[]
    session_length: string
    difficulty_preference: string
    source: string
    confidence: number
    last_updated: string | null
  }
  ability_state: {
    programming: KnowledgeLevel
    mathematics: KnowledgeLevel
    reading_papers: KnowledgeLevel
    application: KnowledgeLevel
    source: string
    confidence: number
    last_updated: string | null
  }
  node_mastery: Record<string, KnowledgePointMastery>
  learning_behavior: LearningBehaviorProfile
}

export interface FormatEffectiveness {
  format: string
  effectiveness_score: number
  positive_count: number
  negative_count: number
  last_updated: string | null
}

export interface DepthPreference {
  too_shallow_count: number
  just_right_count: number
  too_deep_count: number
  preferred_level: string
}

export interface ComprehensionGap {
  node_id: string
  signals: Array<Record<string, any>>
  severity: number
  inferred_root_cause: string
  recommended_strategy: string
  detected_at: string | null
  resolved: boolean
}

export interface PerNodeStrategy {
  node_id: string
  best_approach: string
  avoid_approach: string
  confidence: number
  evidence_count: number
  last_updated: string | null
}

export interface EngagementPattern {
  total_interactions: number
  total_feedback_given: number
  follow_up_rate: number
  clarification_rate: number
  avg_dwell_seconds: number
  preferred_hours: number[]
  hint_usage_rate: number
}

export interface FeedbackInsight {
  key: string
  description: string
  category: string
  confidence: number
  actionable: string
  related_nodes: string[]
  created_at: string | null
}

// ── 成长时间轴 ──

export interface TimelineEvent {
  date: string
  time: string | null
  type: string
  icon: string
  title: string
  description: string
  node_id: string | null
  node_name: string | null
  score_before: number | null
  score_after: number | null
  chapter_id: string | null
  related_id: string | null
  related_type: string | null
  action_url: string | null
}

export interface DailySummary {
  date: string
  active_score: number
  event_count: number
  top_event: TimelineEvent | null
  events: TimelineEvent[]
}

export interface WeeklySummary {
  week_start: string
  week_label: string
  active_days: number
  total_score: number
  days: DailySummary[]
}

export interface MonthlySummary {
  month: string
  month_label: string
  active_days: number
  weeks: WeeklySummary[]
  new_concepts: number
  exercises_done: number
  questions_asked: number
}

export interface ForgettingNode {
  node_id: string
  node_name: string
  mastery_score: number
  days_since_review: number
  estimated_forgetting_rate: number
  threshold_days: number
  urgency: 'low' | 'medium' | 'high'
  action_url: string | null
}

export interface LearningStats {
  total_active_days: number
  current_streak: number
  longest_streak: number
  mastered_concepts: number
  strong_concepts: number
  total_exercises: number
  total_questions: number
  total_feedback: number
  this_week_days: number
  last_week_days: number
  week_trend: 'up' | 'down' | 'stable'
}

export interface TimelineResponse {
  student_id: string
  months: MonthlySummary[]
  stats: LearningStats
  forgetting_soon: ForgettingNode[]
  generated_at: string
}

// ── 周报 / 月报 ──

export interface ReportExerciseStats {
  total_sessions: number
  total_attempts: number
  correct_attempts: number
  accuracy: number
  practiced_nodes: number
  active_days: number
}

export interface ReportMasteryChangeItem {
  node_id: string
  node_name: string
  mastery_score: number
  level: KnowledgeLevel
  updated: boolean
}

export interface ReportMasteryChanges {
  updated_nodes: ReportMasteryChangeItem[]
  new_mastered: ReportMasteryChangeItem[]
  needs_attention: ReportMasteryChangeItem[]
  total_mastered: number
  total_strong: number
}

export interface ReportRecommendationItem {
  node_id: string
  node_name: string
  reason: string
  urgency: 'high' | 'medium' | 'low'
}

export interface WeeklyReportResponse {
  student_id: string
  period_days: number
  period_label: string
  generated_at: string
  exercise_stats: ReportExerciseStats
  mastery_changes: ReportMasteryChanges
  forgetting_warnings: ForgettingNode[]
  recommendations: ReportRecommendationItem[]
  profile_updates: ProfileUpdateRecord[]
  summary: string
}

// ── 行为画像 ──

export interface LearningBehaviorProfile {
  format_effectiveness: Record<string, FormatEffectiveness>
  depth_preference: DepthPreference
  comprehension_gaps: ComprehensionGap[]
  effective_strategies: Record<string, PerNodeStrategy>
  engagement: EngagementPattern
  insights: FeedbackInsight[]
  pace_preference: string
  inferred_cognitive_level: string
  total_feedback_count: number
  last_analyzed_at: string | null
  last_updated: string | null
}

export interface ProfileChatResponse {
  reply: string
  session_status: 'building' | 'completed'
  current_round: number
  profile: StudentProfile
  completeness: number
  updated_dimensions: string[]
  missing_dimensions: string[]
}

export interface ProfileDimensionView {
  key: string
  title: string
  icon: string
  summary: string
  tags: string[]
  confidence: number
  source: string
  last_updated: string | null
  status: 'filled' | 'missing' | 'inferred' | 'low_confidence'
  editable: boolean
}

export interface ProfileDashboardResponse {
  student_id: string
  display_name: string
  headline: string
  completeness: number
  missing_dimensions: string[]
  dimensions: ProfileDimensionView[]
  weak_point_rank: Array<{ label: string; node_id?: string | null; source: string; score: number }>
  mastery_overview: Array<{
    node_id: string
    node_name: string
    chapter_id: string
    mastery_score: number
    level: KnowledgeLevel
    confidence: number
  }>
  recent_updates: ProfileUpdateRecord[]
  personalization_reasons: string[]
}

export interface ProfileEventResponse {
  profile: StudentProfile
  dashboard: ProfileDashboardResponse
  updated_node_mastery: string[]
  update_event: ProfileUpdateRecord
}

export interface ExerciseRoundAttempt {
  exercise_id: string
  node_ids: string[]
  is_correct: boolean
  difficulty?: number
  cognitive_level?: string
  used_hint?: boolean
}

// ── 掌握度证据链 ──

export interface MasteryEvidenceRecord {
  id: string
  student_id: string
  node_id: string
  source_type: string  // exercise_result/forgetting_detection/diagnosis/self_report/feedback
  source_id: string
  score_delta: number
  confidence_delta: number
  summary: string
  created_at: string
}
