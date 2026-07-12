import { apiClient } from './client'
import type { EvidencePackage } from '@/types/graphrag'
import type { StudentProfileInput } from '@/types/profile'

export function getEvidenceByUid(uid: string) {
  return apiClient.get<EvidencePackage>('/api/graphrag/evidence', { params: { uid } }).then((res) => res.data)
}

export function queryEvidence(payload: { query: string; student_profile?: StudentProfileInput | null; student_id?: string | null; top_k?: number }) {
  return apiClient.post<EvidencePackage>('/api/graphrag/query', payload).then((res) => res.data)
}
