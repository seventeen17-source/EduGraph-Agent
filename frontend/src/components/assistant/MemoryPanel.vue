<template>
  <el-card v-if="memories.length > 0" class="section-card memory-panel" shadow="never">
    <template #header>
      <div class="card-header">
        <el-icon><Clock /></el-icon>
        <span>历史记忆</span>
        <el-tag size="small" type="info" effect="plain">语义检索</el-tag>
      </div>
    </template>

    <div class="memory-list">
      <div
        v-for="mem in memories"
        :key="mem.id"
        class="memory-item"
        :class="{ expanded: expandedId === mem.id }"
        @click="expandedId = expandedId === mem.id ? null : mem.id"
      >
        <!-- 摘要行 -->
        <div class="memory-summary">
          <div class="memory-score">
            <el-progress
              type="circle"
              :width="32"
              :percentage="Math.round((mem.score || 0) * 100)"
              :stroke-width="4"
              :color="scoreColor(mem.score || 0)"
            >
              <span class="score-text">{{ Math.round((mem.score || 0) * 100) }}</span>
            </el-progress>
          </div>
          <div class="memory-text">
            <div class="memory-question">{{ mem.student_question_summary || mem.key_insight }}</div>
            <div class="memory-meta">
              <el-tag
                v-for="node in (mem.confusion_nodes || []).slice(0, 2)"
                :key="node"
                size="small"
                type="warning"
                effect="plain"
              >
                {{ uidLabel(node) }}
              </el-tag>
              <span v-if="mem.learning_preference_hint" class="pref-hint">
                {{ mem.learning_preference_hint }}
              </span>
            </div>
          </div>
          <el-icon class="expand-icon" :class="{ rotated: expandedId === mem.id }">
            <ArrowDown />
          </el-icon>
        </div>

        <!-- 展开详情 -->
        <div v-if="expandedId === mem.id" class="memory-detail">
          <div v-if="mem.key_insight" class="detail-row">
            <span class="detail-label">关键发现</span>
            <span>{{ mem.key_insight }}</span>
          </div>
          <div v-if="mem.caution_topics?.length" class="detail-row">
            <span class="detail-label">需注意</span>
            <span>{{ mem.caution_topics.join('、') }}</span>
          </div>
          <div v-if="mem.suggested_follow_up" class="detail-row">
            <span class="detail-label">建议</span>
            <span>{{ mem.suggested_follow_up }}</span>
          </div>
          <div v-if="mem.node_ids?.length" class="detail-row">
            <span class="detail-label">关联知识点</span>
            <el-tag
              v-for="nid in mem.node_ids"
              :key="nid"
              size="small"
              type="primary"
              effect="plain"
            >
              {{ uidLabel(nid) }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ArrowDown, Clock } from '@element-plus/icons-vue'
import { uidLabel } from '@/utils/format'
import type { MemoryEntrySummary } from '@/types/assistant'

defineProps<{
  memories: MemoryEntrySummary[]
}>()

const expandedId = ref<string | null>(null)

function scoreColor(score: number) {
  if (score >= 0.7) return '#10b981'
  if (score >= 0.4) return '#f59e0b'
  return '#94a3b8'
}
</script>

<style scoped>
.memory-panel :deep(.el-card__body) {
  padding: 12px 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.card-header .el-tag {
  margin-left: auto;
}

.memory-list {
  display: flex;
  flex-direction: column;
  max-height: 320px;
  overflow-y: auto;
}

.memory-item {
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.memory-item:hover {
  background: #f8fafc;
}

.memory-item.expanded {
  background: #f0fdf4;
  border-color: #86efac;
}

.memory-summary {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.memory-score {
  flex-shrink: 0;
}

.score-text {
  font-size: 8px;
  font-weight: 700;
}

.memory-text {
  flex: 1;
  min-width: 0;
}

.memory-question {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.memory-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.pref-hint {
  font-size: 11px;
  color: #94a3b8;
  font-style: italic;
}

.expand-icon {
  flex-shrink: 0;
  color: #94a3b8;
  margin-top: 4px;
  transition: transform 0.2s ease;
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

.memory-detail {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  flex-wrap: wrap;
}

.detail-label {
  color: #94a3b8;
  flex-shrink: 0;
  font-weight: 500;
  min-width: 60px;
}

.detail-row span:not(.detail-label) {
  color: #475569;
}
</style>
