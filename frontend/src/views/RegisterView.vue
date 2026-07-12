<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <div class="auth-brand">
        <div class="brand-mark">EG</div>
        <h1>注册新账号</h1>
        <p class="muted">注册后将自动创建学习画像</p>
      </div>

      <el-form @submit.prevent="handleRegister" label-position="top" size="large">
        <el-form-item label="用户名">
          <el-input
            v-model="username"
            placeholder="你的名字"
            :disabled="authStore.loading"
          />
        </el-form-item>

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
            placeholder="至少 6 位"
            show-password
            :disabled="authStore.loading"
          />
        </el-form-item>

        <el-form-item label="确认密码">
          <el-input
            v-model="confirmPassword"
            type="password"
            placeholder="再次输入密码"
            show-password
            :disabled="authStore.loading"
            @keyup.enter="handleRegister"
          />
        </el-form-item>

        <el-alert v-if="validationError" :title="validationError" type="warning" show-icon :closable="false" class="auth-error" />
        <el-alert v-if="authStore.error" :title="authStore.error" type="error" show-icon :closable="false" class="auth-error" />

        <el-button type="primary" native-type="submit" :loading="authStore.loading" class="auth-btn">
          注 册
        </el-button>
      </el-form>

      <div class="auth-alt">
        已有账号？<router-link to="/login">去登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const validationError = ref('')

async function handleRegister() {
  validationError.value = ''
  if (!username.value.trim()) {
    validationError.value = '请输入用户名'
    return
  }
  if (!email.value.trim()) {
    validationError.value = '请输入邮箱'
    return
  }
  if (password.value.length < 6) {
    validationError.value = '密码至少 6 位'
    return
  }
  if (password.value !== confirmPassword.value) {
    validationError.value = '两次密码不一致'
    return
  }

  try {
    await authStore.register(email.value, username.value, password.value)
    router.push('/profile/chat')
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
</style>
