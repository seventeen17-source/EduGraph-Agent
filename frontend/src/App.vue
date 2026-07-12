<template>
  <el-container class="app-shell">
    <!-- 移动端汉堡菜单 -->
    <div v-if="sidebarCollapsed" class="mobile-overlay" @click="sidebarCollapsed = false" />
    <el-aside width="260px" class="app-aside" :class="{ collapsed: sidebarCollapsed }">
      <div class="brand">
        <div class="brand-mark">EG</div>
        <div>
          <div class="brand-title">EduGraph</div>
          <div class="brand-subtitle">个性化学习平台</div>
        </div>
      </div>

      <el-menu :default-active="$route.path" router class="nav-menu" @select="sidebarCollapsed = false">
        <el-menu-item index="/assistant">
          <el-icon><MagicStick /></el-icon>
          <span>学习助手</span>
        </el-menu-item>
        <el-menu-item index="/profile/panel">
          <el-icon><User /></el-icon>
          <span>我的画像</span>
        </el-menu-item>
        <el-menu-item index="/learning-path">
          <el-icon><Guide /></el-icon>
          <span>学习路径</span>
        </el-menu-item>
        <el-menu-item index="/graph">
          <el-icon><Share /></el-icon>
          <span>知识图谱</span>
        </el-menu-item>
        <el-menu-item index="/resources">
          <el-icon><Document /></el-icon>
          <span>AI 备课台</span>
        </el-menu-item>
        <el-menu-item index="/knowledge-center">
          <el-icon><Collection /></el-icon>
          <span>知识中心</span>
        </el-menu-item>
        <el-menu-item index="/exercise">
          <el-icon><EditPen /></el-icon>
          <span>练习与评估</span>
        </el-menu-item>
        <el-menu-item index="/exercise-history">
          <el-icon><Notebook /></el-icon>
          <span>练习记录</span>
        </el-menu-item>
        <el-menu-item index="/learning-growth">
          <el-icon><TrendCharts /></el-icon>
          <span>学习成长</span>
        </el-menu-item>
        <el-menu-item index="/admin">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <el-button class="hamburger" text @click="sidebarCollapsed = !sidebarCollapsed">
            <el-icon :size="22"><Expand /></el-icon>
          </el-button>
          <span class="header-title">{{ pageTitle }}</span>
        </div>
        <div class="header-right">
          <el-progress :percentage="percent(profileStore.completeness)" :stroke-width="10" class="header-progress" />
          <div class="user-info">
            <el-avatar :size="36" :style="{ background: 'linear-gradient(135deg, #4f46e5, #818cf8)' }">
              {{ profileStore.displayName?.charAt(0) || '同学' }}
            </el-avatar>
            <div class="user-meta">
              <span class="user-name">{{ profileStore.displayName }}</span>
              <span class="user-id">{{ profileStore.studentId }}</span>
            </div>
          </div>
          <el-button type="primary" plain size="small" @click="authStore.demoLogin()">演示登录</el-button>
          <el-button v-if="authStore.isAuthenticated" text size="small" @click="authStore.logout(); $router.push('/login')">退出</el-button>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  Collection,
  Document,
  EditPen,
  Expand,
  Guide,
  MagicStick,
  Notebook,
  Setting,
  Share,
  TrendCharts,
  User
} from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'
import { useProfileStore } from '@/stores/profile'
import { percent } from '@/utils/format'

const authStore = useAuthStore()

const route = useRoute()
const profileStore = useProfileStore()
const sidebarCollapsed = ref(false)

const pageTitles: Record<string, string> = {
  '/assistant': '学习助手',
  '/profile/panel': '我的画像',
  '/profile/chat': '对话画像',
  '/learning-path': '学习路径',
  '/graph': '知识图谱',
  '/resources': 'AI 备课台',
  '/knowledge-center': '知识中心',
  '/exercise': '练习测试',
  '/exercise-history': '练习记录',
  '/assessment': '效果评估',
  '/learning-growth': '学习成长',
  '/admin': '系统设置',
}

const pageTitle = computed(() => pageTitles[route.path] || 'EduGraph')
</script>

<style scoped>
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  padding: 0 32px;
  height: 72px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.header-left {
  display: flex;
  align-items: center;
}

.header-title {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.02em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.header-progress {
  width: 220px;
}

.header-progress :deep(.el-progress-bar__outer) {
  border-radius: 10px;
}

.header-progress :deep(.el-progress-bar__inner) {
  border-radius: 10px;
  background: linear-gradient(90deg, #818cf8 0%, #4f46e5 100%);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 16px 6px 6px;
  background: #f8fafc;
  border-radius: 30px;
}

.user-meta {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.user-id {
  font-size: 11px;
  color: #94a3b8;
}

.app-main {
  padding: 28px 36px;
  background: #f8fafc;
}

/* 页面过渡 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 汉堡菜单（桌面端隐藏） */
.hamburger { display: none; }

.mobile-overlay {
  display: none;
}

/* 移动端适配 */
@media (max-width: 1024px) {
  .hamburger { display: inline-flex; }

  .app-aside {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 1000;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }

  .app-aside.collapsed {
    transform: translateX(0);
  }

  .mobile-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.3);
    z-index: 999;
  }

  .app-main {
    padding: 16px;
  }

  .header-progress {
    width: 120px !important;
  }

  .header-title {
    font-size: 16px !important;
  }
}

@media (max-width: 768px) {
  .app-header {
    padding: 0 16px;
    height: 56px;
  }

  .header-progress { display: none; }

  .user-meta { display: none; }

  .header-right { gap: 8px; }

  .app-main { padding: 12px; }
}
</style>
