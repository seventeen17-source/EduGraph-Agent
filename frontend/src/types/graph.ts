export interface GraphNode {
  uid: string
  labels: string[]
  properties: Record<string, any>
}

export interface GraphRelationship {
  type: string
  source_uid: string
  target_uid: string
  properties: Record<string, any>
}

export interface GraphPath {
  nodes: GraphNode[]
  relationships: GraphRelationship[]
}

export interface SubgraphResult {
  center_uid: string
  nodes: GraphNode[]
  relationships: GraphRelationship[]
  paths: GraphPath[]
}

export interface NodeMasteryInfo {
  value: number
  trend: string // stable/rising/falling
  last_attempt: string | null
}

export interface NodeWeakStatus {
  is_weak: boolean
  reason: string | null
}

export interface NodeForgettingRisk {
  level: string // low/medium/high/unknown
  days_since_last: number | null
  suggested_review_date: string | null
}

export interface NodeRecommendation {
  action: string // recommend_now/learn_prerequisites_first/skip/review
  reason: string
}

export interface NodeEdgeWithWeight {
  uid: string
  name: string
  weight: number
  explanation: string
  mastered?: boolean
}

export interface NodeDetailResponse {
  node: GraphNode
  mastery: NodeMasteryInfo | null
  weak_status: NodeWeakStatus | null
  forgetting_risk: NodeForgettingRisk | null
  recommendation: NodeRecommendation | null
  prerequisites: NodeEdgeWithWeight[]
  next_nodes: NodeEdgeWithWeight[]
}

export interface NodeWithMastery {
  uid: string
  name: string
  chapter: string
  difficulty: string
  summary: string
  mastery_score: number
  status: 'mastered' | 'weak' | 'forgetting' | 'learning' | 'unlearned'
  last_practiced: string | null
}

export interface LearningOverview {
  total_nodes: number
  mastered: number
  weak: number
  forgetting: number
  learning: number
  unlearned: number
  mastery_rate: number
  nodes: NodeWithMastery[]
}

export interface RecommendedStart {
  uid: string
  name: string
  reason: string
  status: string
}
