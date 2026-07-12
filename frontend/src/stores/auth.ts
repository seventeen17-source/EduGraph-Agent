import { defineStore } from 'pinia'
import { apiClient } from '@/api/client'

interface UserInfo {
  id: string
  email: string
  username: string
  is_active: boolean
}

interface AuthState {
  user: UserInfo | null
  accessToken: string
  refreshToken: string
  isAuthenticated: boolean
  loading: boolean
  error: string | null
}

function loadState(): Partial<AuthState> {
  try {
    const stored = localStorage.getItem('edugraph_auth')
    if (stored) {
      const parsed = JSON.parse(stored)
      return {
        user: parsed.user || null,
        accessToken: parsed.accessToken || '',
        refreshToken: parsed.refreshToken || '',
        isAuthenticated: !!(parsed.accessToken && parsed.user),
      }
    }
  } catch {}
  return {}
}

function persist(state: AuthState) {
  try {
    localStorage.setItem('edugraph_auth', JSON.stringify({
      user: state.user,
      accessToken: state.accessToken,
      refreshToken: state.refreshToken,
    }))
  } catch {}
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    accessToken: '',
    refreshToken: '',
    isAuthenticated: false,
    loading: false,
    error: null,
    ...loadState(),
  }),

  getters: {
    studentId(state): string {
      return state.user?.id || ''
    },
    displayName(state): string {
      return state.user?.username || ''
    },
  },

  actions: {
    _setAuth(user: UserInfo, accessToken: string, refreshToken: string) {
      this.user = user
      this.accessToken = accessToken
      this.refreshToken = refreshToken
      this.isAuthenticated = true
      this.error = null
      persist(this.$state)
    },

    async login(email: string, password: string) {
      this.loading = true
      this.error = null
      try {
        const res = await apiClient.post('/api/auth/login', { email, password })
        this._setAuth(res.data.user, res.data.access_token, res.data.refresh_token)
      } catch (err: any) {
        this.error = err?.displayMessage || '登录失败'
        throw err
      } finally {
        this.loading = false
      }
    },

    async register(email: string, username: string, password: string) {
      this.loading = true
      this.error = null
      try {
        const res = await apiClient.post('/api/auth/register', { email, username, password })
        this._setAuth(res.data.user, res.data.access_token, res.data.refresh_token)
      } catch (err: any) {
        this.error = err?.displayMessage || '注册失败'
        throw err
      } finally {
        this.loading = false
      }
    },

    async demoLogin() {
      this.loading = true
      this.error = null
      try {
        const res = await apiClient.post('/api/auth/demo', {})
        this._setAuth(res.data.user, res.data.access_token, res.data.refresh_token)
      } catch (err: any) {
        this.error = err?.displayMessage || '演示登录失败'
        throw err
      } finally {
        this.loading = false
      }
    },

    async refreshAuth() {
      if (!this.refreshToken) {
        this.logout()
        return
      }
      try {
        const res = await apiClient.post('/api/auth/refresh', { refresh_token: this.refreshToken })
        this._setAuth(res.data.user, res.data.access_token, res.data.refresh_token)
      } catch {
        this.logout()
      }
    },

    logout() {
      this.user = null
      this.accessToken = ''
      this.refreshToken = ''
      this.isAuthenticated = false
      this.error = null
      try { localStorage.removeItem('edugraph_auth') } catch {}
    },
  },
})
