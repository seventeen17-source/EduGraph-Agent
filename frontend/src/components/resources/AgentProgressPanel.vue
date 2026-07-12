<template>
  <el-card class="section-card">
    <template #header>
      <div class="panel-title">
        <span>多智能体进度</span>
        <el-tag :type="allDone ? 'success' : 'info'">{{ allDone ? '已完成' : '生成中' }}</el-tag>
      </div>
    </template>
    <div class="agent-grid">
      <div v-for="agent in agents" :key="agent.name" class="agent-card">
        <div class="agent-icon">
          <el-icon><component :is="agent.icon" /></el-icon>
        </div>
        <div>
          <strong>{{ agent.label }}</strong>
          <div class="muted">{{ statusText(statuses[agent.name]) }}</div>
        </div>
        <el-tag :type="statusType(statuses[agent.name])" size="small">
          {{ agentStatusLabel(statuses[agent.name]) }}
        </el-tag>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { Check, Cpu, Document, Files, MagicStick, Search, VideoCamera } from '@element-plus/icons-vue'
import { computed } from 'vue'

import { agentStatusLabel } from '@/utils/format'

const props = defineProps<{
  statuses: Record<string, string>
}>()

const agents = [
  { name: 'RetrievalAgent', label: '证据检索智能体', icon: Search },
  { name: 'DocumentAgent', label: '讲解文档智能体', icon: Document },
  { name: 'MindmapAgent', label: '思维导图智能体', icon: MagicStick },
  { name: 'ExerciseAgent', label: '练习生成智能体', icon: Files },
  { name: 'VideoScriptAgent', label: '视频脚本智能体', icon: VideoCamera },
  { name: 'CodeAgent', label: '代码案例智能体', icon: Cpu }
]

const allDone = computed(() => agents.every((agent) => ['done', 'skipped'].includes(props.statuses[agent.name])))

function statusType(status?: string) {
  if (status === 'done') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'skipped') return 'warning'
  if (status === 'running') return 'primary'
  return 'info'
}

function statusText(status?: string) {
  if (status === 'done') return '结果已生成并完成校验'
  if (status === 'failed') return '生成失败，等待重试'
  if (status === 'skipped') return '本轮未请求该资源'
  if (status === 'running') return '正在检索、生成或校验'
  return '等待任务开始'
}
</script>

<style scoped>
.agent-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.agent-card {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}

.agent-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: #409eff;
  background: #ecf5ff;
}
</style>
