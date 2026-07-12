<template>
  <el-card class="profile-card" :class="{ updated }" shadow="hover">
    <template #header>
      <div class="card-header">
        <div>
          <el-icon><component :is="iconComponent" /></el-icon>
          <strong>{{ title }}</strong>
        </div>
        <el-tag :type="sourceTagType(source)" size="small">{{ sourceLabel(source) }}</el-tag>
      </div>
    </template>

    <div class="summary">{{ localizeText(summary) || '暂无信息' }}</div>
    <div v-if="tags?.length" class="tag-row card-tags">
      <el-tag v-for="tag in tags.slice(0, 6)" :key="tag" size="small" effect="plain">{{ localizeText(tag) }}</el-tag>
    </div>
    <div class="confidence-row">
      <span>置信度</span>
      <el-progress :percentage="percent(confidence)" :stroke-width="7" />
    </div>
    <div class="updated-time">{{ relativeTime(lastUpdated) }}</div>
  </el-card>
</template>

<script setup lang="ts">
import {
  Bell,
  Collection,
  Clock,
  MagicStick,
  Operation,
  Aim,
  TrendCharts,
  User
} from '@element-plus/icons-vue'
import { computed } from 'vue'

import { localizeText, percent, relativeTime, sourceLabel, sourceTagType } from '@/utils/format'

const props = defineProps<{
  title: string
  icon?: string
  summary: string
  tags?: string[]
  confidence: number
  source?: string
  lastUpdated?: string | null
  updated?: boolean
}>()

const iconMap: Record<string, any> = {
  User,
  Target: Aim,
  BookOpen: Collection,
  Clock,
  TrendCharts,
  AlertTriangle: Bell,
  SlidersHorizontal: Operation,
  MagicStick
}

const iconComponent = computed(() => iconMap[props.icon || ''] || Collection)
</script>

<style scoped>
.profile-card {
  border-radius: 8px;
  min-height: 196px;
}

.profile-card.updated {
  animation: pulse-border 1.4s ease;
}

.card-header,
.card-header > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.summary {
  min-height: 44px;
  color: #303133;
  line-height: 1.55;
}

.card-tags {
  margin: 12px 0;
}

.confidence-row {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  color: #7a8494;
  font-size: 13px;
}

.updated-time {
  margin-top: 10px;
  color: #909399;
  font-size: 12px;
}

@keyframes pulse-border {
  0% {
    border-color: #409eff;
    box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.28);
  }
  100% {
    box-shadow: 0 0 0 12px rgba(64, 158, 255, 0);
  }
}
</style>
