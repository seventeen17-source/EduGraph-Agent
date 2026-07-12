import { defineStore } from 'pinia'

import {
  chatProfile,
  getProfile,
  getProfileChatHistory,
  getProfileDashboard,
  getProfileHistory,
  initProfile,
  patchProfile,
  updateLearningProgress,
  updateProfileFromExercise,
  updateProfileFromExerciseRound
} from '@/api/profile'
import { submitExerciseSession } from '@/api/exercises'
import type {
  ProfileDashboardResponse,
  ProfileChatMessageRecord,
  ExerciseRoundAttempt,
  ProfileUpdateRecord,
  StudentProfile,
  StudentProfileInput
} from '@/types/profile'
import type { ExerciseSessionSubmitRequest } from '@/types/exercises'

const DEMO_MESSAGE =
  '我是计算机专业大二的，学过 Python 和高数，想学机器学习来完成课程项目。我对梯度下降和神经网络训练不太理解，平时比较喜欢看代码和图解。'

export const useProfileStore = defineStore('profile', {
  state: () => ({
    studentId: '',
    displayName: '',
    profile: null as StudentProfile | null,
    dashboard: null as ProfileDashboardResponse | null,
    completeness: 0,
    sessionStatus: 'building',
    currentRound: 0,
    missingDimensions: [] as string[],
    history: [] as ProfileUpdateRecord[],
    chatMessages: [] as ProfileChatMessageRecord[],
    updatedDimensions: [] as string[],
    loading: false,
    error: null as string | null
  }),
  getters: {
    studentProfileInput(state): StudentProfileInput {
      const profile = state.profile
      const dashboard = state.dashboard
      const weakFromProfile =
        profile?.weak_points.self_reported.map((item) => item.node_id || item.topic).filter(Boolean) || []
      const weakFromDashboard = dashboard?.weak_point_rank.map((item) => item.node_id || item.label).filter(Boolean) || []
      return {
        weak_points: Array.from(new Set([...weakFromProfile, ...weakFromDashboard])) as string[],
        preferences: profile?.preferences.resource_ranking || ['diagram', 'code_case'],
        goal: profile?.learning_goal.description || '理解机器学习核心概念',
        mastery: Object.fromEntries(
          Object.entries(profile?.node_mastery || {}).map(([nodeId, item]) => [nodeId, item.mastery_score])
        )
      }
    }
  },
  actions: {
    async initFromAuth() {
      const { useAuthStore } = await import('@/stores/auth')
      const authStore = useAuthStore()
      if (!authStore.studentId) {
        this.error = '未登录'
        return
      }
      this.studentId = authStore.studentId
      this.displayName = authStore.displayName || this.displayName
      try {
        await this.loadCurrentStudent()
      } catch (err: any) {
        // 首次使用的用户可能还没有 profile
        if (err?.response?.status === 404 || err?.displayMessage?.includes('not found')) {
          this.error = null  // 正常：新用户还没建画像
        } else {
          this.error = err?.displayMessage || '画像加载失败'
        }
      }
    },

    async useDemoStudent() {
      // 演示登录：使用 authStore 中的 demo 用户 ID
      const { useAuthStore } = await import('@/stores/auth')
      const authStore = useAuthStore()
      this.studentId = authStore.studentId || 'demo_student_001'
      this.displayName = authStore.displayName || '张同学'
      try {
        await this.loadCurrentStudent()
      } catch {
        await this.initByMessage(DEMO_MESSAGE)
      }
    },
    async resetDemoStudent() {
      const { useAuthStore } = await import('@/stores/auth')
      const authStore = useAuthStore()
      this.studentId = authStore.studentId || 'demo_student_001'
      this.displayName = authStore.displayName || '张同学'
      await this.initByMessage(DEMO_MESSAGE)
    },
    async loadCurrentStudent() {
      // 确保有 studentId
      if (!this.studentId) {
        const { useAuthStore } = await import('@/stores/auth')
        const authStore = useAuthStore()
        if (authStore.studentId) {
          this.studentId = authStore.studentId
          this.displayName = authStore.displayName || this.displayName
        } else {
          this.error = '未登录，无法加载画像'
          return
        }
      }
      this.loading = true
      this.error = null
      try {
        await this.refreshProfile()
        await this.refreshDashboard()
        await this.loadChatHistory()
      } catch (error: any) {
        this.error = error.displayMessage || '画像加载失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async initByMessage(message: string) {
      this.loading = true
      this.error = null
      try {
        const response = await initProfile({
          student_id: this.studentId,
          display_name: this.displayName,
          message
        })
        this.applyChatResponse(response)
        await this.refreshDashboard()
        await this.loadChatHistory()
        return response
      } catch (error: any) {
        this.error = error.displayMessage || '画像初始化失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async sendMessage(message: string) {
      this.loading = true
      this.error = null
      try {
        const response = await chatProfile({
          student_id: this.studentId,
          display_name: this.displayName,
          message
        })
        this.applyChatResponse(response)
        await this.refreshDashboard()
        await this.loadChatHistory()
        return response
      } catch (error: any) {
        this.error = error.displayMessage || '画像更新失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    applyChatResponse(response: import('@/types/profile').ProfileChatResponse) {
      this.profile = response.profile
      this.completeness = response.completeness
      this.sessionStatus = response.session_status
      this.currentRound = response.current_round
      this.missingDimensions = response.missing_dimensions
      this.updatedDimensions = response.updated_dimensions
    },
    async refreshProfile() {
      this.profile = await getProfile(this.studentId)
      this.completeness = this.profile.completeness
    },
    async refreshDashboard() {
      try {
        this.dashboard = await getProfileDashboard(this.studentId)
        this.history = await getProfileHistory(this.studentId)
        this.completeness = this.dashboard.completeness
      } catch {
        if (this.profile) {
          this.history = []
        }
      }
    },
    async loadChatHistory() {
      try {
        this.chatMessages = await getProfileChatHistory(this.studentId)
        this.currentRound = Math.max(
          this.currentRound,
          ...this.chatMessages.map((message) => message.round_no),
          this.chatMessages.length ? 1 : 0
        )
      } catch {
        this.chatMessages = []
      }
    },
    async patchDimension(dimension: string, value: Record<string, any>) {
      this.profile = await patchProfile(this.studentId, { dimension, value })
      await this.refreshDashboard()
    },
    async recordExercise(payload: { exercise_id: string; node_ids: string[]; is_correct: boolean; difficulty?: number }) {
      const response = await updateProfileFromExercise({
        student_id: this.studentId,
        cognitive_level: 'understand',
        used_hint: false,
        ...payload
      })
      this.profile = response.profile
      this.dashboard = response.dashboard
      await this.refreshDashboard()
      return response
    },
    async recordExerciseRound(payload: { round_id?: string | null; attempts: ExerciseRoundAttempt[] }) {
      const response = await updateProfileFromExerciseRound({
        student_id: this.studentId,
        round_id: payload.round_id,
        attempts: payload.attempts.map((attempt) => ({
          cognitive_level: 'understand',
          used_hint: false,
          ...attempt
        }))
      })
      this.profile = response.profile
      this.dashboard = response.dashboard
      await this.refreshDashboard()
      return response
    },
    async recordExerciseSession(payload: Omit<ExerciseSessionSubmitRequest, 'student_id'>) {
      const response = await submitExerciseSession({
        student_id: this.studentId,
        ...payload,
      })
      this.profile = response.profile
      this.dashboard = response.dashboard
      await this.refreshDashboard()
      return response
    },
    async recordProgress(payload: {
      completed_node_ids?: string[]
      in_progress_node_ids?: string[]
      current_chapter_id?: string
      completion_rate?: number
    }) {
      const response = await updateLearningProgress({
        student_id: this.studentId,
        ...payload
      })
      this.profile = response.profile
      this.dashboard = response.dashboard
      await this.refreshDashboard()
      return response
    }
  }
})
