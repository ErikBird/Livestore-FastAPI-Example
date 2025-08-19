<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAdminAuth } from '../composables/useAdminAuth'
import { useAdminApi } from '../composables/useAdminApi'
import UserManagement from './UserManagement.vue'
import WorkspaceManagement from './WorkspaceManagement.vue'
import SystemStats from './SystemStats.vue'

const { user, logout } = useAdminAuth()
const { getSystemStats } = useAdminApi()

const activeTab = ref('dashboard')
const stats = ref<any>(null)

const tabs = [
  { id: 'dashboard', name: 'Dashboard' },
  { id: 'users', name: 'Users' },
  { id: 'workspaces', name: 'Workspaces' },
]

async function loadStats() {
  try {
    stats.value = await getSystemStats()
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

async function handleLogout() {
  await logout()
  window.location.reload()
}

onMounted(() => {
  loadStats()
})
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Navigation -->
    <nav class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex">
            <div class="flex-shrink-0 flex items-center">
              <h1 class="text-xl font-bold text-gray-900">Admin Dashboard</h1>
            </div>
            <div class="hidden sm:ml-6 sm:flex sm:space-x-8">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                @click="activeTab = tab.id"
                class="inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                :class="{
                  'border-indigo-500 text-gray-900': activeTab === tab.id,
                  'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300': activeTab !== tab.id
                }"
              >
                {{ tab.name }}
              </button>
            </div>
          </div>
          <div class="flex items-center">
            <span class="text-sm text-gray-700 mr-4">{{ user?.email }}</span>
            <button
              @click="handleLogout"
              class="bg-white border border-gray-300 rounded-md px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Mobile tab navigation -->
    <div class="sm:hidden border-b border-gray-200">
      <nav class="-mb-px flex space-x-8 px-4" aria-label="Tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          class="py-2 px-1 border-b-2 font-medium text-sm"
          :class="{
            'border-indigo-500 text-indigo-600': activeTab === tab.id,
            'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300': activeTab !== tab.id
          }"
        >
          {{ tab.name }}
        </button>
      </nav>
    </div>

    <!-- Main content -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        
        <!-- Dashboard Tab -->
        <div v-if="activeTab === 'dashboard'">
          <div class="mb-6">
            <h2 class="text-2xl font-bold text-gray-900">System Overview</h2>
            <p class="text-gray-600">Monitor your LiveStore system health and usage</p>
          </div>
          
          <SystemStats :stats="stats" />
          
          <div class="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div class="bg-white overflow-hidden shadow rounded-lg">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
                <div class="space-y-3">
                  <button
                    @click="activeTab = 'users'"
                    class="w-full text-left bg-gray-50 hover:bg-gray-100 rounded-lg p-3 transition-colors"
                  >
                    <div class="font-medium text-gray-900">Manage Users</div>
                    <div class="text-sm text-gray-500">View and manage user accounts</div>
                  </button>
                  <button
                    @click="activeTab = 'workspaces'"
                    class="w-full text-left bg-gray-50 hover:bg-gray-100 rounded-lg p-3 transition-colors"
                  >
                    <div class="font-medium text-gray-900">Manage Workspaces</div>
                    <div class="text-sm text-gray-500">Create and configure workspaces</div>
                  </button>
                </div>
              </div>
            </div>
            
            <div class="bg-white overflow-hidden shadow rounded-lg">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">System Info</h3>
                <dl class="space-y-2">
                  <div>
                    <dt class="text-sm font-medium text-gray-500">Database Status</dt>
                    <dd class="text-sm text-gray-900">{{ stats?.database_status || 'Loading...' }}</dd>
                  </div>
                  <div>
                    <dt class="text-sm font-medium text-gray-500">Admin User</dt>
                    <dd class="text-sm text-gray-900">{{ user?.email }}</dd>
                  </div>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <!-- Users Tab -->
        <UserManagement v-else-if="activeTab === 'users'" />

        <!-- Workspaces Tab -->
        <WorkspaceManagement v-else-if="activeTab === 'workspaces'" />

      </div>
    </main>
  </div>
</template>