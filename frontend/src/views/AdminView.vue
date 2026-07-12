<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>系统管理</h1>
        <div class="muted">运行状态、反馈分析与演示说明。</div>
      </div>
      <el-button type="primary" :loading="runtimeLoading" @click="checkRuntime">
        运行检查
      </el-button>
    </div>

    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="系统状态" name="system">
        <el-card class="section-card" shadow="never">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="后端地址">http://127.0.0.1:8000</el-descriptions-item>
            <el-descriptions-item label="演示账号">demo@edugraph.local / demo123</el-descriptions-item>
            <el-descriptions-item label="整体状态">
              <el-tag :type="statusTag(runtime?.status)">{{ statusLabel(runtime?.status || 'unchecked') }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="运行环境">{{ runtime?.environment || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-alert
          v-if="runtime?.degraded_features?.length"
          class="runtime-alert"
          type="warning"
          show-icon
          :closable="false"
          title="当前存在降级能力"
          :description="runtime.degraded_features.join('、')"
        />
        <el-alert
          v-if="runtime?.warnings?.length"
          class="runtime-alert"
          type="info"
          show-icon
          :closable="false"
          title="运行提醒"
          :description="runtime.warnings.join('、')"
        />

        <el-empty v-if="!runtime && !runtimeLoading" description="点击运行检查查看系统真实状态" />
        <div v-if="runtime" class="runtime-grid">
          <el-card v-for="component in componentList" :key="component.name" class="runtime-card" shadow="never">
            <div class="runtime-head">
              <strong>{{ componentLabel(component.name) }}</strong>
              <el-tag size="small" :type="statusTag(component.status)">
                {{ statusLabel(component.status) }}
              </el-tag>
            </div>
            <p class="runtime-detail">{{ component.detail }}</p>

            <div v-if="component.name === 'chroma'" class="runtime-meta">
              <div>路径：{{ component.metadata?.persist_dir || '-' }}</div>
              <div>课程语义索引：{{ component.metadata?.collections?.course_semantic?.count ?? 0 }} 条</div>
              <div>学生记忆索引：{{ component.metadata?.collections?.memory?.count ?? 0 }} 条</div>
              <div>期望维度：{{ component.metadata?.expected_embedding_dimension || '-' }}</div>
            </div>
            <div v-else-if="component.name === 'sqlite'" class="runtime-meta">
              <div>业务表：{{ component.metadata?.table_count ?? 0 }} 个</div>
              <div class="table-list">{{ (component.metadata?.tables || []).join('、') }}</div>
            </div>
            <div v-else-if="component.name === 'llm'" class="runtime-meta">
              <div>Provider：{{ component.metadata?.provider || '-' }}</div>
              <div>模型：{{ component.metadata?.model || '-' }}</div>
              <div>解析器：{{ component.metadata?.resolver_enabled ? '已启用' : '未启用' }}</div>
            </div>
            <div v-else-if="component.name === 'embedding'" class="runtime-meta">
              <div>模型：{{ component.metadata?.model || '-' }}</div>
              <div>维度：{{ component.metadata?.dimension || '-' }}</div>
              <div>凭证：{{ component.metadata?.embedding_api_key_configured ? '专用 Key' : '非专用 Key' }}</div>
            </div>
            <div v-else-if="component.name === 'neo4j'" class="runtime-meta">
              <div>地址：{{ component.metadata?.uri || '-' }}</div>
              <div>数据库：{{ component.metadata?.database || '-' }}</div>
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="反馈分析" name="feedback">
        <div v-if="feedbackLoading" class="muted loading-line">
          正在加载反馈数据...
        </div>
        <template v-else-if="feedbackStats">
          <div class="stats-row">
            <div class="stat-card">
              <div class="stat-value">{{ feedbackStats.total }}</div>
              <div class="stat-label">总评价数</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ positiveRate }}%</div>
              <div class="stat-label">好评率</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ Object.keys(feedbackStats.by_intent || {}).length }}</div>
              <div class="stat-label">覆盖意图类型</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ Object.keys(feedbackStats.by_node || {}).length }}</div>
              <div class="stat-label">覆盖知识点</div>
            </div>
          </div>

          <el-card class="section-card" shadow="never">
            <template #header>
              <div class="panel-title">
                <span>按意图统计（近 30 天）</span>
              </div>
            </template>
            <div v-if="Object.keys(feedbackStats.by_intent || {}).length" class="intent-stats">
              <div v-for="(tags, intent) in feedbackStats.by_intent" :key="intent" class="intent-row">
                <div class="intent-name">{{ intentLabel(String(intent)) }}</div>
                <div class="intent-bars">
                  <span
                    v-for="(count, tag) in tags"
                    :key="tag"
                    class="intent-tag-bar"
                    :class="tagCategory(String(tag))"
                  >
                    {{ tagLabel(String(tag)) }} x{{ count }}
                  </span>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无数据" />
          </el-card>

          <el-card class="section-card" shadow="never">
            <template #header>
              <div class="panel-title">
                <span>最近评价</span>
              </div>
            </template>
            <div v-if="feedbackStats.recent?.length" class="recent-list">
              <div v-for="fb in feedbackStats.recent" :key="fb.id" class="recent-item">
                <span class="recent-tags">
                  <el-tag
                    v-for="tag in fb.tags"
                    :key="tag"
                    size="small"
                    :type="tagCategory(tag as string)"
                    effect="plain"
                  >
                    {{ tagLabel(tag as string) }}
                  </el-tag>
                </span>
                <span class="recent-intent">{{ intentLabel(fb.intent) }}</span>
                <span v-if="fb.target_node_id" class="recent-node">{{ fb.target_node_id }}</span>
                <span class="recent-time">{{ formatTime(fb.created_at) }}</span>
              </div>
            </div>
            <el-empty v-else description="暂无评价" />
          </el-card>
        </template>
        <div v-else class="muted loading-line">
          点击加载反馈数据查看分析。
        </div>
        <div class="feedback-actions">
          <el-input v-model="feedbackStudentId" placeholder="学生 ID" class="student-input" size="small" />
          <el-button type="primary" :loading="feedbackLoading" @click="loadFeedbackStats">
            {{ feedbackStats ? '刷新' : '加载反馈数据' }}
          </el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="演示说明" name="demo">
        <el-card class="section-card" shadow="never">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="演示路线">
              1. 画像对话 -> 2. 学习助手提问 -> 3. 知识图谱浏览 -> 4. AI 备课台 -> 5. 练习评估 -> 6. 学习路径 -> 7. 评估报告
            </el-descriptions-item>
            <el-descriptions-item label="种子数据">
              演示账号和种子记忆仅用于快速展示个性化能力；真实联调时应通过运行状态面板确认是否存在降级或空索引。
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { apiClient } from '@/api/client'
import { getRuntimeStatus, type RuntimeStatusResponse } from '@/api/admin'

