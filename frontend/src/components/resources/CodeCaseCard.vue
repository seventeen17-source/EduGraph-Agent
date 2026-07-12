<template>
  <el-card class="section-card">
    <template #header>
      <div class="panel-title">
        <span>{{ localizeText(codeCase?.title) || '代码案例' }}</span>
        <el-button text type="primary" :disabled="!codeCase?.code" @click="copy">复制代码</el-button>
      </div>
    </template>
    <el-empty v-if="!codeCase" description="暂无代码案例" />
    <div v-else>
      <p>{{ localizeText(codeCase.explanation) }}</p>
      <pre><code class="hljs" v-html="highlighted" /></pre>
      <el-divider />
      <strong>测试/实验任务</strong>
      <pre class="test-cases">{{ JSON.stringify(codeCase.test_cases, null, 2) }}</pre>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import hljs from 'highlight.js'
import { computed } from 'vue'
import { ElMessage } from 'element-plus'

import type { GeneratedCodeCase } from '@/types/resources'
import { localizeText } from '@/utils/format'

const props = defineProps<{
  codeCase: GeneratedCodeCase | null
}>()

const highlighted = computed(() => hljs.highlight(props.codeCase?.code || '', { language: 'python' }).value)

async function copy() {
  await navigator.clipboard.writeText(props.codeCase?.code || '')
  ElMessage.success('代码已复制')
}
</script>

<style scoped>
p {
  color: #606266;
  line-height: 1.7;
}

pre {
  overflow: auto;
  padding: 14px;
  border-radius: 8px;
  background: #f6f8fa;
}

.test-cases {
  white-space: pre-wrap;
}
</style>
