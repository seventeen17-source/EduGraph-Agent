import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/', redirect: '/assistant' },
  { path: '/login', component: () => import('@/views/LoginView.vue') },
  { path: '/register', component: () => import('@/views/RegisterView.vue') },
  { path: '/assistant', component: () => import('@/views/AssistantView.vue') },
  { path: '/profile/chat', component: () => import('@/views/ProfileChatView.vue') },
  { path: '/profile/panel', component: () => import('@/views/ProfilePanelView.vue') },
  { path: '/graph', component: () => import('@/views/KnowledgeGraphView.vue') },
  { path: '/learning-path', component: () => import('@/views/LearningPathView.vue') },
  { path: '/resources', component: () => import('@/views/ResourceGenerationView.vue') },
  { path: '/knowledge-center', component: () => import('@/views/KnowledgeCenterView.vue') },
  { path: '/tutor', component: () => import('@/views/TutorChatView.vue') },
  { path: '/exercise', component: () => import('@/views/ExerciseView.vue') },
  { path: '/exercise-history', component: () => import('@/views/ExerciseHistoryView.vue') },
  { path: '/assessment', component: () => import('@/views/AssessmentView.vue') },
  { path: '/learning-growth', component: () => import('@/views/LearningGrowthView.vue') },
  { path: '/admin', component: () => import('@/views/AdminView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

const PUBLIC_PAGES = ['/login', '/register']

router.beforeEach(async (to, _from, next) => {
  if (PUBLIC_PAGES.includes(to.path)) {
    return next()
  }

  const authStore = useAuthStore()
  if (!authStore.isAuthenticated) {
    // 尝试从 localStorage 恢复
    const stored = localStorage.getItem('edugraph_auth')
    if (stored) {
      try {
        await authStore.refreshAuth()
        if (authStore.isAuthenticated) return next()
      } catch {}
    }
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  next()
})

export default router
