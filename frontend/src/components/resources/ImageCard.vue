<template>
  <el-card class="section-card image-card">
    <template #header>
      <div class="panel-title">
        <span>{{ image?.title || '教学图片' }}</span>
        <el-tag type="success">讯飞图片生成</el-tag>
      </div>
    </template>

    <el-empty v-if="!image" description="暂无教学图片" />
    <el-alert
      v-else-if="!image.image_url"
      type="warning"
      title="图片资源缺少可访问地址"
      description="本次图片生成未返回有效 URL，请重新生成。"
      show-icon
      :closable="false"
    />
    <div v-else class="image-resource">
      <div class="image-shell">
        <img :src="image.image_url" :alt="image.title || '教学图片'" loading="lazy" />
      </div>
      <div class="image-actions">
        <el-button :icon="Link" plain @click="openImage">打开原图</el-button>
        <el-button :icon="Download" type="primary" plain @click="downloadImage">下载图片</el-button>
      </div>
      <el-collapse>
        <el-collapse-item title="生成提示词" name="prompt">
          <p class="prompt-text">{{ image.prompt || '暂无提示词' }}</p>
          <p v-if="image.negative_prompt" class="negative-text">负面约束：{{ image.negative_prompt }}</p>
        </el-collapse-item>
      </el-collapse>
      <div v-if="image.source_uids?.length" class="tag-row">
        <el-tag v-for="source in image.source_uids" :key="source" effect="plain">
          {{ source }}
        </el-tag>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { Download, Link } from '@element-plus/icons-vue'

import type { GeneratedImage } from '@/types/resources'

const props = defineProps<{
  image: GeneratedImage | null
}>()

function openImage() {
  if (props.image?.image_url) window.open(props.image.image_url, '_blank', 'noopener,noreferrer')
}

function downloadImage() {
  if (!props.image?.image_url) return
  const link = document.createElement('a')
  link.href = props.image.image_url
  link.download = `${props.image.title || '教学图片'}.png`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
</script>

<style scoped>
.image-resource {
  display: grid;
  gap: 14px;
}

.image-shell {
  display: grid;
  place-items: center;
  min-height: 320px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.image-shell img {
  display: block;
  max-width: 100%;
  max-height: 680px;
  object-fit: contain;
}

.image-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.prompt-text,
.negative-text {
  margin: 0;
  line-height: 1.7;
  color: #334155;
  white-space: pre-wrap;
}

.negative-text {
  margin-top: 8px;
  color: #64748b;
}
</style>

