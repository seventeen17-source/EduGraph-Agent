import { defineStore } from 'pinia'

import { generateResources, getResourceCenterDetail, listResourceCenter, updateResourceCenterMindmap } from '@/api/agents'
import { recommendDiagnosis } from '@/api/diagnosis'
import { getEvidenceByUid, queryEvidence } from '@/api/graphrag'
import { getGraphNode, getSubgraph } from '@/api/graph'
import type { DiagnosisRecommendResponse } from '@/types/diagnosis'
import type { GraphNode, SubgraphResult } from '@/types/graph'
import type { EvidencePackage } from '@/types/graphrag'
import type { ResourceType, StudentProfileInput } from '@/types/profile'
import type { ResourceCenterDetail, ResourceCenterItem, ResourceGenerateResponse } from '@/types/resources'

const AGENTS = ['RetrievalAgent', 'DocumentAgent', 'MindmapAgent', 'ExerciseAgent', 'VideoScriptAgent', 'CodeAgent', 'ImageAgent']

export const useLearningStore = defineStore('learning', {
  state: () => ({
    currentChapter: null as string | null,
    currentNodeId: 'ml_gradient_descent',
    currentNode: null as GraphNode | null,
    subgraph: null as SubgraphResult | null,
    evidencePackage: null as EvidencePackage | null,
    diagnosis: null as DiagnosisRecommendResponse | null,
    resourceResponse: null as ResourceGenerateResponse | null,
    resourceCenterItems: [] as ResourceCenterItem[],
    selectedResourceRecord: null as ResourceCenterDetail | null,
    agentStatuses: Object.fromEntries(AGENTS.map((agent) => [agent, 'waiting'])) as Record<string, string>,
    loadingGraph: false,
    loadingEvidence: false,
    loadingResources: false,
    loadingResourceCenter: false,
    error: null as string | null
  }),
  getters: {
    recommendedNodes(state): string[] {
      return state.diagnosis?.recommended_nodes || []
    }
  },
  actions: {
    resetAgentStatuses() {
      this.agentStatuses = Object.fromEntries(AGENTS.map((agent) => [agent, 'waiting']))
    },
    async loadGraph(uid?: string) {
      this.loadingGraph = true
      this.error = null
      try {
        const targetUid = uid || this.currentNodeId
        this.currentNodeId = targetUid
        const [node, subgraph] = await Promise.all([getGraphNode(targetUid), getSubgraph(targetUid, { depth: 1, limit: 80 })])
        this.currentNode = node
        this.subgraph = subgraph
      } catch (error: any) {
        this.error = error.displayMessage || '知识图谱加载失败'
      } finally {
        this.loadingGraph = false
      }
    },
    async loadEvidence(uidOrQuery?: string, profile?: StudentProfileInput | null, studentId?: string | null) {
      this.loadingEvidence = true
      this.error = null
      try {
        const target = uidOrQuery || this.currentNodeId
        this.evidencePackage = profile
          ? await queryEvidence({ query: target, student_profile: profile, student_id: studentId, top_k: 8 })
          : await getEvidenceByUid(target)
        if (this.evidencePackage.resolved_uid) {
          this.currentNodeId = this.evidencePackage.resolved_uid
        }
      } catch (error: any) {
        this.error = error.displayMessage || 'GraphRAG 证据包加载失败'
      } finally {
        this.loadingEvidence = false
      }
    },
    async loadDiagnosis(profile: StudentProfileInput, nodeMastery?: Record<string, any>, targetGoal?: string | null) {
      this.error = null
      try {
        this.diagnosis = await recommendDiagnosis({
          student_profile: profile, top_k: 5, node_mastery: nodeMastery || {}, target_goal: targetGoal || null
        })
      } catch (error: any) {
        this.error = error.displayMessage || '诊断推荐失败'
        this.diagnosis = {
          recommended_nodes: [],
          recommended_exercises: [],
          reasoning: ['诊断接口暂不可用，暂不生成推荐路径。'],
          node_priorities: {},
          sorted_by_prerequisites: false,
        }
      }
    },
    async generateForQuery(query: string, nodeId?: string, profile?: StudentProfileInput | null, resourceTypes?: ResourceType[], studentId?: string | null) {
      this.loadingResources = true
      this.error = null
      this.resourceResponse = null
      this.resetAgentStatuses()
      this.agentStatuses.RetrievalAgent = 'running'
      try {
        const response = await generateResources({
          query,
          node_id: nodeId || null,
          student_id: studentId,
          student_profile: profile || null,
          resource_types: resourceTypes || ['document', 'mindmap', 'exercise', 'video_script', 'code_case']
        })
        this.resourceResponse = response
        this.evidencePackage = response.evidence
        this.currentNode = response.center_node
        this.currentNodeId = response.resolved_uid || this.currentNodeId
        this.resetAgentStatuses()
        response.agent_trace.forEach((item) => {
          this.agentStatuses[item.agent] = item.status
        })
        for (const type of resourceTypes || []) {
          const agentName =
            type === 'document'
              ? 'DocumentAgent'
              : type === 'mindmap'
                ? 'MindmapAgent'
                : type === 'exercise'
                  ? 'ExerciseAgent'
                  : type === 'video_script'
                    ? 'VideoScriptAgent'
                    : type === 'image'
                      ? 'ImageAgent'
                      : 'CodeAgent'
          if (!this.agentStatuses[agentName] || this.agentStatuses[agentName] === 'waiting') {
            this.agentStatuses[agentName] = 'done'
          }
        }
        if (studentId) {
          await this.loadResourceCenter(studentId)
        }
        return response
      } catch (error: any) {
        this.error = error.displayMessage || 'AI 备课失败'
        Object.keys(this.agentStatuses).forEach((agent) => {
          if (this.agentStatuses[agent] === 'running') this.agentStatuses[agent] = 'failed'
        })
        throw error
      } finally {
        this.loadingResources = false
      }
    },
    async loadResourceCenter(studentId?: string | null, query = '', filterByWeakPoints = false) {
      this.loadingResourceCenter = true
      this.error = null
      try {
        const response = await listResourceCenter({
          student_id: studentId,
          limit: 60,
          q: query,
          filter_by_weak_points: filterByWeakPoints,
        })
        this.resourceCenterItems = response.items
      } catch (error: any) {
        this.error = error.displayMessage || '知识中心加载失败'
      } finally {
        this.loadingResourceCenter = false
      }
    },
    async loadResourceRecord(resourceId: string) {
      this.loadingResourceCenter = true
      this.error = null
      try {
        this.selectedResourceRecord = await getResourceCenterDetail(resourceId)
        this.resourceResponse = {
          resource_record_id: this.selectedResourceRecord.id,
          query: this.selectedResourceRecord.query,
          resolved_uid: this.selectedResourceRecord.resolved_uid || null,
          center_node: null,
          evidence: this.selectedResourceRecord.evidence,
          resources: this.selectedResourceRecord.resources,
          quality_report: this.selectedResourceRecord.quality_report,
          agent_trace: this.selectedResourceRecord.agent_trace,
          uncertainty: this.selectedResourceRecord.evidence.uncertainty,
          missing_evidence: this.selectedResourceRecord.evidence.missing_evidence,
          resolution_quality: 'exact',
          suggested_alternatives: [],
          resolution_notice: '',
        }
        this.evidencePackage = this.selectedResourceRecord.evidence
        this.currentNodeId = this.selectedResourceRecord.resolved_uid || this.currentNodeId
        return this.selectedResourceRecord
      } catch (error: any) {
        this.error = error.displayMessage || '资源详情加载失败'
        throw error
      } finally {
        this.loadingResourceCenter = false
      }
    },
    async saveResourceMindmap(resourceId: string, payload: { title?: string | null; content: string }) {
      this.loadingResourceCenter = true
      this.error = null
      try {
        this.selectedResourceRecord = await updateResourceCenterMindmap(resourceId, payload)
        if (this.resourceResponse) {
          this.resourceResponse.resources = this.selectedResourceRecord.resources
        }
        return this.selectedResourceRecord
      } catch (error: any) {
        this.error = error.displayMessage || '思维导图保存失败'
        throw error
      } finally {
        this.loadingResourceCenter = false
      }
    }
  }
})
