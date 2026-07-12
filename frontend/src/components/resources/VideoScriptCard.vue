<template>
  <el-card class="section-card">
    <template #header>
      <div class="panel-title">
        <span>{{ script?.title || '视频脚本' }}</span>
        <el-tag>{{ script?.target_duration_seconds || 0 }} 秒</el-tag>
      </div>
    </template>
    <el-empty v-if="!script" description="暂无视频脚本" />
    <el-timeline v-else>
      <el-timeline-item v-for="scene in script.scenes" :key="scene.scene_no" :timestamp="`镜头 ${scene.scene_no}`">
        <strong>{{ scene.title }}</strong>
        <p><b>画面：</b>{{ scene.visual }}</p>
        <p><b>旁白：</b>{{ scene.narration }}</p>
        <p class="muted">{{ scene.animation_hint }}</p>
      </el-timeline-item>
    </el-timeline>
  </el-card>
</template>

<script setup lang="ts">
import type { GeneratedVideoScript } from '@/types/resources'

defineProps<{
  script: GeneratedVideoScript | null
}>()
</script>

<style scoped>
p {
  margin: 6px 0;
  line-height: 1.6;
}
</style>
