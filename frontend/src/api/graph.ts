import { apiClient } from './client'
import type { GraphNode, SubgraphResult } from '@/types/graph'

export function getGraphNode(uid: string) {
  return apiClient.get<GraphNode>(`/api/graph/node/${uid}`).then((res) => res.data)
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
