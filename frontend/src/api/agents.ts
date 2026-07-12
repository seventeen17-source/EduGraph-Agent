import { apiClient } from './client'
import type {
  ResourceCenterDetail,
  ResourceCenterListResponse,
  ResourceGenerateRequest,
  ResourceGenerateResponse
} from '@/types/resources'

export function generateResources(payload: ResourceGenerateRequest) {
  return apiClient.post<ResourceGenerateResponse>('/api/agents/generate-resources', payload).then((res) => res.data)
}

export function listResourceCenter(params?: { student_id?: string | null; limit?: number }) {
  return apiClient.get<ResourceCenterListResponse>('/api/agents/resource-center', { params }).then((res) => res.data)
}

export function getResourceCenterDetail(resourceId: string) {
  return apiClient.get<ResourceCenterDetail>(`/api/agents/resource-center/${resourceId}`).then((res) => res.data)
}

export function updateResourceCenterMindmap(resourceId: string, payload: { title?: string | null; content: string }) {
  return apiClient
    .patch<ResourceCenterDetail>(`/api/agents/resource-center/${resourceId}/mindmap`, payload)
    .then((res) => res.data)
}
