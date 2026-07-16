<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>对话式学生画像构建</h1>
        <div class="muted">通过自然语言初始化画像，并实时观察 8 维画像变化。</div>
      </div>
      <div class="title-actions">
        <el-button v-if="authStore.isDemoUser" type="primary" :loading="profileStore.loading" @click="useDemo">使用演示学生</el-button>
        <el-button @click="$router.push('/profile/panel')">已完成</el-button>
      </div>
    </div>

    <ErrorAlert :message="profileStore.error" :retry="useDemo" />

    <div class="chat-layout">
      <el-card class="section-card chat-card">
        <div ref="messageListRef" class="messages">
          <ChatBubble v-for="message in messages" :key="message.id" :role="message.role" :content="message.content" />
        </div>

        <div class="chat-input">
          <div v-if="dimensionHints" class="dimension-hint">
            💡 {{ dimensionHints }}
          </div>
          <el-input
            v-model="draft"
            type="textarea"
            :rows="3"
            resize="none"
            placeholder="补充你的学习背景、目标、偏好或薄弱知识点"
            @keydown.ctrl.enter="send"
          />
          <el-button type="primary" :loading="profileStore.loading" @click="send">发送</el-button>
        </div>
      </el-card>

      <el-card class="section-card side-panel">
        <template #header>
          <div class="panel-title">
            <span>实时画像</span>
            <el-tag :type="profileStore.sessionStatus === 'completed' ? 'success' : 'warning'">
              {{ sessionStatusLabel(profileStore.sessionStatus) }}
            </el-tag>
          </div>
        </template>
        <CompletenessBar :value="profileStore.completeness" label="画像完整度" />
        <div class="dimension-list">
          <ProfileCard
            v-for="card in cards"
            :key="card.key"
            :title="card.title"
            :icon="card.icon"
            :summary="card.summary"
            :tags="card.tags"
            :confidence="card.confidence"
            :source="card.source"
            :last-updated="card.lastUpdated"
            :updated="profileStore.updatedDimensions.includes(card.key)"
          />
        </div>
        <div class="round-info">当前轮次 {{ Math.max(profileStore.currentRound, 1) }}/6</div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'

import ChatBubble from '@/components/common/ChatBubble.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import CompletenessBar from '@/components/profile/CompletenessBar.vue'
import ProfileCard from '@/components/profile/ProfileCard.vue'
import { useAuthStore } from '@/stores/auth'
import { useProfileStore } from '@/stores/profile'
import { levelLabel, resourceLabel, sessionStatusLabel } from '@/utils/format'

const authStore = useAuthStore()
const profileStore = useProfileStore()
const draft = ref('')
const messageListRef = ref<HTMLElement | null>(null)
type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

const openingMessage: ChatMessage = {
    id: 'opening-message',
    role: 'assistant' as const,
    content: '你好，我会先了解你的背景、目标、偏好和薄弱点，然后为你生成个性化学习路径。'
}

const messages = computed<ChatMessage[]>(() => {
  if (!profileStore.chatMessages.length) return [openingMessage]
  return profileStore.chatMessages.map((message) => ({
    id: message.id || `${message.round_no}-${message.role}-${message.created_at}`,
    role: message.role === 'user' ? 'user' : 'assistant',
    content: message.content
  }))
})

const demoMessage =
  '我是计算机专业大二的，学过 Python 和高数，想学机器学习来完成课程项目。我对梯度下降和神经网络训练不太理解，平时比较喜欢看代码和图解。'