const activeTab = ref('system')
const runtime = ref<RuntimeStatusResponse | null>(null)
const runtimeLoading = ref(false)
const feedbackStats = ref<any>(null)
const feedbackLoading = ref(false)
const feedbackStudentId = ref('')

async function checkRuntime() {
  runtimeLoading.value = true
  try {
    runtime.value = await getRuntimeStatus()
  } finally {
    runtimeLoading.value = false
  }
}

const componentList = computed(() => Object.values(runtime.value?.components || {}))

async function loadFeedbackStats() {
  feedbackLoading.value = true
  try {
    const response = await apiClient.get(`/api/assistant/feedback/stats/${feedbackStudentId.value}?days=30`)
    feedbackStats.value = response.data
  } catch {
    feedbackStats.value = null
  } finally {
    feedbackLoading.value = false
  }
}

const positiveRate = computed(() => {
  if (!feedbackStats.value?.by_intent) return 0
  let pos = 0
  let neg = 0
  for (const tags of Object.values(feedbackStats.value.by_intent) as any[]) {
    for (const [tag, count] of Object.entries(tags as Record<string, number>)) {
      if (['helpful', 'clear'].includes(tag)) pos += count
      else neg += count
    }
  }
  if (pos + neg === 0) return 0
  return Math.round((pos / (pos + neg)) * 100)
})

