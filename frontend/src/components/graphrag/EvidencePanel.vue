<template>
  <el-card class="section-card">
    <template #header>
      <div class="panel-title">
        <span>学习导航</span>
        <el-tag v-if="evidence?.resolved_uid" type="primary" size="small">
          {{ displayNodeLabel(evidence.resolved_uid) }}
        </el-tag>
        <el-tag v-if="semanticHits.length" type="success" size="small">
          语义命中 {{ semanticHits.length }}
        </el-tag>
      </div>
    </template>

    <el-empty v-if="!evidence" description="暂无证据数据" />
    <div v-else class="evidence-body">
      <div class="concept-summary">
        {{ localizeText(evidence.center_node?.properties?.summary || '当前知识点暂无摘要。') }}
      </div>

      <el-alert
        v-if="evidence.resolution_quality && evidence.resolution_quality !== 'exact'"
        :type="evidence.resolution_quality === 'none' ? 'warning' : 'info'"
        :title="resolutionNotice"
        :closable="false"
        show-icon
      />

      <div v-if="mergeReport" class="fusion-banner">
        <span class="fusion-title">HybridRAG 证据融合</span>
        <span>语义索引只负责发现线索，已回 Neo4j 合并真实证据。</span>
        <span class="fusion-count">{{ semanticAddedCount }} 条补充证据</span>
      </div>

      <div v-if="evidence.multi_hop_summary?.dependency_paths?.length" class="learn-path">
        <div class="path-title">学习路线</div>
        <div class="path-intro">
          要理解「{{ displayNodeLabel(evidence.resolved_uid || '') }}」，建议按以下依赖关系回顾。
        </div>
        <div class="path-steps">
          <div
            v-for="(dp, idx) in evidence.multi_hop_summary.dependency_paths.slice(0, 3)"
            :key="idx"
            class="path-step"
            :class="{ deep: dp.depth >= 2 }"
          >
            <span class="step-num">{{ idx + 1 }}</span>
            <span class="step-labels">
              <template v-for="(nodeId, nIdx) in dp.path_nodes" :key="`${idx}-${nodeId}-${nIdx}`">
                <span v-if="nIdx > 0" class="step-arrow">→</span>
                <span class="step-node" :class="{ target: nIdx === dp.path_nodes.length - 1 }">
                  {{ displayNodeLabel(nodeId) }}
                </span>
              </template>
            </span>
          </div>
        </div>
      </div>

      <div v-if="evidence.multi_hop_summary?.reasoning_chain?.length" class="reasoning">
        <div
          v-for="(reason, idx) in evidence.multi_hop_summary.reasoning_chain.slice(0, 2)"
          :key="idx"
          class="reasoning-item"
        >
          {{ localizeText(reason) }}
        </div>
      </div>

      <div class="resource-cards">
        <div v-if="evidence.document_chunks?.length" class="res-card">
          <span class="res-num">{{ evidence.document_chunks.length }}</span>
          <span class="res-label">文档证据</span>
          <span v-if="semanticCountByType.DocumentChunk" class="res-semantic">
            +{{ semanticCountByType.DocumentChunk }} 语义
          </span>
        </div>
        <div v-if="evidence.code_cases?.length" class="res-card">
          <span class="res-num">{{ evidence.code_cases.length }}</span>
          <span class="res-label">代码案例</span>
          <span v-if="semanticCountByType.CodeCase" class="res-semantic">
            +{{ semanticCountByType.CodeCase }} 语义
          </span>
        </div>
        <div v-if="evidence.exercises?.length" class="res-card">
          <span class="res-num">{{ evidence.exercises.length }}</span>
          <span class="res-label">练习题</span>
          <span v-if="semanticCountByType.Exercise" class="res-semantic">
            +{{ semanticCountByType.Exercise }} 语义
          </span>
        </div>
        <div v-if="evidence.misconceptions?.length" class="res-card">
          <span class="res-num">{{ evidence.misconceptions.length }}</span>
          <span class="res-label">常见误区</span>
          <span v-if="semanticCountByType.Misconception" class="res-semantic">
            +{{ semanticCountByType.Misconception }} 语义
          </span>
        </div>
      </div>

      <div v-if="evidence.recommended_next_actions?.length" class="next-actions">
        <div class="section-label">建议下一步</div>
        <div v-for="(action, idx) in evidence.recommended_next_actions.slice(0, 4)" :key="idx" class="action-item">
          {{ idx + 1 }}. {{ localizeText(action) }}
        </div>
      </div>

      <el-collapse v-if="hasExpandableEvidence">
        <el-collapse-item v-if="semanticHits.length" :title="`语义检索命中（${semanticHits.length} 条）`" name="semantic">
          <div v-for="hit in semanticHits.slice(0, 8)" :key="hit.view.id" class="semantic-hit">
            <div class="hit-main">
              <strong>{{ displaySourceLabel(hit.view.title || hit.view.target_uid, '语义证据') }}</strong>
              <el-tag size="small" effect="plain">{{ targetTypeLabel(hit.view.target_type) }}</el-tag>
              <el-tag size="small" type="success" effect="plain">{{ viewTypeLabel(hit.view.view_type) }}</el-tag>
            </div>
            <p>{{ localizeText(hit.view.text.slice(0, 180)) }}</p>
            <div class="hit-meta">
              <span>综合 {{ formatScore(hit.score) }}</span>
              <span>语义 {{ formatScore(hit.semantic_score) }}</span>
              <span v-if="hit.graph_bonus">图谱 +{{ formatScore(hit.graph_bonus) }}</span>
              <span v-if="hit.profile_bonus">画像 +{{ formatScore(hit.profile_bonus) }}</span>
            </div>
            <div v-if="hit.rank_reason?.length" class="hit-reasons">
              {{ hit.rank_reason.map(localizeText).join('；') }}
            </div>
          </div>
        </el-collapse-item>

        <el-collapse-item v-if="evidence.document_chunks?.length" :title="`文档证据（${evidence.document_chunks.length} 篇）`" name="docs">
          <div v-for="chunk in evidence.document_chunks.slice(0, 6)" :key="chunk.uid" class="chunk-item">
            <div class="item-title">
              <strong>{{ displaySourceLabel(chunk.properties?.title || chunk.uid, '文档证据') }}</strong>
              <SemanticTag :match="chunk.properties?._semantic_match" />
            </div>
            <p>{{ localizeText((chunk.properties?.content || '').slice(0, 220)) }}</p>
          </div>
        </el-collapse-item>

        <el-collapse-item v-if="evidence.misconceptions?.length" :title="`常见误区（${evidence.misconceptions.length} 条）`" name="faq">
          <div v-for="mc in evidence.misconceptions.slice(0, 8)" :key="mc.uid" class="chunk-item">
            <div class="item-title">
              <strong>{{ localizeText(mc.properties?.question || mc.properties?.title || '') }}</strong>
              <SemanticTag :match="mc.properties?._semantic_match" />
            </div>
            <p class="mc-wrong">误区：{{ localizeText(mc.properties?.misconception || '') }}</p>
            <p class="mc-right">正确理解：{{ localizeText(mc.properties?.answer || mc.properties?.content || '') }}</p>
          </div>
        </el-collapse-item>

        <el-collapse-item v-if="evidence.code_cases?.length" :title="`代码案例（${evidence.code_cases.length} 个）`" name="code">
          <div v-for="code in evidence.code_cases.slice(0, 5)" :key="code.uid" class="chunk-item">
            <div class="item-title">
              <strong>{{ displaySourceLabel(code.properties?.title || code.uid, '代码案例') }}</strong>
              <SemanticTag :match="code.properties?._semantic_match" />
            </div>
            <p>{{ localizeText(code.properties?.description || code.properties?.summary || '') }}</p>
          </div>
        </el-collapse-item>

        <el-collapse-item v-if="evidence.exercises?.length" :title="`练习题（${evidence.exercises.length} 道）`" name="exercises">
          <div v-for="exercise in evidence.exercises.slice(0, 5)" :key="exercise.uid" class="chunk-item">
            <div class="item-title">
              <strong>{{ displaySourceLabel(exercise.properties?.title || exercise.uid, '练习题') }}</strong>
              <SemanticTag :match="exercise.properties?._semantic_match" />
            </div>
            <p>{{ localizeText(exercise.properties?.question || exercise.properties?.stem || '') }}</p>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, type PropType } from 'vue'
