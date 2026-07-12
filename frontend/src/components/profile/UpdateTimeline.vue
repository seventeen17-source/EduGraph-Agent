<template>
  <el-timeline>
    <el-timeline-item
      v-for="item in items"
      :key="`${item.timestamp}-${item.trigger_detail}`"
      :timestamp="relativeTime(item.timestamp)"
      placement="top"
    >
      <div class="timeline-body">
        <strong>{{ profileSummaryLabel(item.summary) }}</strong>
        <div class="tag-row timeline-tags">
          <el-tag size="small" type="primary">{{ profileTriggerLabel(item.trigger) }}</el-tag>
          <el-tag v-for="field in item.updated_fields" :key="field" size="small" effect="plain">
            {{ profileFieldLabel(field) }}
          </el-tag>
        </div>
      </div>
    </el-timeline-item>
  </el-timeline>
</template>

<script setup lang="ts">
import type { ProfileUpdateRecord } from '@/types/profile'
import { profileFieldLabel, profileSummaryLabel, profileTriggerLabel, relativeTime } from '@/utils/format'

defineProps<{
  items: ProfileUpdateRecord[]
}>()
</script>

<style scoped>
.timeline-body {
  line-height: 1.5;
}

.timeline-tags {
  margin-top: 8px;
}
</style>
