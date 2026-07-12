<template>
  <div class="bubble-row" :class="role">
    <div class="bubble">
      <div class="bubble-role">{{ role === 'user' ? '学生' : '系统' }}</div>
      <div class="bubble-content">{{ content }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  role: 'user' | 'assistant'
  content: string
}>()
</script>

<style scoped>
.bubble-row {
  display: flex;
  margin: 12px 0;
}

.bubble-row.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 72%;
  padding: 12px 14px;
  border-radius: 8px;
  background: #ecf5ff;
  line-height: 1.65;
}

.bubble-row.user .bubble {
  background: #f4f4f5;
}

.bubble-role {
  margin-bottom: 4px;
  color: #7a8494;
  font-size: 12px;
}

.bubble-content {
  white-space: pre-wrap;
}
</style>
