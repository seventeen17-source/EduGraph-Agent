<template>
  <el-card class="profile-card" :class="{ updated }" :style="{ '--card-color': cardColor }" shadow="hover">
    <template #header>
      <div class="card-header">
        <div class="card-header-left">
          <div class="card-icon-wrapper" :style="{ background: cardColor + '15' }">
            <el-icon :style="{ color: cardColor }"><component :is="iconComponent" /></el-icon>
          </div>
          <strong>{{ title }}</strong>
        </div>
        <el-tag :type="sourceTagType(source)" size="small">{{ sourceLabel(source) }}</el-tag>
      </div>
    </template>

    <div class="summary">{{ localizeText(summary) || '暂无信息' }}</div>
    <div v-if="tags?.length" class="tag-row card-tags">
      <el-tag v-for="tag in tags.slice(0, 6)" :key="tag" size="small" effect="plain">{{ localizeText(tag) }}</el-tag>
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

import { localizeText, relativeTime, sourceLabel, sourceTagType } from '@/utils/format'

const props = defineProps<{
  title: string
  icon?: string
  summary: string
  tags?: string[]
  confidence?: number
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

const colorMap: Record<string, string> = {
  User: '#6366f1',
  Target: '#10b981',
  BookOpen: '#8b5cf6',
  Clock: '#f59e0b',
  TrendCharts: '#ec4899',
  AlertTriangle: '#ef4444',
  SlidersHorizontal: '#14b8a6',
  MagicStick: '#3b82f6'
}

const iconComponent = computed(() => iconMap[props.icon || ''] || Collection)
const cardColor = computed(() => colorMap[props.icon || ''] || '#6366f1')
</script>

<style scoped>
.profile-card {
  border-radius: 12px;
  min-height: 200px;
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.8);
  animation: cardIn 0.4s ease-out;
}

.profile-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12), 0 2px 6px rgba(0, 0, 0, 0.06);
}

.profile-card.updated {
  animation: pulse-border 1.4s ease;
}

@keyframes cardIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card-header,
.card-header > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-icon-wrapper {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.summary {
  min-height: 48px;
  color: #334155;
  line-height: 1.6;
  font-size: 14px;
}

.card-tags {
  margin: 12px 0;
}

.updated-time {
  margin-top: 10px;
  color: #94a3b8;
  font-size: 12px;
}

@keyframes pulse-border {
  0% {
    border-color: var(--card-color);
    box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.28);
  }
  100% {
    box-shadow: 0 0 0 12px rgba(99, 102, 241, 0);
  }
}
</style>
