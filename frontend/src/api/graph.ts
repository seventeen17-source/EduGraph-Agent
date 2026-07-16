import { apiClient } from './client'
import type { GraphNode, NodeDetailResponse, SubgraphResult, LearningOverview, RecommendedStart, NodeWithMastery } from '@/types/graph'

export function getGraphNode(uid: string) {
  return apiClient.get<GraphNode>(`/api/graph/node/${uid}`).then((res) => res.data)
}

export function getNodeDetail(uid: string, studentId: string) {
  return apiClient.get<NodeDetailResponse>(`/api/graph/node-detail/${uid}`, { params: { student_id: studentId } }).then((res) => res.data)
}

export function searchGraphNodes(q: string, limit = 10) {
  return apiClient.get<GraphNode[]>('/api/graph/search', { params: { q, limit } }).then((res) => res.data)
}

export function getSubgraph(uid: string, params: { depth?: number; limit?: number; relations?: string[] } = {}) {
  return apiClient.get<SubgraphResult>(`/api/graph/subgraph/${uid}`, { params }).then((res) => res.data)
}

export function getAllNodes(limit = 200) {
  return apiClient.get<GraphNode[]>('/api/graph/all', { params: { limit } }).then((res) => res.data)
}

export function getLearningOverview(studentId: string) {
  return apiClient.get<LearningOverview>('/api/graph/learning-overview', { params: { student_id: studentId } }).then((res) => res.data)
}

export function getRecommendedStart(studentId: string) {
  return apiClient.get<RecommendedStart>('/api/graph/recommended-start', { params: { student_id: studentId } }).then((res) => res.data)
}

export function getAllNodesWithMastery(studentId: string) {
  return apiClient.get<NodeWithMastery[]>('/api/graph/all-with-mastery', { params: { student_id: studentId } }).then((res) => res.data)
}
