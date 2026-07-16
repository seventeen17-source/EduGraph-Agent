<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <div class="auth-brand">
        <div class="brand-mark">EG</div>
        <h1>EduGraph</h1>
        <p class="muted">个性化学习平台</p>
      </div>

      <el-form @submit.prevent="handleLogin" label-position="top" size="large">
        <el-form-item label="邮箱">
          <el-input
            v-model="email"
            type="email"
            placeholder="请输入邮箱"
            :disabled="authStore.loading"
          />
        </el-form-item>

        <el-form-item label="密码">
          <el-input
            v-model="password"
            type="password"
            placeholder="请输入密码"
            show-password
            :disabled="authStore.loading"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-alert v-if="authStore.error" :title="authStore.error" type="error" show-icon :closable="false" class="auth-error" />

        <el-button type="primary" native-type="submit" :loading="authStore.loading" class="auth-btn">
          登 录
        </el-button>
      </el-form>

      <div class="auth-alt">
        没有账号？<router-link to="/register">去注册</router-link>
      </div>

      <el-divider>或</el-divider>

      <el-button text type="primary" :loading="authStore.loading" @click="handleDemo" class="demo-btn">
        以演示账号体验
      </el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')

async function handleLogin() {
  if (!email.value || !password.value) return
  try {
    await authStore.login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/assistant'
    router.push(redirect)
  } catch {}
}

async function handleDemo() {
  try {
    await authStore.demoLogin()
    router.push('/assistant')
  } catch {}
}
</script>

<style scoped>
.auth-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  background: linear-gradient(135deg, #f8fafc 0%, #e0e7ff 50%, #c7d2fe 100%);
  position: relative;
  overflow: hidden;
}

.auth-page::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle at 30% 30%, rgba(99, 102, 241, 0.1) 0%, transparent 50%),
              radial-gradient(circle at 70% 70%, rgba(139, 92, 246, 0.08) 0%, transparent 50%);
  animation: float 30s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: rotate(0deg); }
  50% { transform: rotate(5deg); }
}

.auth-card {
  width: 420px;
  padding: 32px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 60px rgba(79, 70, 229, 0.15), 0 8px 24px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.8);
  position: relative;
  z-index: 1;
  animation: slideUp 0.6s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.auth-brand {
  text-align: center;
  margin-bottom: 32px;
}

.brand-mark {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  background: linear-gradient(135deg, #818cf8 0%, #4f46e5 100%);
  color: #fff;
  font-weight: 800;
  font-size: 24px;
  display: inline-grid;
  place-items: center;
  margin-bottom: 16px;
  box-shadow: 0 8px 24px rgba(79, 70, 229, 0.35);
  transition: all 0.3s ease;
}

.brand-mark:hover {
  transform: scale(1.05);
  box-shadow: 0 12px 32px rgba(79, 70, 229, 0.4);
}

.auth-brand h1 {
  margin: 0 0 6px;
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.02em;
}

.auth-brand .muted {
  font-size: 14px;
  color: #64748b;
}

.auth-error {
  margin-bottom: 16px;
}

.auth-btn {
  width: 100%;
  margin-top: 8px;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
}

.auth-alt {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: #64748b;
}

.auth-alt a {
  color: #4f46e5;
  font-weight: 600;
  transition: color 0.2s ease;
}

.auth-alt a:hover {
  color: #3730a3;
}

.demo-btn {
  width: 100%;
  height: 44px;
}

/* 输入框聚焦效果 */
.auth-card :deep(.el-input__wrapper) {
  border-radius: 12px;
  transition: all 0.25s ease;
}

.auth-card :deep(.el-input__wrapper:hover) {
  border-color: #818cf8;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1);
}

.auth-card :deep(.el-input__wrapper.is-focus) {
  border-color: #4f46e5;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
}

.auth-card :deep(.el-form-item__label) {
  font-weight: 600;
  font-size: 14px;
  color: #334155;
}
</style>
