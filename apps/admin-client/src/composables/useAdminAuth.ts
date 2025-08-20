import { ref, computed, watch } from 'vue'
import type { Ref, ComputedRef } from 'vue'

interface User {
  id: string
  email: string
  workspaces: Workspace[]
  is_admin: boolean
}

interface Workspace {
  id: string
  name: string
  database_name: string
  role: 'admin' | 'member'
  joined_at?: string
}

interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

interface AdminAuthState {
  user: Ref<User | null>
  accessToken: Ref<string | null>
  refreshToken: Ref<string | null>
  isAuthenticated: ComputedRef<boolean>
  isLoading: Ref<boolean>
  error: Ref<string | null>
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Global auth state
const user = ref<User | null>(null)
const accessToken = ref<string | null>(null)
const refreshToken = ref<string | null>(null)
const isLoading = ref(false)
const error = ref<string | null>(null)

// Load tokens from localStorage on initialization
if (typeof window !== 'undefined') {
  const storedAccessToken = localStorage.getItem('admin_access_token')
  const storedRefreshToken = localStorage.getItem('admin_refresh_token')
  const storedUser = localStorage.getItem('admin_user')
  
  if (storedAccessToken) accessToken.value = storedAccessToken
  if (storedRefreshToken) refreshToken.value = storedRefreshToken
  if (storedUser) {
    try {
      user.value = JSON.parse(storedUser)
    } catch (e) {
      console.error('Failed to parse stored admin user:', e)
    }
  }
}

// Save tokens to localStorage when they change
watch(accessToken, (newToken) => {
  if (newToken) {
    localStorage.setItem('admin_access_token', newToken)
  } else {
    localStorage.removeItem('admin_access_token')
  }
})

watch(refreshToken, (newToken) => {
  if (newToken) {
    localStorage.setItem('admin_refresh_token', newToken)
  } else {
    localStorage.removeItem('admin_refresh_token')
  }
})

watch(user, (newUser) => {
  if (newUser) {
    localStorage.setItem('admin_user', JSON.stringify(newUser))
  } else {
    localStorage.removeItem('admin_user')
  }
})

export function useAdminAuth(): AdminAuthState {
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)

  async function login(email: string, password: string): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Login failed')
      }

      const data: TokenResponse = await response.json()
      
      accessToken.value = data.access_token
      refreshToken.value = data.refresh_token

      // Fetch user info
      await fetchCurrentUser()
      
      // Verify admin access (user should have is_admin flag set to true)
      if (!user.value?.is_admin) {
        await logout()
        throw new Error('Admin access required')
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'An error occurred during login'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function logout(): Promise<void> {
    // Clear local state
    user.value = null
    accessToken.value = null
    refreshToken.value = null
    error.value = null
    
    // Optional: Call logout endpoint
    try {
      await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
        method: 'POST',
      })
    } catch {
      // Ignore logout endpoint errors
    }
  }

  async function refreshAccessToken(): Promise<void> {
    if (!refreshToken.value) {
      throw new Error('No refresh token available')
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken.value }),
      })

      if (!response.ok) {
        throw new Error('Token refresh failed')
      }

      const data: TokenResponse = await response.json()
      accessToken.value = data.access_token
      
      if (data.refresh_token) {
        refreshToken.value = data.refresh_token
      }
    } catch (err) {
      await logout()
      throw err
    }
  }

  async function fetchCurrentUser(): Promise<void> {
    if (!accessToken.value) {
      throw new Error('No access token available')
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken.value}`,
        },
      })

      if (!response.ok) {
        if (response.status === 401) {
          await refreshAccessToken()
          return fetchCurrentUser()
        }
        throw new Error('Failed to fetch user info')
      }

      const userData = await response.json()
      user.value = userData
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch user info'
      throw err
    }
  }

  // Auto-refresh token before expiry
  let refreshTimer: number | null = null
  
  watch(accessToken, (token) => {
    if (refreshTimer) {
      clearTimeout(refreshTimer)
      refreshTimer = null
    }
    
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        const expiresAt = payload.exp * 1000
        const now = Date.now()
        const timeUntilExpiry = expiresAt - now
        const refreshIn = Math.max(0, timeUntilExpiry - 60000)
        
        if (refreshIn > 0) {
          refreshTimer = window.setTimeout(() => {
            refreshAccessToken().catch(console.error)
          }, refreshIn)
        }
      } catch (e) {
        console.error('Failed to decode token for auto-refresh:', e)
      }
    }
  }, { immediate: true })

  // Initialize: try to fetch user if we have a token
  if (accessToken.value && !user.value) {
    fetchCurrentUser().catch(() => {
      refreshAccessToken().catch(() => {
        logout()
      })
    })
  }

  return {
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    refreshAccessToken,
    fetchCurrentUser,
  }
}