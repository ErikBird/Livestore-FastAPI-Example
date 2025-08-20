import { ref } from 'vue'
import { useAdminAuth } from './useAdminAuth'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface User {
  id: string
  email: string
  created_at: string
  updated_at: string
  is_active: boolean
}

interface Workspace {
  id: string
  name: string
  owner_id: string
  database_name: string
  created_at: string
}

interface WorkspaceMember {
  user_id: string
  email: string
  is_active: boolean
  role: string
  joined_at: string
}

export function useAdminApi() {
  const { accessToken, refreshAccessToken } = useAdminAuth()
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function makeAuthenticatedRequest(url: string, options: RequestInit = {}) {
    if (!accessToken.value) {
      throw new Error('No access token available')
    }

    const response = await fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${accessToken.value}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (response.status === 401) {
      // Try to refresh token and retry
      try {
        await refreshAccessToken()
        return fetch(url, {
          ...options,
          headers: {
            'Authorization': `Bearer ${accessToken.value}`,
            'Content-Type': 'application/json',
            ...options.headers,
          },
        })
      } catch {
        throw new Error('Authentication failed')
      }
    }

    return response
  }

  // Users API
  async function getUsers(): Promise<{ users: User[], total: number }> {
    isLoading.value = true
    error.value = null

    try {
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/api/v1/admin/users`)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to fetch users')
      }

      return await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch users'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createUser(email: string, password: string, workspaceName?: string): Promise<any> {
    isLoading.value = true
    error.value = null

    try {
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/api/v1/admin/users`, {
        method: 'POST',
        body: JSON.stringify({
          email,
          password,
          workspace_name: workspaceName
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to create user')
      }

      return await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create user'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Workspaces API
  async function getWorkspaces(): Promise<{ workspaces: Workspace[], total: number }> {
    isLoading.value = true
    error.value = null

    try {
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/api/v1/admin/workspaces`)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to fetch workspaces')
      }

      return await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch workspaces'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function getWorkspaceDetails(workspaceId: string): Promise<{ workspace: Workspace, members: WorkspaceMember[] }> {
    isLoading.value = true
    error.value = null

    try {
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/api/v1/admin/workspaces/${workspaceId}`)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to fetch workspace details')
      }

      return await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch workspace details'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createWorkspace(name: string, ownerEmail: string): Promise<any> {
    isLoading.value = true
    error.value = null

    try {
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/api/v1/admin/workspaces`, {
        method: 'POST',
        body: JSON.stringify({
          name,
          owner_email: ownerEmail
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to create workspace')
      }

      return await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create workspace'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function addWorkspaceMember(workspaceId: string, userEmail: string, role: string = 'member'): Promise<any> {
    isLoading.value = true
    error.value = null

    try {
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/api/v1/admin/workspaces/${workspaceId}/members`, {
        method: 'POST',
        body: JSON.stringify({
          user_email: userEmail,
          role
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to add member')
      }

      return await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to add member'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function removeWorkspaceMember(workspaceId: string, userId: string): Promise<any> {
    isLoading.value = true
    error.value = null

    try {
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/api/v1/admin/workspaces/${workspaceId}/members/${userId}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to remove member')
      }

      return await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to remove member'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // System Stats API
  async function getSystemStats(): Promise<any> {
    isLoading.value = true
    error.value = null

    try {
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/api/v1/admin/stats`)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to fetch system stats')
      }

      return await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch system stats'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function deleteUser(userId: string): Promise<any> {
    isLoading.value = true
    error.value = null

    try {
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/api/v1/admin/users/${userId}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to delete user')
      }

      return await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete user'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function deleteWorkspace(workspaceId: string): Promise<any> {
    isLoading.value = true
    error.value = null

    try {
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/api/v1/admin/workspaces/${workspaceId}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to delete workspace')
      }

      return await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete workspace'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  return {
    isLoading,
    error,
    getUsers,
    createUser,
    deleteUser,
    getWorkspaces,
    getWorkspaceDetails,
    createWorkspace,
    deleteWorkspace,
    addWorkspaceMember,
    removeWorkspaceMember,
    getSystemStats,
  }
}