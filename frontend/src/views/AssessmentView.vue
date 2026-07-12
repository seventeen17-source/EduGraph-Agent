<template>
  <div class="page">
    <div class="page-title">
      <div>
        <h1>学习效果评估</h1>
        <div class="muted">知识点掌握度雷达、薄弱点分布、掌握度趋势和学习建议</div>
      </div>
      <div class="title-actions">
        <el-button :loading="loading" @click="load">刷新评估</el-button>
        <el-button type="primary" plain @click="exportReport">导出评估报告</el-button>
      </div>
    </div>

    <LoadingSkeleton v-if="loading" :rows="4" />

    <el-empty
      v-if="!loading && mastery.length === 0 && weak.length === 0"
      description="暂无评估数据"
    >
      <template #default>
        <div class="empty-guide">
          <p>要生成评估数据，请先完成以下步骤：</p>
          <p>1. <el-button size="small" text type="primary" @click="$router.push('/profile/chat')">完善学习画像</el-button></p>
          <p>2. <el-button size="small" text type="primary" @click="$router.push('/exercise')">做一次练习测试</el-button></p>
          <p>3. <el-button size="small" text type="primary" @click="$router.push('/assistant')">与学习助手对话</el-button></p>
        </div>
      </template>
    </el-empty>

    <div v-if="!loading && (mastery.length || weak.length)" class="assessment-grid">
      <!-- 掌握度雷达图 -->
      <el-card class="section-card">
        <template #header>
          <div class="panel-title">
            <span>掌握度雷达图</span>
            <el-tag>{{ mastery.length }} 项</el-tag>
            <span class="muted small">蓝色=当前 | 绿色虚线=目标 0.6</span>
          </div>
        </template>
        <div ref="radarRef" class="chart-box" />
      </el-card>

      <!-- 薄弱点饼图 -->
      <el-card class="section-card">
        <template #header>
          <div class="panel-title">
            <span>薄弱点分布</span>
            <el-tag type="warning">{{ weak.length }} 个</el-tag>
          </div>
        </template>
        <div ref="pieRef" class="chart-box" />
      </el-card>

      <!-- 掌握度柱状图 -->
      <el-card class="section-card trend-card">
        <template #header>
          <div class="panel-title">
            <span>掌握度一览</span>
            <el-tag type="primary">{{ mastery.length }} 个知识点</el-tag>
            <span class="muted small">绿>=60% | 黄>=35% | 红<35%</span>
          </div>
        </template>
        <div v-if="!mastery.length" class="trend-empty">
          <el-empty description="暂无掌握度数据" :image-size="80" />
        </div>
        <div ref="barRef" v-else class="chart-box" />
      </el-card>

      <!-- 学习时间线 -->
      <el-card class="section-card timeline-card">
        <template #header>
          <div class="panel-title">
            <span>学习记录时间线</span>
            <el-tag type="info">{{ timeline.length }} 条</el-tag>
          </div>
        </template>
        <div v-if="!timeline.length" class="trend-empty">
          <el-empty description="暂无学习记录" :image-size="60" />
        </div>
        <div v-else class="timeline-list">
          <div v-for="(evt, i) in timeline.slice(0, 15)" :key="i" class="timeline-item">
            <div class="tl-dot" :class="evt.trigger"></div>
            <div class="tl-content">
              <span class="tl-summary">{{ evt.summary }}</span>
              <span class="tl-time muted small">{{ formatDate(evt.timestamp) }}</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 建议 -->
      <el-card class="section-card advice-card">
        <template #header>
          <div class="panel-title">
            <span>个性化学习建议</span>
            <el-tag type="success">数据驱动</el-tag>
          </div>
        </template>
        <div class="advice-content">
          <div class="advice-section">
            <div class="advice-title">📋 优先学习</div>
            <ul>
              <li v-for="item in weak.slice(0, 5)" :key="item.label">
                <strong>{{ item.label }}</strong>
                <span class="muted">（薄弱度 {{ Math.round((item.score || 0) * 100) }}%）</span>
              </li>
            </ul>
          </div>
          <div class="advice-section">
            <div class="advice-title">📈 进步最快</div>
            <ul>
              <li v-for="uid in improvingNodes.slice(0, 3)" :key="uid">
                <strong>{{ uidLabelMap[uid] || uid }}</strong>
                <span class="muted"> 持续提升中</span>
              </li>
              <li v-if="!improvingNodes.length" class="muted">继续学习，积累更多数据后这里会显示进步最快的知识点</li>
            </ul>
          </div>
        </div>
        <el-divider />
        <el-button type="primary" @click="$router.push('/learning-path')">查看个性化学习路径</el-button>
        <el-button plain @click="$router.push('/profile/panel')">查看完整画像</el-button>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'

import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import { useProfileStore } from '@/stores/profile'
import { uidLabel } from '@/utils/format'

const profileStore = useProfileStore()
const loading = ref(false)
const radarRef = ref<HTMLDivElement | null>(null)
const pieRef = ref<HTMLDivElement | null>(null)
const barRef = ref<HTMLDivElement | null>(null)
let radar: echarts.ECharts | null = null
let pie: echarts.ECharts | null = null
let bar: echarts.ECharts | null = null

const mastery = computed(() => profileStore.dashboard?.mastery_overview || [])
const weak = computed(() => profileStore.dashboard?.weak_point_rank || [])
const timeline = computed(() => profileStore.dashboard?.recent_updates || [])
const trendDays = computed(() => {
  if (timeline.value.length < 2) return 0
  const first = new Date(timeline.value[timeline.value.length - 1].timestamp).getTime()
  const last = new Date(timeline.value[0].timestamp).getTime()
  return Math.max(1, Math.round((last - first) / (1000 * 60 * 60 * 24)))
})

