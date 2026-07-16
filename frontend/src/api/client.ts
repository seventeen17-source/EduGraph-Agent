import axios from 'axios'

export function defaultApiBaseUrl() {
  if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL
  if (typeof window !== 'undefined' && window.location?.hostname) {
    return `${window.location.protocol}//${window.location.hostname}:8000`
  }
  return 'http://127.0.0.1:8000'
}

export const apiClient = axios.create({
  baseURL: defaultApiBaseUrl(),
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

// ── 请求拦截器：自动附加 access token ──

apiClient.interceptors.request.use((config) => {
  // 动态导入避免循环依赖
  try {
    const raw = localStorage.getItem('edugraph_auth')
    if (raw) {
      const { accessToken } = JSON.parse(raw)
      if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`
      }
    }
  } catch {}
  return config
})

// ── 响应拦截器：401 → 自动刷新 token → 重试 ──

let isRefreshing = false
let refreshPromise: Promise<any> | null = null

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const detail = error?.response?.data?.detail
    error.displayMessage = typeof detail === 'string' ? detail : error.message || '请求失败'

    // 401 + 不是 refresh 请求本身 → 尝试刷新
    if (error?.response?.status === 401 && !originalRequest._retry
        && !originalRequest.url?.includes('/auth/')) {
      originalRequest._retry = true

      if (!isRefreshing) {
        isRefreshing = true
        try {
          const raw = localStorage.getItem('edugraph_auth')
          if (raw) {
            const { refreshToken } = JSON.parse(raw)
            if (refreshToken) {
              refreshPromise = apiClient.post('/api/auth/refresh', { refresh_token: refreshToken })
              const res = await refreshPromise
              // 更新 localStorage
              const stored = JSON.parse(localStorage.getItem('edugraph_auth') || '{}')
              stored.accessToken = res.data.access_token
              stored.refreshToken = res.data.refresh_token
              stored.user = res.data.user
              localStorage.setItem('edugraph_auth', JSON.stringify(stored))
              // 重试原请求
              originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`
              return apiClient(originalRequest)
            }
          }
        } catch {
          // refresh 失败 → 清除登录态
          localStorage.removeItem('edugraph_auth')
          window.location.href = '/login'
        } finally {
          isRefreshing = false
          refreshPromise = null
        }
      } else if (refreshPromise) {
        // 等待正在进行的刷新
        await refreshPromise
        const stored = JSON.parse(localStorage.getItem('edugraph_auth') || '{}')
        originalRequest.headers.Authorization = `Bearer ${stored.accessToken}`
        return apiClient(originalRequest)
      }
    }

    return Promise.reject(error)
  },
)
