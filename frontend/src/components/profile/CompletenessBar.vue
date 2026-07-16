<template>
  <div class="completeness">
    <div class="completeness-header">
      <div class="completeness-left">
        <span class="completeness-icon">📊</span>
        <span class="completeness-label">{{ label }}</span>
      </div>
      <span class="completeness-value" :class="valueClass">{{ animatedValue }}%</span>
    </div>
    <div class="completeness-bar-container">
      <div class="completeness-bar-bg">
        <div
          class="completeness-bar-fill"
          :class="valueClass"
          :style="{ width: animatedValue + '%' }"
        />
      </div>
      <div class="completeness-markers">
        <span class="marker" :style="{ left: '25%' }"></span>
        <span class="marker" :style="{ left: '50%' }"></span>
        <span class="marker" :style="{ left: '75%' }"></span>
      </div>
    </div>
    <div class="completeness-hint" v-if="value < 0.5">
      <span class="hint-icon">💡</span>
      <span class="hint-text">完善画像可获得更精准的个性化学习推荐</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'

const props = defineProps<{
  value: number
  label?: string
}>()

const animatedValue = ref(0)

const valueClass = computed(() => {
  if (props.value >= 0.8) return 'high'
  if (props.value >= 0.5) return 'medium'
  return 'low'
})

function animateValue(target: number) {
  const start = animatedValue.value
  const startTime = performance.now()
  function update(currentTime: number) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / 1000, 1)
    const easeOut = 1 - Math.pow(1 - progress, 3)
    animatedValue.value = Math.round(start + (Math.round(target * 100) - start) * easeOut)
    if (progress < 1) {
      requestAnimationFrame(update)
    }
  }
  requestAnimationFrame(update)
}

onMounted(() => {
  setTimeout(() => {
    animateValue(props.value)
  }, 200)
})

watch(() => props.value, (newVal) => {
  animateValue(newVal)
})
</script>

<style scoped>
.completeness {
  padding: 4px 0;
}

.completeness-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.completeness-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.completeness-icon {
  font-size: 18px;
}

.completeness-label {
  font-size: 14px;
  color: #475569;
  font-weight: 500;
}

.completeness-value {
  font-size: 20px;
  font-weight: 700;
  transition: color 0.3s ease;
}

.completeness-value.high {
  color: #10b981;
}

.completeness-value.medium {
  color: #f59e0b;
}

.completeness-value.low {
  color: #ef4444;
}

.completeness-bar-container {
  position: relative;
  height: 12px;
}

.completeness-bar-bg {
  height: 100%;
  background: #f1f5f9;
  border-radius: 6px;
  overflow: hidden;
}

.completeness-bar-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 1s ease;
}

.completeness-bar-fill.high {
  background: linear-gradient(90deg, #10b981, #34d399, #6ee7b7);
}

.completeness-bar-fill.medium {
  background: linear-gradient(90deg, #f59e0b, #fbbf24, #fcd34d);
}

.completeness-bar-fill.low {
  background: linear-gradient(90deg, #ef4444, #f87171, #fca5a5);
}

.completeness-markers {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.marker {
  position: absolute;
  width: 1px;
  height: 100%;
  background: rgba(148, 163, 184, 0.3);
}

.completeness-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 12px;
  background: rgba(251, 191, 36, 0.1);
  border-radius: 8px;
}

.hint-icon {
  font-size: 14px;
}

.hint-text {
  font-size: 12px;
  color: #92400e;
}
</style>