import type { EvidencePackage } from '@/types/graphrag'
import { displayNodeLabel, displaySourceLabel, localizeText } from '@/utils/format'

interface SemanticMatch {
  view_id?: string
  view_type?: string
  score?: number
  semantic_score?: number
  graph_bonus?: number
  profile_bonus?: number
  rank_reason?: string[]
}

const props = defineProps<{
  evidence: EvidencePackage | null
}>()

const semanticHits = computed(() => props.evidence?.semantic_hits || [])
const mergeReport = computed(() => props.evidence?.student_profile_adaptation?.semantic_canonical_merge || null)
const resolutionNotice = computed(() => {
  const evidence = props.evidence
  if (!evidence) return ''
  if (evidence.resolution_quality === 'fallback') {
    const label = displayNodeLabel(evidence.resolved_uid || '', '相关知识点')
    return `未精确匹配你的问题，系统暂按「${label}」组织证据。`
  }
  if (evidence.resolution_quality === 'none') {
    return '系统暂未定位到明确知识点，请尝试补充更具体的问题或选择候选知识点。'
  }
  return ''
})

const semanticAddedCount = computed(() => {
  const added = mergeReport.value?.added || {}
  return Object.values(added).reduce((sum: number, value) => sum + Number(value || 0), 0)
})

