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
  background: linear-gradient(135deg, #f8fafc 0%, #e0e7ff 100%);
}

.auth-card {
  width: 420px;
  padding: 8px 0;
}

.auth-brand {
  text-align: center;
  margin-bottom: 28px;
}

.brand-mark {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, #818cf8 0%, #4f46e5 100%);
  color: #fff;
  font-weight: 800;
  font-size: 20px;
  display: inline-grid;
  place-items: center;
  margin-bottom: 12px;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.auth-brand h1 {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
}

.auth-error {
  margin-bottom: 12px;
}

.auth-btn {
  width: 100%;
  margin-top: 4px;
}

.auth-alt {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: #64748b;
}

.auth-alt a {
  color: #4f46e5;
  font-weight: 500;
}

.demo-btn {
  width: 100%;
}
</style>
