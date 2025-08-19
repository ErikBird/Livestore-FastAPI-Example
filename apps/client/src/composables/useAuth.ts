import { ref, computed, watch } from 'vue'
import type { Ref, ComputedRef } from 'vue'

interface User {
  id: string
  email: string
  workspaces: Workspace[]
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

interface AuthState {
  user: Ref<User | null>
  accessToken: Ref<string | null>
  refreshToken: Ref<string | null>
  isAuthenticated: ComputedRef<boolean>
  isLoading: Ref<boolean>
  error: Ref<string | null>
  currentWorkspace: ComputedRef<Workspace | null>
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Global auth state
const user = ref<User | null>(null)
const accessToken = ref<string | null>(null)
const refreshToken = ref<string | null>(null)
const isLoading = ref(false)
const error = ref<string | null>(null)
const selectedWorkspaceId = ref<string | null>(null)

// Load tokens from localStorage on initialization
if (typeof window !== 'undefined') {
  const storedAccessToken = localStorage.getItem('access_token')
  const storedRefreshToken = localStorage.getItem('refresh_token')
  const storedUser = localStorage.getItem('user')
  
  if (storedAccessToken) accessToken.value = storedAccessToken
  if (storedRefreshToken) refreshToken.value = storedRefreshToken
  if (storedUser) {
    try {
      user.value = JSON.parse(storedUser)
      // Select first workspace by default
      if (user.value?.workspaces?.length) {
        selectedWorkspaceId.value = user.value.workspaces[0].id
      }
    } catch (e) {
      console.error('Failed to parse stored user:', e)
    }
  }
}

// Save tokens to localStorage when they change
watch(accessToken, (newToken) => {
  if (newToken) {
    localStorage.setItem('access_token', newToken)
  } else {
    localStorage.removeItem('access_token')
  }
})

watch(refreshToken, (newToken) => {
  if (newToken) {
    localStorage.setItem('refresh_token', newToken)
  } else {
    localStorage.removeItem('refresh_token')
  }
})

watch(user, (newUser) => {
  if (newUser) {
    localStorage.setItem('user', JSON.stringify(newUser))
  } else {
    localStorage.removeItem('user')
  }
})

export function useAuth(): AuthState {
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  
  const currentWorkspace = computed(() => {
    if (!user.value || !selectedWorkspaceId.value) return null
    return user.value.workspaces.find(w => w.id === selectedWorkspaceId.value) || null
  })

  async function login(email: string, password: string): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
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
    selectedWorkspaceId.value = null
    error.value = null
    
    // Optional: Call logout endpoint (not strictly necessary with JWT)
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
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
      const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
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
      
      // Optionally update refresh token if server returns a new one
      if (data.refresh_token) {
        refreshToken.value = data.refresh_token
      }
    } catch (err) {
      // If refresh fails, clear auth state
      await logout()
      throw err
    }
  }

  async function fetchCurrentUser(): Promise<void> {
    if (!accessToken.value) {
      throw new Error('No access token available')
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken.value}`,
        },
      })

      if (!response.ok) {
        if (response.status === 401) {
          // Try to refresh token
          await refreshAccessToken()
          // Retry with new token
          return fetchCurrentUser()
        }
        throw new Error('Failed to fetch user info')
      }

      const userData = await response.json()
      user.value = userData
      
      // Select first workspace if none selected
      if (userData.workspaces?.length && !selectedWorkspaceId.value) {
        selectedWorkspaceId.value = userData.workspaces[0].id
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch user info'
      throw err
    }
  }

  function selectWorkspace(workspaceId: string): void {
    if (user.value?.workspaces.some(w => w.id === workspaceId)) {
      selectedWorkspaceId.value = workspaceId
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
      // Decode token to get expiry (without verification)
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        const expiresAt = payload.exp * 1000 // Convert to milliseconds
        const now = Date.now()
        const timeUntilExpiry = expiresAt - now
        
        // Refresh 1 minute before expiry
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
      // If initial fetch fails, try to refresh
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
    currentWorkspace,
    login,
    logout,
    refreshAccessToken,
    fetchCurrentUser,
    selectWorkspace,
  }
}