const semanticCountByType = computed(() => {
  const added = mergeReport.value?.added || {}
  return {
    DocumentChunk: Number(added.DocumentChunk || 0),
    Exercise: Number(added.Exercise || 0),
    CodeCase: Number(added.CodeCase || 0),
    Misconception: Number(added.Misconception || 0)
  }
})

const hasExpandableEvidence = computed(() => {
  const evidence = props.evidence
  return Boolean(
    semanticHits.value.length ||
    evidence?.document_chunks?.length ||
    evidence?.misconceptions?.length ||
    evidence?.code_cases?.length ||
    evidence?.exercises?.length
  )
})

function formatScore(value?: number) {
  return Number(value || 0).toFixed(2)
}

function targetTypeLabel(type?: string) {
  const labels: Record<string, string> = {
    KnowledgePoint: '知识点',
    DocumentChunk: '文档',
    Misconception: '误区',
    Exercise: '练习',
    CodeCase: '代码'
  }
  return labels[type || ''] || displaySourceLabel(type, '证据')
}

function viewTypeLabel(type?: string) {
  const labels: Record<string, string> = {
    student_confusion: '学生困惑',
    concept_explanation: '概念讲解',
    error_diagnosis: '错误诊断',
    code_intent: '代码实践',
    learning_action: '学习行动',
    raw_summary: '原文摘要'
  }
  return labels[type || ''] || displaySourceLabel(type, '语义视图')
}

const SemanticTag = defineComponent({
  name: 'SemanticTag',
  props: {
    match: {
      type: Object as PropType<SemanticMatch | undefined>,
      default: undefined
    }
  },
  setup(tagProps) {
    return () => {
      if (!tagProps.match) return null
      const score = formatScore(tagProps.match.score)
      return h(
        'span',
        { class: 'semantic-tag', title: `由语义检索补充，综合分 ${score}` },
        `语义补充 ${score}`
      )
    }
  }
})
</script>

<style scoped>
.evidence-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.concept-summary {
  font-size: 13px;
  line-height: 1.7;
  color: #475569;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  border-left: 3px solid #2563eb;
}

.fusion-banner {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  background: #f0fdf4;
  color: #166534;
  font-size: 12px;
}

.fusion-title {
  font-weight: 700;
}

.fusion-count {
  color: #15803d;
  font-weight: 700;
}

.learn-path {
  background: #eef2ff;
  border-radius: 8px;
  padding: 14px;
  border: 1px solid #c7d2fe;
}

.path-title {
  font-size: 14px;
  font-weight: 600;
  color: #3730a3;
  margin-bottom: 4px;
}

.path-intro {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 10px;
}

.path-steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.path-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.step-num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #4f46e5;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-labels {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.step-arrow {
  color: #6366f1;
  font-size: 12px;
}

.step-node {
  padding: 2px 8px;
  background: #fff;
  border-radius: 8px;
  color: #374151;
  font-size: 12px;
}

.step-node.target {
  background: #4f46e5;
  color: #fff;
  font-weight: 600;
}

.path-step.deep {
  opacity: 0.88;
}

.reasoning {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.reasoning-item {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
  padding: 6px 10px;
  background: #fffbeb;
  border-radius: 6px;
  border-left: 2px solid #f59e0b;
}

.resource-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.res-card {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-areas:
    "num label"
    "num semantic";
  column-gap: 8px;
  align-items: center;
  min-height: 56px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8fafc;
  color: #1e293b;
  border: 1px solid #e2e8f0;
}

.res-num {
  grid-area: num;
  font-size: 22px;
  line-height: 1;
  font-weight: 700;
  color: #2563eb;
}

.res-label {
  grid-area: label;
  font-size: 12px;
  font-weight: 600;
}

.res-semantic {
  grid-area: semantic;
  font-size: 11px;
  color: #15803d;
}

.next-actions {
  padding: 10px 12px;
  background: #f0fdf4;
  border-radius: 8px;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: #166534;
  margin-bottom: 6px;
}

.action-item {
  font-size: 13px;
  color: #166534;
  padding: 3px 0;
  line-height: 1.5;
}

.semantic-hit,
.chunk-item {
  padding: 10px 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 13px;
}

.semantic-hit:last-child,
.chunk-item:last-child {
  border-bottom: 0;
}

.hit-main,
.item-title {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}

.semantic-hit p,
.chunk-item p {
  margin: 6px 0 0;
  color: #64748b;
  line-height: 1.6;
}

.hit-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
  color: #475569;
  font-size: 12px;
}

.hit-reasons {
  margin-top: 4px;
  color: #15803d;
  font-size: 12px;
}

.semantic-tag {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 6px;
  border-radius: 6px;
  background: #dcfce7;
  color: #166534;
  font-size: 11px;
  font-weight: 600;
}

.mc-wrong {
  color: #dc2626 !important;
}

.mc-right {
  color: #16a34a !important;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}
</style>
