<template>
  <el-card class="section-card">
    <el-skeleton :rows="rows || 6" animated />
  </el-card>
</template>

<script setup lang="ts">
defineProps<{
  rows?: number
}>()
</script>