const improvingNodes = computed(() => {
  const items = timeline.value || []
  if (items.length < 2) return []
  const exerciseItems = items.filter(t => t.trigger === 'exercise_result')
  return [...new Set(exerciseItems.flatMap(t => t.updated_fields || []).slice(0, 3))]
})

const uidLabelMap = computed(() => {
  const map: Record<string, string> = {}
  for (const item of mastery.value) {
    map[item.node_id] = item.node_name || uidLabel(item.node_id)
  }
  return map
})

async function load() {
  loading.value = true
  try {
    if (!profileStore.profile) await profileStore.initFromAuth()
    await profileStore.refreshDashboard()
    await nextTick()
    renderCharts()
  } finally { loading.value = false }
}

function renderCharts() {
  // 雷达图：当前 + 目标
  if (radarRef.value) {
    radar ||= echarts.init(radarRef.value)
    const items = mastery.value.length
      ? mastery.value.slice(0, 8)
      : [{ node_id: 'ml_basic', node_name: '示例', mastery_score: 0.4 }]
    const current = items.map((i: any) => i.mastery_score || 0)
    const target = items.map(() => 0.6)
    radar.setOption({
      tooltip: {},
      legend: { data: ['当前掌握度', '目标掌握度'], bottom: 0 },
      radar: {
        indicator: items.map((i: any) => ({
          name: i.node_name || uidLabel(i.node_id) || '知识点',
          max: 1
        }))
      },
      series: [
        {
          type: 'radar', name: '当前掌握度',
          data: [{ value: current, name: '当前' }],
          areaStyle: { opacity: 0.3 },
          lineStyle: { color: '#3b82f6' },
          itemStyle: { color: '#3b82f6' },
        },
        {
          type: 'radar', name: '目标掌握度',
          data: [{ value: target, name: '目标(0.6)' }],
          lineStyle: { type: 'dashed', color: '#10b981' },
          itemStyle: { color: '#10b981' },
          symbol: 'none',
        },
      ],
    })
  }

  // 饼图
  if (pieRef.value) {
    pie ||= echarts.init(pieRef.value)
    const items = weak.value.length
      ? weak.value.slice(0, 6)
      : [{ label: '示例薄弱点', score: 0.5 }]
    pie.setOption({
      tooltip: { formatter: '{b}: {c}%' },
      series: [{
        type: 'pie',
        radius: ['45%', '75%'],
        center: ['50%', '50%'],
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}\n{c}%' },
        data: items.map((i: any) => ({
          name: i.label, value: Math.round((i.score || 0.5) * 100)
        })),
        emphasis: {
          scale: true,
          label: { fontSize: 16, fontWeight: 'bold' },
        },
      }],
    })
  }

  // 掌握度柱状图
  if (barRef.value) {
    bar ||= echarts.init(barRef.value)
    const items = mastery.value.length
      ? mastery.value.slice(0, 12)
      : [{ node_id: 'ml_basic', node_name: '示例', mastery_score: 0.4 }]
    bar.setOption({
      tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
      grid: { left: 120, right: 30, top: 10, bottom: 10 },
      xAxis: { type: 'value', name: '掌握度(%)', min: 0, max: 100 },
      yAxis: {
        type: 'category',
        data: items.map((i: any) => i.node_name || uidLabel(i.node_id) || '知识点'),
        axisLabel: { fontSize: 12, width: 110, overflow: 'truncate' },
      },
      series: [{
        type: 'bar',
        data: items.map((i: any) => ({
          value: Math.round((i.mastery_score || 0) * 100),
          itemStyle: {
            color: (i.mastery_score || 0) >= 0.6 ? '#10b981' : (i.mastery_score || 0) >= 0.35 ? '#f59e0b' : '#ef4444',
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barMaxWidth: 24,
        label: { show: true, position: 'right', formatter: '{c}%' },
      }],
    })
  }
}

function exportReport() {
  if (!radar) return
  const url = radar.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' })
  const a = document.createElement('a')
  a.href = url; a.download = `edugraph-assessment-${Date.now()}.png`
  a.click()
}

function formatDate(d: string) {
  if (!d) return ''
  const date = new Date(d); date.setHours(date.getHours() + 8)
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) + ' ' +
    date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

onMounted(load)
</script>

<style scoped>
.title-actions { display: flex; gap: 10px; }

.assessment-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-box { height: 380px; }

.trend-card { grid-column: span 2; }
.timeline-card { max-height: 400px; overflow: hidden; }
.advice-card { grid-column: span 2; }

.trend-empty {
  display: flex; justify-content: center; padding: 20px;
}

.timeline-list {
  max-height: 280px; overflow-y: auto;
  display: flex; flex-direction: column; gap: 8px;
}

.timeline-item {
  display: flex; gap: 12px; align-items: flex-start; padding: 8px 12px;
  background: #f8fafc; border-radius: 8px;
}

.tl-dot {
  width: 10px; height: 10px; border-radius: 50%; margin-top: 4px; flex-shrink: 0;
  background: #3b82f6;
}

.tl-dot.exercise_result { background: #10b981; }
.tl-dot.profile_update { background: #8b5cf6; }
.tl-dot.learning_progress { background: #f59e0b; }

.tl-content {
  display: flex; flex-direction: column; gap: 2px;
}

.tl-summary { font-size: 13px; }
.tl-time { font-size: 11px; }

.advice-content {
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
}

.advice-title { font-weight: 600; margin-bottom: 10px; color: #1e293b; }

.advice-section ul { padding-left: 18px; line-height: 2; margin: 0; }

.empty-guide p { margin: 8px 0; }

@media (max-width: 768px) {
  .assessment-grid { grid-template-columns: 1fr; }
  .trend-card, .advice-card { grid-column: span 1; }
}
</style>
