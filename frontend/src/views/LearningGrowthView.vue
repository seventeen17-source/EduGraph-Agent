<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>📈 学习成长</h1>
        <div class="muted">回顾学习历程，了解自己的节奏，发现下一步方向。</div>
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <LoadingSkeleton :rows="6" />
    </div>

    <ErrorAlert v-else-if="error" :message="error" :retry="load" />

    <LearningTimeline
      v-else-if="data"
      :months="data.months"
      :stats="data.stats"
      :forgetting-soon="data.forgetting_soon"
      @go-to-node="goToNode"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import ErrorAlert from '@/components/common/ErrorAlert.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import LearningTimeline from '@/components/profile/LearningTimeline.vue'
import { getLearningTimeline } from '@/api/profile'
import { useAuthStore } from '@/stores/auth'
import { useProfileStore } from '@/stores/profile'
import type { TimelineResponse } from '@/types/profile'

const router = useRouter()
const authStore = useAuthStore()
const profileStore = useProfileStore()
const data = ref<TimelineResponse | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const sid = authStore.studentId || profileStore.studentId
    if (!sid) { error.value = '未登录'; return }
    if (!profileStore.profile && authStore.studentId) {
      profileStore.studentId = authStore.studentId
      profileStore.displayName = authStore.displayName
      await profileStore.loadCurrentStudent().catch(() => {})
    }
    data.value = await getLearningTimeline(sid)
  } catch (err: any) {
    error.value = err?.message || '加载时间轴失败'
  } finally {
    loading.value = false
  }
}

function goToNode(nodeId: string | null) {
  if (!nodeId) return
  router.push({ path: '/graph', query: { node_id: nodeId } })
}

onMounted(load)
</script>
