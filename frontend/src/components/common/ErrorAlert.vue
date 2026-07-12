<template>
  <el-alert v-if="message" type="error" show-icon :closable="false" class="error-alert">
    <template #title>{{ message }}</template>
    <el-button v-if="retry" size="small" type="danger" plain @click="retry">重试</el-button>
  </el-alert>
</template>

<script setup lang="ts">
defineProps<{
  message?: string | null
  retry?: () => void
}>()
</script>

<style scoped>
.error-alert {
  margin-bottom: 12px;
}
</style>
