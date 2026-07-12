<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>智能辅导</h1>
        <div class="muted">用图谱增强检索证据包回答问题，并显示来源与推荐原因。</div>
      </div>
    </div>

    <div class="tutor-layout">
      <el-card class="section-card">
        <template #header>
          <div class="panel-title">
            <span>提问区</span>
            <el-segmented v-model="mode" :options="['图解说明', '代码示例', '类比解释', '练习推荐']" />
          </div>
        </template>
        <el-input v-model="question" type="textarea" :rows="4" resize="none" placeholder="输入机器学习问题" />
        <div class="actions">
          <el-button type="primary" :loading="learningStore.loadingEvidence" @click="ask">发送问题</el-button>
        </div>
        <el-divider />
        <div v-if="answer" class="answer-box">
          <h3>{{ mode }}</h3>
          <p>{{ answer }}</p>
        </div>
        <el-empty v-else description="发送问题后显示辅导回答" />
      </el-card>

      <EvidencePanel :evidence="learningStore.evidencePackage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import EvidencePanel from '@/components/graphrag/EvidencePanel.vue'
import { useLearningStore } from '@/stores/learning'
import { useProfileStore } from '@/stores/profile'
import { localizeText } from '@/utils/format'

const profileStore = useProfileStore()
const learningStore = useLearningStore()
const question = ref('反向传播和梯度下降到底是什么关系？')
const mode = ref('图解说明')

const answer = computed(() => {
  const evidence = learningStore.evidencePackage
  if (!evidence) return ''
  const summary = evidence.center_node?.properties?.summary || '系统已定位到相关知识点。'
  const reason = localizeText(evidence.ranking_reason?.[0]) || '回答基于图谱证据和学生画像生成。'
  return `${summary}\n\n${mode.value}：先看它在训练流程中的位置。反向传播负责计算每个参数的梯度，优化器再使用这些梯度更新参数。${reason}`
})

async function ask() {
  if (!profileStore.profile) await profileStore.initFromAuth()
  await learningStore.loadEvidence(question.value, profileStore.studentProfileInput, profileStore.studentId)
}
</script>

<style scoped>
.tutor-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 430px;
  gap: 16px;
}

.actions {
  margin-top: 12px;
}

.answer-box {
  padding: 14px;
  border-radius: 8px;
  background: #f5f7fa;
  white-space: pre-wrap;
  line-height: 1.75;
}
</style>