function componentLabel(name: string): string {
  const labels: Record<string, string> = {
    neo4j: 'Neo4j 图数据库',
    sqlite: 'SQLite 业务库',
    llm: 'LLM 服务',
    embedding: 'Embedding 服务',
    chroma: 'Chroma 向量库',
  }
  return labels[name] || name
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    ok: '正常',
    warning: '提醒',
    missing: '缺失',
    empty: '为空',
    degraded: '降级',
    error: '异常',
    unchecked: '未检查',
  }
  return labels[status] || status
}

function statusTag(status?: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'ok') return 'success'
  if (status === 'warning' || status === 'empty' || status === 'degraded') return 'warning'
  if (status === 'missing' || status === 'error') return 'danger'
  return 'info'
}

function tagCategory(tag: string): 'success' | 'danger' | 'info' | '' {
  const pos = ['helpful', 'clear']
  const neg = ['dont_get', 'too_hard', 'too_vague', 'incorrect']
  const info = ['want_examples', 'want_summary', 'too_easy']
  if (pos.includes(tag)) return 'success'
  if (neg.includes(tag)) return 'danger'
  if (info.includes(tag)) return 'info'
  return ''
}

function tagLabel(tag: string): string {
  const labels: Record<string, string> = {
    helpful: '有帮助',
    clear: '很清楚',
    dont_get: '没看懂',
    too_hard: '太难',
    too_easy: '太简单',
    too_vague: '不够具体',
    want_examples: '想要例子',
    want_summary: '想要总结',
    incorrect: '内容有误',
  }
  return labels[tag] || tag
}

function intentLabel(intent: string): string {
  const labels: Record<string, string> = {
    concept_explain: '概念讲解',
    resource_generate: 'AI 备课台',
    exercise_help: '练习辅导',
    path_plan: '路径规划',
    assessment_review: '评估回顾',
    general_learning_chat: '通用问答',
    profile_update: '画像更新',
    progress_update: '进度更新',
  }
  return labels[intent] || intent
}

function formatTime(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.runtime-alert {
  margin-top: 12px;
}

.runtime-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.runtime-card {
  border-radius: 8px;
}

.runtime-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.runtime-detail {
  margin: 10px 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}

.runtime-meta {
  display: grid;
  gap: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.table-list {
  max-height: 42px;
  overflow: hidden;
  color: #94a3b8;
}

.loading-line {
  padding: 20px;
  text-align: center;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: #f8fafc;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #4f46e5;
}

.stat-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.intent-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.intent-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.intent-name {
  min-width: 100px;
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  padding-top: 2px;
}

.intent-bars {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.intent-tag-bar {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  background: #f1f5f9;
  color: #64748b;
}

.intent-tag-bar.success { background: #dcfce7; color: #16a34a; }
.intent-tag-bar.danger { background: #fef2f2; color: #dc2626; }
.intent-tag-bar.info { background: #dbeafe; color: #2563eb; }

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 13px;
}

.recent-tags {
  display: flex;
  gap: 4px;
}

.recent-intent {
  color: #64748b;
  font-size: 12px;
}

.recent-node {
  color: #4f46e5;
  font-size: 12px;
  font-family: monospace;
}

.recent-time {
  color: #94a3b8;
  font-size: 11px;
  margin-left: auto;
}

.feedback-actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.student-input {
  width: 220px;
}

@media (max-width: 900px) {
  .runtime-grid,
  .stats-row {
    grid-template-columns: 1fr;
  }

  .recent-item,
  .intent-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