const cards = computed(() => {
  const p = profileStore.profile
  if (!p) {
    return [
      { key: 'background', title: '专业背景', icon: 'User', summary: '待采集', tags: [], confidence: 0, source: '', lastUpdated: null },
      { key: 'learning_goal', title: '学习目标', icon: 'Target', summary: '待采集', tags: [], confidence: 0, source: '', lastUpdated: null },
      { key: 'knowledge_base', title: '知识基础', icon: 'BookOpen', summary: '待采集', tags: [], confidence: 0, source: '', lastUpdated: null },
      { key: 'weak_points', title: '薄弱点', icon: 'AlertTriangle', summary: '待采集', tags: [], confidence: 0, source: '', lastUpdated: null }
    ]
  }
  return [
    {
      key: 'background',
      title: '专业背景',
      icon: 'User',
      summary: `${p.background.major || '未填写'} · 大${p.background.grade || '?'}`,
      tags: p.background.course_foundation,
      confidence: p.background.confidence,
      source: p.background.source,
      lastUpdated: p.background.last_updated
    },
    {
      key: 'learning_goal',
      title: '学习目标',
      icon: 'Target',
      summary: p.learning_goal.description || '未填写学习目标',
      tags: p.learning_goal.goal_type,
      confidence: p.learning_goal.confidence,
      source: p.learning_goal.source,
      lastUpdated: p.learning_goal.last_updated
    },
    {
      key: 'knowledge_base',
      title: '知识基础',
      icon: 'BookOpen',
      summary: `${p.knowledge_base.known_topics.length} 个已知主题，${Object.keys(p.node_mastery).length} 个知识点掌握度`,
      tags: p.knowledge_base.known_topics.map((item) => item.topic),
      confidence: p.knowledge_base.confidence,
      source: p.knowledge_base.source,
      lastUpdated: p.knowledge_base.last_updated
    },
    {
      key: 'weak_points',
      title: '薄弱点',
      icon: 'AlertTriangle',
      summary: `${p.weak_points.self_reported.length + p.weak_points.diagnosed.length} 个薄弱点`,
      tags: p.weak_points.self_reported.map((item) => item.topic),
      confidence: p.weak_points.confidence,
      source: p.weak_points.source,
      lastUpdated: p.weak_points.last_updated
    },
    {
      key: 'preferences',
      title: '资源偏好',
      icon: 'SlidersHorizontal',
      summary: p.preferences.resource_ranking.map(resourceLabel).join(' > ') || '未填写偏好',
      tags: p.preferences.resource_ranking.map(resourceLabel),
      confidence: p.preferences.confidence,
      source: p.preferences.source,
      lastUpdated: p.preferences.last_updated
    },
    {
      key: 'ability_state',
      title: '能力状态',
      icon: 'TrendCharts',
      summary: `编程 ${levelLabel(p.ability_state.programming)} · 数学 ${levelLabel(p.ability_state.mathematics)}`,
      tags: [p.ability_state.programming, p.ability_state.mathematics, p.ability_state.application].map(levelLabel),
      confidence: p.ability_state.confidence,
      source: p.ability_state.source,
      lastUpdated: p.ability_state.last_updated
    }
  ]
})

async function scrollBottom() {
  await nextTick()
  if (messageListRef.value) messageListRef.value.scrollTop = messageListRef.value.scrollHeight
}

async function useDemo() {
  await profileStore.initByMessage(demoMessage)
  await scrollBottom()
}

async function send() {
  if (!draft.value.trim()) return
  const content = draft.value.trim()
  draft.value = ''
  if (profileStore.profile) {
    await profileStore.sendMessage(content)
  } else {
    await profileStore.initByMessage(content)
  }
  await scrollBottom()
}

// 缺失维度引导提示
const dimensionHints = computed(() => {
  const missing = profileStore.missingDimensions || []
  if (!missing.length) return ''
  const hints: Record<string, string> = {
    background: '你的专业和年级是什么？',
    learning_goal: '你的学习目标是什么？（如课程项目、考研、兴趣了解）',
    knowledge_base: '你学过哪些编程语言和数学课程？',
    weak_points: '你觉得哪些知识点比较难？',
    preferences: '你喜欢什么类型的学习资源？（图解、代码、视频）',
    ability_state: '你的编程和数学能力怎么样？',
    cognitive_style: '你偏好什么样的学习方式？',
  }
  const next = missing[0]
  return hints[next] || `请补充你的${next}信息`
})

onMounted(async () => {
  await profileStore.initFromAuth()
  if (profileStore.studentId) {
    await profileStore.loadChatHistory().catch(() => {})
  }
  await scrollBottom()
})
</script>

<style scoped>
.title-actions {
  display: flex;
  gap: 10px;
}

.chat-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 16px;
}

.chat-card {
  min-height: 720px;
}

.messages {
  height: 590px;
  overflow: auto;
  padding-right: 8px;
}

.chat-input {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 88px;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid #ebeef5;
}

.dimension-hint {
  grid-column: 1 / -1;
  padding: 8px 12px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-size: 13px;
  color: #1e40af;
  margin-bottom: 4px;
}

.side-panel {
  max-height: 720px;
  overflow: auto;
}

.dimension-list {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.round-info {
  margin-top: 14px;
  color: #909399;
  text-align: center;
}
</style>
