<script setup lang="ts">
import { computed, watch } from 'vue'
import { makePersistedAdapter } from '@livestore/adapter-web'
import LiveStoreSharedWorker from '@livestore/adapter-web/shared-worker?sharedworker'
import { LiveStoreProvider } from 'vue-livestore'
import ToDos from './components/to-dos.vue'
import LiveStoreWorker from './livestore/livestore.worker?worker'
import { schema } from './livestore/schema'
import AuthGuard from './components/auth/AuthGuard.vue'
import { useAuth } from './composables/useAuth'

const { accessToken, currentWorkspace, isAuthenticated } = useAuth()

const adapter = makePersistedAdapter({
  storage: { type: 'opfs' },
  worker: LiveStoreWorker,
  sharedWorker: LiveStoreSharedWorker,
  resetPersistence: false, // Persist data across sessions
})

// Reactive store options that update when auth changes
const storeOptions = computed(() => ({
  schema,
  adapter,
  storeId: currentWorkspace.value?.database_name || 'default_store',
  syncPayload: {
    jwtToken: accessToken.value || '',
    workspaceId: currentWorkspace.value?.id || '',
    // Legacy auth fallback (optional, remove in production)
    authToken: 'insecure-token-change-me'
  }
}))

// Log when auth state changes
watch(isAuthenticated, (newVal) => {
  console.log('Authentication status changed:', newVal)
})

watch(currentWorkspace, (workspace) => {
  if (workspace) {
    console.log('Current workspace:', workspace.name, workspace.database_name)
  }
})
</script>

<template>
  <AuthGuard>
    <LiveStoreProvider v-if="isAuthenticated && currentWorkspace" :options="storeOptions">
      <template #loading>
        <div class="min-h-screen flex items-center justify-center bg-gray-50">
          <div class="text-lg text-gray-600">Loading LiveStore...</div>
        </div>
      </template>
      <div class="min-h-screen bg-gray-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div class="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h1 class="text-2xl font-bold text-gray-900 mb-2">
              {{ currentWorkspace.name }}
            </h1>
            <p class="text-sm text-gray-600">
              Workspace ID: {{ currentWorkspace.id }}
            </p>
          </div>
          <ToDos />
        </div>
      </div>
    </LiveStoreProvider>
    <div v-else-if="isAuthenticated && !currentWorkspace" class="min-h-screen flex items-center justify-center bg-gray-50">
      <div class="text-lg text-gray-600">No workspace available. Please contact support.</div>
    </div>
  </AuthGuard>
</template>