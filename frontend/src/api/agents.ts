import { apiClient } from './client'
import type {
  ResourceCenterDetail,
  ResourceCenterListResponse,
  ResourceGenerateRequest,
  ResourceGenerateResponse,
  RetryResourceResponse
} from '@/types/resources'

export function generateResources(payload: ResourceGenerateRequest) {
  return apiClient.post<ResourceGenerateResponse>('/api/agents/generate-resources', payload).then((res) => res.data)
}

export function retryResourceType(payload: { resource_id: string; resource_type: string; student_id: string }) {
  return apiClient.post<RetryResourceResponse>('/api/agents/retry', payload).then((res) => res.data)
}

export function listResourceCenter(params?: { student_id?: string | null; limit?: number; q?: string; filter_by_weak_points?: boolean }) {
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
