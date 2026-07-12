<template>
  <div class="completeness">
    <div class="completeness-header">
      <span>{{ label }}</span>
      <strong>{{ percent(value) }}%</strong>
    </div>
    <el-progress :percentage="percent(value)" :stroke-width="10" :show-text="false" />
  </div>
</template>

<script setup lang="ts">
import { percent } from '@/utils/format'

defineProps<{
  value: number
  label?: string
}>()
</script>

<style scoped>
.completeness-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
}
</style>
