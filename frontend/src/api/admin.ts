import { apiClient } from './client'

export interface RuntimeComponentStatus {
  name: string
  status: string
  detail: string
  metadata: Record<string, any>
}

export interface RuntimeStatusResponse {
  status: string
  environment: string
  components: Record<string, RuntimeComponentStatus>
  degraded_features: string[]
  warnings: string[]
}

export function getRuntimeStatus() {
  return apiClient.get<RuntimeStatusResponse>('/api/admin/runtime-status').then((res) => res.data)
}
